"""
LLM interface for the MCP server.

This module provides a natural language interface for LLMs to interact with the MCP server.
It includes functions for parsing LLM requests, generating resource configurations,
and providing helpful responses.
"""

import json
import re
from typing import Dict, Any, Optional, Tuple, List, Union
from .schema_manager import SchemaManager

class LLMInterface:
    """Interface for handling LLM requests and generating responses."""
    
    # Initialize schema manager as a class variable
    schema_manager = SchemaManager()
    
    @staticmethod
    def parse_request(request_text: str) -> Dict[str, Any]:
        """
        Parse a natural language request from an LLM into a structured format.
        
        Args:
            request_text: The natural language request from the LLM
            
        Returns:
            Dictionary with parsed request parameters
        """
        # Extract resource type
        resource_type_match = re.search(r'create (?:an? )?(AWS::\w+::\w+|s3 bucket|dynamodb table|lambda function|ec2 instance)', 
                                       request_text.lower())
        
        if not resource_type_match:
            return {"error": "Could not determine the resource type to create"}
        
        resource_type = resource_type_match.group(1)
        
        # Map common names to AWS resource types
        resource_type_mapping = {
            "s3 bucket": "AWS::S3::Bucket",
            "dynamodb table": "AWS::DynamoDB::Table",
            "lambda function": "AWS::Lambda::Function",
            "ec2 instance": "AWS::EC2::Instance"
        }
        
        if resource_type in resource_type_mapping:
            resource_type = resource_type_mapping[resource_type]
        
        # Get schema for the resource type
        schema = LLMInterface.schema_manager.get_schema(resource_type)
        if not schema:
            # Try to download the schema
            if not LLMInterface.schema_manager.download_schema(resource_type):
                return {"error": f"Could not find schema for resource type: {resource_type}"}
        
        # Extract parameters based on resource type
        params = {}
        
        # Generic parameter extraction based on property names from schema
        property_types = LLMInterface.schema_manager.get_property_types(resource_type)
        
        for prop_name in property_types.keys():
            # Create regex patterns to match property values in the request text
            # Look for patterns like "PropertyName: value" or "property name is value"
            patterns = [
                rf'{prop_name}[:\s]+["\']([\w.-]+)["\']',  # PropertyName: "value"
                rf'{prop_name}[:\s]+(\w+)',  # PropertyName: value
                rf'{prop_name.lower()}[:\s]+["\']([\w.-]+)["\']',  # propertyname: "value"
                rf'{prop_name.lower()}[:\s]+(\w+)',  # propertyname: value
                rf'{" ".join(re.findall("[A-Z][^A-Z]*", prop_name)).lower()}[:\s]+["\']([\w.-]+)["\']',  # property name: "value"
                rf'{" ".join(re.findall("[A-Z][^A-Z]*", prop_name)).lower()}[:\s]+(\w+)'  # property name: value
            ]
            
            for pattern in patterns:
                match = re.search(pattern, request_text)
                if match:
                    params[prop_name] = match.group(1)
                    break
        
        # Special handling for specific resource types
        if resource_type == "AWS::S3::Bucket":
            # Extract bucket name if not already found
            if "BucketName" not in params:
                bucket_name_match = re.search(r'(?:bucket|name)[:\s]+["\']([\w.-]+)["\']', request_text)
                if bucket_name_match:
                    params["BucketName"] = bucket_name_match.group(1)
            
            # Check for versioning
            versioning_match = re.search(r'versioning[:\s]+(enabled|disabled|true|false)', request_text.lower())
            if versioning_match:
                versioning_value = versioning_match.group(1)
                if versioning_value in ["enabled", "true"]:
                    params["VersioningConfiguration"] = {"Status": "Enabled"}
                else:
                    params["VersioningConfiguration"] = {"Status": "Suspended"}
            
            # Check for public access
            public_access_match = re.search(r'public access[:\s]+(blocked|allowed|true|false)', request_text.lower())
            if public_access_match:
                public_access_value = public_access_match.group(1)
                if public_access_value in ["blocked", "true"]:
                    params["PublicAccessBlockConfiguration"] = {
                        "BlockPublicAcls": True,
                        "BlockPublicPolicy": True,
                        "IgnorePublicAcls": True,
                        "RestrictPublicBuckets": True
                    }
            
            # Check for encryption
            encryption_match = re.search(r'encryption[:\s]+(enabled|disabled|true|false)', request_text.lower())
            if encryption_match:
                encryption_value = encryption_match.group(1)
                if encryption_value in ["enabled", "true"]:
                    params["BucketEncryption"] = {
                        "ServerSideEncryptionConfiguration": [
                            {
                                "ServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": "AES256"
                                }
                            }
                        ]
                    }
        
        elif resource_type == "AWS::DynamoDB::Table":
            # Extract table name if not already found
            if "TableName" not in params:
                table_name_match = re.search(r'(?:table|name)[:\s]+["\']([\w.-]+)["\']', request_text)
                if table_name_match:
                    params["TableName"] = table_name_match.group(1)
            
            # Extract partition key
            partition_key_match = re.search(r'partition key[:\s]+["\']([\w.-]+)["\']', request_text)
            if partition_key_match:
                partition_key = partition_key_match.group(1)
                
                # Initialize KeySchema and AttributeDefinitions if not already present
                if "KeySchema" not in params:
                    params["KeySchema"] = []
                if "AttributeDefinitions" not in params:
                    params["AttributeDefinitions"] = []
                
                # Add partition key to KeySchema
                params["KeySchema"].append({
                    "AttributeName": partition_key,
                    "KeyType": "HASH"
                })
                
                # Add partition key to AttributeDefinitions
                params["AttributeDefinitions"].append({
                    "AttributeName": partition_key,
                    "AttributeType": "S"  # Default to string type
                })
            
            # Extract sort key
            sort_key_match = re.search(r'sort key[:\s]+["\']([\w.-]+)["\']', request_text)
            if sort_key_match:
                sort_key = sort_key_match.group(1)
                
                # Initialize KeySchema and AttributeDefinitions if not already present
                if "KeySchema" not in params:
                    params["KeySchema"] = []
                if "AttributeDefinitions" not in params:
                    params["AttributeDefinitions"] = []
                
                # Add sort key to KeySchema
                params["KeySchema"].append({
                    "AttributeName": sort_key,
                    "KeyType": "RANGE"
                })
                
                # Add sort key to AttributeDefinitions
                params["AttributeDefinitions"].append({
                    "AttributeName": sort_key,
                    "AttributeType": "S"  # Default to string type
                })
            
            # Extract capacity
            read_capacity_match = re.search(r'read capacity[:\s]+(\d+)', request_text)
            write_capacity_match = re.search(r'write capacity[:\s]+(\d+)', request_text)
            
            if read_capacity_match or write_capacity_match:
                params["ProvisionedThroughput"] = {}
                
                if read_capacity_match:
                    params["ProvisionedThroughput"]["ReadCapacityUnits"] = int(read_capacity_match.group(1))
                else:
                    params["ProvisionedThroughput"]["ReadCapacityUnits"] = 5  # Default
                
                if write_capacity_match:
                    params["ProvisionedThroughput"]["WriteCapacityUnits"] = int(write_capacity_match.group(1))
                else:
                    params["ProvisionedThroughput"]["WriteCapacityUnits"] = 5  # Default
        
        return {
            "resource_type": resource_type,
            "params": params
        }
    
    @staticmethod
    def generate_resource_config(parsed_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a resource configuration based on the parsed request.
        
        Args:
            parsed_request: The parsed request from parse_request
            
        Returns:
            Dictionary with the resource configuration
        """
        if "error" in parsed_request:
            return {"error": parsed_request["error"]}
        
        resource_type = parsed_request.get("resource_type")
        params = parsed_request.get("params", {})
        
        # Get required properties for the resource type
        required_props = LLMInterface.schema_manager.get_required_properties(resource_type)
        
        # Check if all required properties are present
        missing_props = [prop for prop in required_props if prop not in params]
        if missing_props:
            return {"error": f"Missing required properties: {', '.join(missing_props)}"}
        
        # Validate the resource configuration
        validation_result = LLMInterface.schema_manager.validate_resource_config(resource_type, params)
        if not validation_result.get("valid", False):
            return {"error": "; ".join(validation_result.get("errors", ["Invalid resource configuration"]))}
        
        # Create the resource configuration
        return {
            "type_name": resource_type,
            "desired_state": params
        }
    
    @staticmethod
    def generate_response(resource_config: Dict[str, Any], result: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a natural language response based on the resource configuration and result.
        
        Args:
            resource_config: The resource configuration
            result: The result of the resource creation (if available)
            
        Returns:
            Natural language response
        """
        if "error" in resource_config:
            return f"I couldn't create the resource: {resource_config['error']}"
        
        resource_type = resource_config.get("type_name")
        desired_state = resource_config.get("desired_state", {})
        
        if not result:
            # This is a preview response
            # Get the identifier property for the resource type
            identifier_prop = LLMInterface.schema_manager.get_resource_identifier_property(resource_type)
            identifier_value = desired_state.get(identifier_prop, "unknown") if identifier_prop else "unknown"
            
            # Generate a human-readable description of the resource
            properties_description = []
            
            for prop_name, prop_value in desired_state.items():
                if prop_name == identifier_prop:
                    continue  # Skip the identifier property as it's already mentioned
                
                if isinstance(prop_value, dict):
                    properties_description.append(f"- {prop_name}: {json.dumps(prop_value, indent=2)}")
                elif isinstance(prop_value, list):
                    properties_description.append(f"- {prop_name}: {json.dumps(prop_value, indent=2)}")
                else:
                    properties_description.append(f"- {prop_name}: {prop_value}")
            
            properties_text = "\n".join(properties_description)
            
            return (
                f"I'll create a {resource_type} resource with identifier '{identifier_value}' and the following configuration:\n"
                f"{properties_text}\n\n"
                f"Would you like me to proceed with creating this resource?"
            )
        
        else:
            # This is a response after resource creation
            operation = result.get("operation", "CREATE")
            status = result.get("operation_status", "")
            identifier = result.get("identifier", "")
            
            if status == "IN_PROGRESS":
                return (
                    f"I've started the {operation} operation for the {resource_type} resource.\n"
                    f"- Resource identifier: {identifier}\n"
                    f"- Current status: {status}\n"
                    f"- Request token: {result.get('request_token', '')}\n\n"
                    f"You can check the status of this request later using the request token."
                )
            
            elif status == "SUCCESS":
                return (
                    f"The {operation} operation for the {resource_type} resource was successful!\n"
                    f"- Resource identifier: {identifier}\n"
                    f"- Status: {status}"
                )
            
            elif status == "FAILED":
                error_code = result.get("error_code", "")
                status_message = result.get("status_message", "")
                
                return (
                    f"The {operation} operation for the {resource_type} resource failed.\n"
                    f"- Resource identifier: {identifier}\n"
                    f"- Error code: {error_code}\n"
                    f"- Error message: {status_message}"
                )
            
            else:
                return f"The {operation} operation for the {resource_type} resource is in state: {status}" 