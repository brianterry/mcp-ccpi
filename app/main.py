import os
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
import json
import boto3
import uuid
from pydantic import BaseModel, Field

from .llm_interface import LLMInterface
from .schema_manager import SchemaManager
from .guard_validator import GuardValidator

# Load environment variables
load_dotenv()

app = FastAPI(
    title="MCP Server for AWS CloudControl API",
    description="A server that allows LLMs to create and manage AWS cloud resources using CloudControl API",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize schema manager
schema_manager = SchemaManager()

# Initialize guard validator
guard_validator = GuardValidator()

# Pydantic models for request/response validation
class ResourceRequest(BaseModel):
    type_name: str = Field(..., description="The name of the resource type (e.g., AWS::S3::Bucket)")
    desired_state: Dict[str, Any] = Field(..., description="The desired state of the resource")
    role_arn: Optional[str] = Field(None, description="The ARN of the IAM role to use for the operation")
    client_token: Optional[str] = Field(None, description="A unique identifier to ensure idempotency")

class ResourceResponse(BaseModel):
    request_token: str = Field(..., description="The token that can be used to track the request status")
    operation: str = Field(..., description="The operation being performed (CREATE, UPDATE, DELETE)")
    operation_status: str = Field(..., description="The status of the operation")
    type_name: str = Field(..., description="The resource type name")
    identifier: Optional[str] = Field(None, description="The resource identifier")

class ResourceStatusResponse(BaseModel):
    request_token: str = Field(..., description="The token used to track the request")
    operation: str = Field(..., description="The operation being performed")
    operation_status: str = Field(..., description="The status of the operation")
    type_name: str = Field(..., description="The resource type name")
    identifier: Optional[str] = Field(None, description="The resource identifier")
    status_message: Optional[str] = Field(None, description="Additional status information")
    error_code: Optional[str] = Field(None, description="Error code if the operation failed")

class ResourceDescription(BaseModel):
    identifier: str = Field(..., description="The resource identifier")
    properties: Dict[str, Any] = Field(..., description="The resource properties")

class ResourceListResponse(BaseModel):
    type_name: str = Field(..., description="The resource type name")
    resources: List[ResourceDescription] = Field(..., description="List of resources")

class ResourceUpdateRequest(BaseModel):
    type_name: str = Field(..., description="The name of the resource type")
    identifier: str = Field(..., description="The identifier of the resource to update")
    patch_document: List[Dict[str, Any]] = Field(..., description="JSON Patch document describing the updates")
    role_arn: Optional[str] = Field(None, description="The ARN of the IAM role to use for the operation")
    client_token: Optional[str] = Field(None, description="A unique identifier to ensure idempotency")

class ResourceDeleteRequest(BaseModel):
    type_name: str = Field(..., description="The name of the resource type")
    identifier: str = Field(..., description="The identifier of the resource to delete")
    role_arn: Optional[str] = Field(None, description="The ARN of the IAM role to use for the operation")
    client_token: Optional[str] = Field(None, description="A unique identifier to ensure idempotency")

class NaturalLanguageRequest(BaseModel):
    text: str = Field(..., description="Natural language request from the LLM")
    execute: bool = Field(False, description="Whether to execute the request or just preview it")
    role_arn: Optional[str] = Field(None, description="The ARN of the IAM role to use for the operation")

class NaturalLanguageResponse(BaseModel):
    response: str = Field(..., description="Natural language response to the LLM")
    resource_config: Optional[Dict[str, Any]] = Field(None, description="The generated resource configuration")
    result: Optional[Dict[str, Any]] = Field(None, description="The result of the operation (if executed)")

class SchemaResponse(BaseModel):
    type_name: str = Field(..., description="The resource type name")
    schema: Dict[str, Any] = Field(..., description="The resource schema")

class ResourceTypeListResponse(BaseModel):
    resource_types: List[str] = Field(..., description="List of available resource types")

class ResourceTemplateResponse(BaseModel):
    type_name: str = Field(..., description="The resource type name")
    template: Dict[str, Any] = Field(..., description="The resource template")

# New models for CloudFormation Guard validation
class ValidationRequest(BaseModel):
    type_name: str = Field(..., description="The name of the resource type (e.g., AWS::S3::Bucket)")
    resource_config: Dict[str, Any] = Field(..., description="The resource configuration to validate")
    rule_names: Optional[List[str]] = Field(None, description="List of rule names to validate against (optional)")

class ValidationResponse(BaseModel):
    valid: bool = Field(..., description="Whether the resource configuration is valid")
    results: List[Dict[str, Any]] = Field(..., description="Validation results for each rule")

class RuleRequest(BaseModel):
    rule_name: str = Field(..., description="The name of the rule file")
    rule_content: str = Field(..., description="The content of the rule file")

class RuleResponse(BaseModel):
    rule_name: str = Field(..., description="The name of the rule file")
    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(None, description="Additional information about the operation")

class RuleListResponse(BaseModel):
    rules: List[str] = Field(..., description="List of available rule files")

class RuleContentResponse(BaseModel):
    rule_name: str = Field(..., description="The name of the rule file")
    rule_content: Optional[str] = Field(None, description="The content of the rule file")

# Dependency to get CloudControl client
def get_cloudcontrol_client():
    return boto3.client('cloudcontrol', 
                       region_name=os.getenv('AWS_REGION', 'us-east-1'))

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "message": "MCP Server for AWS CloudControl API is running"}

