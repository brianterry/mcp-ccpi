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
    client: Any = Depends(get_cloudcontrol_client)
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
    """Process a natural language request from an LLM to create AWS resources"""
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
        
        # Execute the resource creation
        try:
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
            
            # Generate response text
            response_text = LLMInterface.generate_response(resource_config, result)
            
            return NaturalLanguageResponse(
                response=response_text,
                resource_config=resource_config,
                result=result
            )
        
        except Exception as e:
            # If resource creation fails, return the error
            error_result = {
                "operation": "CREATE",
                "operation_status": "FAILED",
                "type_name": resource_config["type_name"],
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 