@app.post("/resources", response_model=ResourceResponse, tags=["Resources"])
async def create_resource(
    request: ResourceRequest,
    client: Any = Depends(get_cloudcontrol_client),
    validate_policy: bool = Query(False, description="Whether to validate the resource against policy rules")
):
    """Create a new AWS resource using CloudControl API"""
    try:
        # Validate the resource configuration against its schema
        validation_result = schema_manager.validate_resource_config(request.type_name, request.desired_state)
        if not validation_result.get("valid", False):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid resource configuration: {'; '.join(validation_result.get('errors', []))}"
            )
        
        # Validate against policy rules if requested
        if validate_policy:
            is_valid, validation_results = guard_validator.validate_resource(
                request.type_name,
                request.desired_state
            )
            
            if not is_valid:
                # Format the validation errors
                error_messages = []
                for result in validation_results:
                    if not result.get("valid", True):
                        rule_file = result.get("rule_file", "unknown")
                        details = result.get("details", [])
                        
                        for detail in details:
                            if detail.get("status") != "PASS":
                                rule_name = detail.get("rule_name", "unknown")
                                message = detail.get("message", "No message provided")
                                error_messages.append(f"Rule '{rule_name}' in '{rule_file}': {message}")
                
                if not error_messages:
                    error_messages.append("Resource configuration does not comply with policy rules")
                
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Resource configuration does not comply with policy rules",
                        "validation_results": validation_results,
                        "errors": error_messages
                    }
                )
        
        # Convert desired_state to JSON string
        desired_state_json = json.dumps(request.desired_state)
        
        # Prepare parameters for CloudControl API
        params = {
            "TypeName": request.type_name,
            "DesiredState": desired_state_json
        }
        
        # Add optional parameters if provided
        if request.role_arn:
            params["RoleArn"] = request.role_arn
        
        if request.client_token:
            params["ClientToken"] = request.client_token
        else:
            params["ClientToken"] = str(uuid.uuid4())
        
        # Call CloudControl API to create the resource
        response = client.create_resource(**params)
        
        # Extract progress event from response
        progress_event = response.get("ProgressEvent", {})
        
        return ResourceResponse(
            request_token=progress_event.get("RequestToken", ""),
            operation=progress_event.get("Operation", "CREATE"),
            operation_status=progress_event.get("OperationStatus", ""),
            type_name=progress_event.get("TypeName", request.type_name),
            identifier=progress_event.get("Identifier")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resources/status/{request_token}", response_model=ResourceStatusResponse, tags=["Resources"])
async def get_resource_request_status(
    request_token: str,
    client: Any = Depends(get_cloudcontrol_client)
):
    """Get the status of a resource request"""
    try:
        response = client.get_resource_request_status(RequestToken=request_token)
        
        # Extract progress event from response
        progress_event = response.get("ProgressEvent", {})
        
        return ResourceStatusResponse(
            request_token=progress_event.get("RequestToken", request_token),
            operation=progress_event.get("Operation", ""),
            operation_status=progress_event.get("OperationStatus", ""),
            type_name=progress_event.get("TypeName", ""),
            identifier=progress_event.get("Identifier"),
            status_message=progress_event.get("StatusMessage"),
            error_code=progress_event.get("ErrorCode")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resources/{type_name}", response_model=ResourceListResponse, tags=["Resources"])
async def list_resources(
    type_name: str,
    client: Any = Depends(get_cloudcontrol_client)
):
    """List resources of a specific type"""
    try:
        response = client.list_resources(TypeName=type_name)
        
        resources = []
        for resource_desc in response.get("ResourceDescriptions", []):
            # Parse properties JSON string to dictionary
            properties = json.loads(resource_desc.get("Properties", "{}"))
            
            resources.append(ResourceDescription(
                identifier=resource_desc.get("Identifier", ""),
                properties=properties
            ))
        
        return ResourceListResponse(
            type_name=type_name,
            resources=resources
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/resources/{type_name}/{identifier}", tags=["Resources"])
async def get_resource(
    type_name: str,
    identifier: str,
    client: Any = Depends(get_cloudcontrol_client)
):
    """Get details of a specific resource"""
    try:
        response = client.get_resource(
            TypeName=type_name,
            Identifier=identifier
        )
        
        # Parse properties JSON string to dictionary
        properties = json.loads(response.get("ResourceDescription", {}).get("Properties", "{}"))
        
        return {
            "type_name": type_name,
            "identifier": identifier,
            "properties": properties
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/resources", response_model=ResourceResponse, tags=["Resources"])
async def update_resource(
    request: ResourceUpdateRequest,
    client: Any = Depends(get_cloudcontrol_client)
):
    """Update an existing AWS resource"""
    try:
        # Convert patch document to JSON string
        patch_document_json = json.dumps(request.patch_document)
        
        # Prepare parameters for CloudControl API
        params = {
            "TypeName": request.type_name,
            "Identifier": request.identifier,
            "PatchDocument": patch_document_json
        }
        
        # Add optional parameters if provided
        if request.role_arn:
            params["RoleArn"] = request.role_arn
        
        if request.client_token:
            params["ClientToken"] = request.client_token
        else:
            params["ClientToken"] = str(uuid.uuid4())
        
        # Call CloudControl API to update the resource
        response = client.update_resource(**params)
        
        # Extract progress event from response
        progress_event = response.get("ProgressEvent", {})
        
        return ResourceResponse(
            request_token=progress_event.get("RequestToken", ""),
            operation=progress_event.get("Operation", "UPDATE"),
            operation_status=progress_event.get("OperationStatus", ""),
            type_name=progress_event.get("TypeName", request.type_name),
            identifier=progress_event.get("Identifier", request.identifier)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/resources", response_model=ResourceResponse, tags=["Resources"])
async def delete_resource(
    request: ResourceDeleteRequest,
    client: Any = Depends(get_cloudcontrol_client)
):
    """Delete an AWS resource"""
    try:
        # Prepare parameters for CloudControl API
        params = {
            "TypeName": request.type_name,
            "Identifier": request.identifier
        }
        
        # Add optional parameters if provided
        if request.role_arn:
            params["RoleArn"] = request.role_arn
        
        if request.client_token:
            params["ClientToken"] = request.client_token
        else:
            params["ClientToken"] = str(uuid.uuid4())
        
        # Call CloudControl API to delete the resource
        response = client.delete_resource(**params)
        
        # Extract progress event from response
        progress_event = response.get("ProgressEvent", {})
        
        return ResourceResponse(
            request_token=progress_event.get("RequestToken", ""),
            operation=progress_event.get("Operation", "DELETE"),
            operation_status=progress_event.get("OperationStatus", ""),
            type_name=progress_event.get("TypeName", request.type_name),
            identifier=progress_event.get("Identifier", request.identifier)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/llm/resources", response_model=NaturalLanguageResponse, tags=["LLM Interface"])
async def process_natural_language_request(
    request: NaturalLanguageRequest,
    client: Any = Depends(get_cloudcontrol_client)
):
    """Process a natural language request from an LLM to manage AWS resources"""
    try:
        # Parse the natural language request
        parsed_request = LLMInterface.parse_request(request.text)
        
        # Generate resource configuration
        resource_config = LLMInterface.generate_resource_config(parsed_request)
        
        # If there's an error in the configuration, return it
        if "error" in resource_config:
            response_text = LLMInterface.generate_response(resource_config)
            return NaturalLanguageResponse(
                response=response_text,
                resource_config=resource_config
            )
        
        # If execute is False, just return the preview
        if not request.execute:
            response_text = LLMInterface.generate_response(resource_config)
            return NaturalLanguageResponse(
                response=response_text,
                resource_config=resource_config
            )
        
        # Execute the operation based on the operation type
        operation = resource_config.get("operation", "CREATE")
        
        try:
            if operation == "CREATE":
                # Convert desired_state to JSON string
                desired_state_json = json.dumps(resource_config["desired_state"])
                
                # Prepare parameters for CloudControl API
                params = {
                    "TypeName": resource_config["type_name"],
                    "DesiredState": desired_state_json
                }
                
                # Add role ARN if provided
                if request.role_arn:
                    params["RoleArn"] = request.role_arn
                
                # Generate client token
                params["ClientToken"] = str(uuid.uuid4())
                
                # Call CloudControl API to create the resource
                response = client.create_resource(**params)
                
                # Extract progress event from response
                progress_event = response.get("ProgressEvent", {})
                
                result = {
                    "request_token": progress_event.get("RequestToken", ""),
                    "operation": progress_event.get("Operation", "CREATE"),
                    "operation_status": progress_event.get("OperationStatus", ""),
                    "type_name": progress_event.get("TypeName", resource_config["type_name"]),
                    "identifier": progress_event.get("Identifier")
                }
            
            elif operation == "GET":
                # Get resource details
                response = client.get_resource(
                    TypeName=resource_config["type_name"],
                    Identifier=resource_config["identifier"]
                )
                
                # Parse properties JSON string to dictionary
                properties = json.loads(response.get("ResourceDescription", {}).get("Properties", "{}"))
                
                result = {
                    "operation": "GET",
                    "type_name": resource_config["type_name"],
                    "identifier": resource_config["identifier"],
                    "properties": properties
                }
            
            elif operation == "LIST":
                # List resources
                response = client.list_resources(TypeName=resource_config["type_name"])
                
                resources = []
                for resource_desc in response.get("ResourceDescriptions", []):
                    # Parse properties JSON string to dictionary
                    properties = json.loads(resource_desc.get("Properties", "{}"))
                    
                    resources.append({
                        "identifier": resource_desc.get("Identifier", ""),
                        "properties": properties
                    })
                
                result = {
                    "operation": "LIST",
                    "type_name": resource_config["type_name"],
                    "resources": resources
                }
            
            elif operation == "UPDATE":
                # Convert patch document to JSON string
                patch_document_json = json.dumps(resource_config["patch_document"])
                
                # Prepare parameters for CloudControl API
                params = {
                    "TypeName": resource_config["type_name"],
                    "Identifier": resource_config["identifier"],
                    "PatchDocument": patch_document_json
                }
                
                # Add role ARN if provided
                if request.role_arn:
                    params["RoleArn"] = request.role_arn
                
                # Generate client token
                params["ClientToken"] = str(uuid.uuid4())
                
                # Call CloudControl API to update the resource
                response = client.update_resource(**params)
                
                # Extract progress event from response
                progress_event = response.get("ProgressEvent", {})
                
                result = {
                    "request_token": progress_event.get("RequestToken", ""),
                    "operation": progress_event.get("Operation", "UPDATE"),
                    "operation_status": progress_event.get("OperationStatus", ""),
                    "type_name": progress_event.get("TypeName", resource_config["type_name"]),
                    "identifier": progress_event.get("Identifier", resource_config["identifier"])
                }
            
            elif operation == "DELETE":
                # Prepare parameters for CloudControl API
                params = {
                    "TypeName": resource_config["type_name"],
                    "Identifier": resource_config["identifier"]
                }
                
                # Add role ARN if provided
                if request.role_arn:
                    params["RoleArn"] = request.role_arn
                
                # Generate client token
                params["ClientToken"] = str(uuid.uuid4())
                
                # Call CloudControl API to delete the resource
                response = client.delete_resource(**params)
                
                # Extract progress event from response
                progress_event = response.get("ProgressEvent", {})
                
                result = {
                    "request_token": progress_event.get("RequestToken", ""),
                    "operation": progress_event.get("Operation", "DELETE"),
                    "operation_status": progress_event.get("OperationStatus", ""),
                    "type_name": progress_event.get("TypeName", resource_config["type_name"]),
                    "identifier": progress_event.get("Identifier", resource_config["identifier"])
                }
            
            else:
                raise ValueError(f"Unsupported operation: {operation}")
            
            # Generate response text
            response_text = LLMInterface.generate_response(resource_config, result)
            
            return NaturalLanguageResponse(
                response=response_text,
                resource_config=resource_config,
                result=result
            )
        
        except Exception as e:
            # If operation execution fails, return the error
            error_result = {
                "operation": operation,
                "operation_status": "FAILED",
                "type_name": resource_config.get("type_name", ""),
                "error_code": "ExecutionError",
                "status_message": str(e)
            }
            
            response_text = LLMInterface.generate_response(resource_config, error_result)
            
            return NaturalLanguageResponse(
                response=response_text,
                resource_config=resource_config,
                result=error_result
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schemas/{type_name}", response_model=SchemaResponse, tags=["Schemas"])
async def get_resource_schema(type_name: str):
    """Get the schema for a resource type"""
    try:
        schema = schema_manager.get_schema(type_name)
        if not schema:
            # Try to download the schema
            if not schema_manager.download_schema(type_name):
                raise HTTPException(status_code=404, detail=f"Schema not found for resource type: {type_name}")
            schema = schema_manager.get_schema(type_name)
        
        return SchemaResponse(
            type_name=type_name,
            schema=schema
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schemas", response_model=ResourceTypeListResponse, tags=["Schemas"])
async def list_resource_types(
    query: Optional[str] = Query(None, description="Search query for resource types")
):
    """List available resource types"""
    try:
        if query:
            resource_types = schema_manager.search_resource_types(query)
        else:
            resource_types = schema_manager.list_available_resource_types()
        
        return ResourceTypeListResponse(
            resource_types=resource_types
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/templates/{type_name}", response_model=ResourceTemplateResponse, tags=["Templates"])
async def get_resource_template(
    type_name: str,
    include_optional: bool = Query(False, description="Whether to include optional properties")
):
    """Get a template for a resource type"""
    try:
        template = schema_manager.generate_resource_template(type_name, include_optional)
        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found for resource type: {type_name}")
        
        return ResourceTemplateResponse(
            type_name=type_name,
            template=template
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schemas/download", tags=["Schemas"])
async def download_schemas(
    common_only: bool = Query(True, description="Whether to download only common schemas or all schemas")
):
    """Download resource schemas"""
    try:
        if common_only:
            schema_manager.download_common_schemas()
            return {"message": "Common schemas downloaded successfully"}
        else:
            schema_manager.download_all_schemas()
            return {"message": "All schemas downloaded successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/validate", response_model=ValidationResponse, tags=["Validation"])
async def validate_resource_config(request: ValidationRequest):
    """
    Validate a resource configuration against CloudFormation Guard rules.
    
    This endpoint validates a resource configuration against policy rules
    defined using AWS CloudFormation Guard syntax.
    """
    try:
        is_valid, validation_results = guard_validator.validate_resource(
            request.type_name,
            request.resource_config,
            request.rule_names
        )
        
        return ValidationResponse(
            valid=is_valid,
            results=validation_results
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/llm/validate", tags=["LLM Interface"])
async def llm_validate_resource(request: NaturalLanguageRequest):
    """
    Process a natural language request from an LLM to validate a resource configuration.
    
    This endpoint allows LLMs to validate resource configurations against policy rules
    using natural language.
    """
    try:
        llm_interface = LLMInterface(schema_manager, guard_validator)
        
        # Process the natural language request
        operation, resource_type, resource_config = llm_interface.process_validation_request(request.text)
        
        if not resource_config:
            return {
                "response": "I couldn't understand the resource configuration from your request. "
                           "Please provide a clearer description of the resource you want to validate."
            }
        
        # Validate the resource configuration
        is_valid, validation_results = guard_validator.validate_resource(
            resource_type,
            resource_config
        )
        
        # Generate a natural language response
        response = llm_interface.generate_validation_response(
            is_valid,
            validation_results,
            resource_type,
            resource_config
        )
        
        return {
            "response": response,
            "resource_config": resource_config,
            "validation_results": {
                "valid": is_valid,
                "results": validation_results
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Rule management endpoints
@app.get("/rules", response_model=RuleListResponse, tags=["Rules"])
async def list_rules():
    """List all available CloudFormation Guard rule files."""
    try:
        rules = guard_validator.list_rules()
        return RuleListResponse(rules=rules)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rules/{rule_name}", response_model=RuleContentResponse, tags=["Rules"])
async def get_rule(rule_name: str):
    """Get the content of a CloudFormation Guard rule file."""
    try:
        rule_content = guard_validator.get_rule_content(rule_name)
        
        if rule_content is None:
            raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found")
        
        return RuleContentResponse(
            rule_name=rule_name,
            rule_content=rule_content
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rules", response_model=RuleResponse, tags=["Rules"])
async def save_rule(request: RuleRequest):
    """Save a CloudFormation Guard rule file."""
    try:
        success = guard_validator.save_rule(request.rule_name, request.rule_content)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to save rule '{request.rule_name}'")
        
        return RuleResponse(
            rule_name=request.rule_name,
            success=True,
            message=f"Rule '{request.rule_name}' saved successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/rules/{rule_name}", response_model=RuleResponse, tags=["Rules"])
async def delete_rule(rule_name: str):
    """Delete a CloudFormation Guard rule file."""
    try:
        success = guard_validator.delete_rule(rule_name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found or could not be deleted")
        
        return RuleResponse(
            rule_name=rule_name,
            success=True,
            message=f"Rule '{rule_name}' deleted successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rules/generate-examples", response_model=RuleListResponse, tags=["Rules"])
async def generate_example_rules():
    """Generate example CloudFormation Guard rule files."""
    try:
        guard_validator.generate_example_rules()
        rules = guard_validator.list_rules()
        
        return RuleListResponse(rules=rules)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 