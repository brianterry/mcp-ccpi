"""
LLM Interface module for the MCP server.

This module provides functionality to parse natural language requests from LLMs,
generate resource configurations, and generate responses back to the LLM.
"""

import re
import json
from typing import Dict, Any, List, Optional, Union, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMInterface:
    """
    Interface for handling natural language interactions with LLMs.
    """
    
    @staticmethod
    def parse_request(text: str) -> Dict[str, Any]:
        """
        Parse a natural language request from an LLM.
        
        Args:
            text: The natural language request text
            
        Returns:
            A dictionary containing the parsed request information
        """
        # Initialize the parsed request
        parsed_request = {
            "original_text": text,
            "operation": None,
            "resource_type": None,
            "resource_name": None,
            "properties": {},
            "identifier": None,
        }
        
        # Try to determine the operation type (CREATE, GET, LIST, UPDATE, DELETE)
        if re.search(r'\b(create|make|provision|deploy|set up|launch)\b', text.lower()):
            parsed_request["operation"] = "CREATE"
        elif re.search(r'\b(get|fetch|retrieve|show|display|describe)\b', text.lower()):
            parsed_request["operation"] = "GET"
        elif re.search(r'\b(list|show all|get all|enumerate|find all)\b', text.lower()):
            parsed_request["operation"] = "LIST"
        elif re.search(r'\b(update|modify|change|edit|alter)\b', text.lower()):
            parsed_request["operation"] = "UPDATE"
        elif re.search(r'\b(delete|remove|destroy|tear down|terminate)\b', text.lower()):
            parsed_request["operation"] = "DELETE"
        
        # Try to extract the resource type
        resource_type_match = re.search(r'(AWS::\w+::\w+)', text)
        if resource_type_match:
            parsed_request["resource_type"] = resource_type_match.group(1)
        else:
            # Try to infer resource type from common names
            if re.search(r'\b(s3|bucket|storage)\b', text.lower()):
                parsed_request["resource_type"] = "AWS::S3::Bucket"
            elif re.search(r'\b(lambda|function)\b', text.lower()):
                parsed_request["resource_type"] = "AWS::Lambda::Function"
            elif re.search(r'\b(dynamodb|dynamo|table)\b', text.lower()):
                parsed_request["resource_type"] = "AWS::DynamoDB::Table"
            elif re.search(r'\b(ec2|instance|server|vm)\b', text.lower()):
                parsed_request["resource_type"] = "AWS::EC2::Instance"
            elif re.search(r'\b(rds|database|db)\b', text.lower()):
                parsed_request["resource_type"] = "AWS::RDS::DBInstance"
            elif re.search(r'\b(sns|topic|notification)\b', text.lower()):
                parsed_request["resource_type"] = "AWS::SNS::Topic"
            elif re.search(r'\b(sqs|queue)\b', text.lower()):
                parsed_request["resource_type"] = "AWS::SQS::Queue"
        
        # Try to extract resource name
        name_match = re.search(r'(?:named|called|with name|name is|name it)\s+["\']?([a-zA-Z0-9-_]+)["\']?', text.lower())
        if name_match:
            parsed_request["resource_name"] = name_match.group(1)
        
        # Try to extract resource identifier for GET, UPDATE, DELETE operations
        if parsed_request["operation"] in ["GET", "UPDATE", "DELETE"]:
            identifier_match = re.search(r'(?:with id|identifier|id is|id:|identifier is)\s+["\']?([a-zA-Z0-9-_:/]+)["\']?', text.lower())
            if identifier_match:
                parsed_request["identifier"] = identifier_match.group(1)
        
        # Try to extract properties from the text
        # This is a simplified approach - in a real implementation, you might use more sophisticated NLP
        properties = {}
        
        # Look for key-value pairs in the format "key: value" or "key = value"
        kv_matches = re.finditer(r'(\w+)[\s]*[=:]+[\s]*["\']?([^,"\']+)["\']?', text)
        for match in kv_matches:
            key, value = match.groups()
            properties[key.strip()] = value.strip()
        
        # Look for JSON-like structures in the text
        json_match = re.search(r'{(.*)}', text, re.DOTALL)
        if json_match:
            try:
                json_str = "{" + json_match.group(1) + "}"
                # Try to fix common issues in the JSON string
                json_str = re.sub(r'(\w+):', r'"\1":', json_str)  # Add quotes to keys
                json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
                json_data = json.loads(json_str)
                properties.update(json_data)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON-like structure in the text")
        
        parsed_request["properties"] = properties
        
        return parsed_request
    
    @staticmethod
    def generate_resource_config(parsed_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a resource configuration based on the parsed request.
        
        Args:
            parsed_request: The parsed request from parse_request()
            
        Returns:
            A dictionary containing the resource configuration
        """
        operation = parsed_request.get("operation")
        resource_type = parsed_request.get("resource_type")
        
        # Validate required fields
        if not operation:
            return {
                "error": "Operation not specified or could not be determined",
                "parsed_request": parsed_request
            }
        
        if not resource_type:
            return {
                "error": "Resource type not specified or could not be determined",
                "parsed_request": parsed_request
            }
        
        # Initialize the resource configuration
        resource_config = {
            "operation": operation,
            "type_name": resource_type,
        }
        
        # Handle different operations
        if operation == "CREATE":
            # For CREATE, we need a desired state
            desired_state = {}
            
            # Add resource name if provided
            if parsed_request.get("resource_name"):
                desired_state["Name"] = parsed_request.get("resource_name")
            
            # Add other properties
            desired_state.update(parsed_request.get("properties", {}))
            
            resource_config["desired_state"] = desired_state
            
        elif operation in ["GET", "DELETE"]:
            # For GET and DELETE, we need an identifier
            identifier = parsed_request.get("identifier")
            if not identifier:
                return {
                    "error": f"Identifier is required for {operation} operation",
                    "parsed_request": parsed_request
                }
            
            resource_config["identifier"] = identifier
            
        elif operation == "LIST":
            # For LIST, we just need the resource type, which we already have
            pass
            
        elif operation == "UPDATE":
            # For UPDATE, we need an identifier and a patch document
            identifier = parsed_request.get("identifier")
            if not identifier:
                return {
                    "error": "Identifier is required for UPDATE operation",
                    "parsed_request": parsed_request
                }
            
            resource_config["identifier"] = identifier
            
            # Create a patch document from the properties
            properties = parsed_request.get("properties", {})
            if not properties:
                return {
                    "error": "No properties specified for UPDATE operation",
                    "parsed_request": parsed_request
                }
            
            # Convert properties to a JSON Patch document
            patch_document = []
            for key, value in properties.items():
                patch_document.append({
                    "op": "replace",
                    "path": f"/{key}",
                    "value": value
                })
            
            resource_config["patch_document"] = patch_document
        
        return resource_config
    
    @staticmethod
    def generate_response(resource_config: Dict[str, Any], result: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a natural language response based on the resource configuration and result.
        
        Args:
            resource_config: The resource configuration
            result: The result of the operation (if any)
            
        Returns:
            A natural language response
        """
        # Check if there was an error in the resource configuration
        if "error" in resource_config:
            return f"I couldn't process your request. {resource_config['error']}. Please provide more information."
        
        operation = resource_config.get("operation")
        type_name = resource_config.get("type_name")
        
        # If no result, this is a preview response
        if not result:
            if operation == "CREATE":
                desired_state = resource_config.get("desired_state", {})
                properties_str = ", ".join([f"{k}: {v}" for k, v in desired_state.items()])
                return f"I'll create a new {type_name} resource with the following properties: {properties_str}. Would you like me to proceed?"
                
            elif operation == "GET":
                identifier = resource_config.get("identifier")
                return f"I'll retrieve the {type_name} resource with identifier '{identifier}'. Would you like me to proceed?"
                
            elif operation == "LIST":
                return f"I'll list all {type_name} resources. Would you like me to proceed?"
                
            elif operation == "UPDATE":
                identifier = resource_config.get("identifier")
                patch_document = resource_config.get("patch_document", [])
                changes = ", ".join([f"{p['path'].lstrip('/')}: {p['value']}" for p in patch_document])
                return f"I'll update the {type_name} resource with identifier '{identifier}' with the following changes: {changes}. Would you like me to proceed?"
                
            elif operation == "DELETE":
                identifier = resource_config.get("identifier")
                return f"I'll delete the {type_name} resource with identifier '{identifier}'. Would you like me to proceed?"
        
        # If there is a result, this is a response after execution
        else:
            operation_status = result.get("operation_status")
            
            if operation_status == "FAILED":
                error_code = result.get("error_code", "Unknown")
                status_message = result.get("status_message", "No additional information available")
                return f"The {operation} operation for {type_name} failed with error code '{error_code}'. {status_message}"
            
            if operation == "CREATE":
                request_token = result.get("request_token", "")
                identifier = result.get("identifier")
                if identifier:
                    return f"I've started creating a new {type_name} resource with identifier '{identifier}'. You can check the status using the request token: {request_token}"
                else:
                    return f"I've started creating a new {type_name} resource. You can check the status using the request token: {request_token}"
                
            elif operation == "GET":
                properties = result.get("properties", {})
                properties_str = json.dumps(properties, indent=2)
                return f"Here are the details of the {type_name} resource:\n{properties_str}"
                
            elif operation == "LIST":
                resources = result.get("resources", [])
                if not resources:
                    return f"No {type_name} resources found."
                
                resources_str = "\n".join([f"- {r['identifier']}" for r in resources])
                return f"I found {len(resources)} {type_name} resources:\n{resources_str}"
                
            elif operation == "UPDATE":
                request_token = result.get("request_token", "")
                identifier = result.get("identifier")
                return f"I've started updating the {type_name} resource with identifier '{identifier}'. You can check the status using the request token: {request_token}"
                
            elif operation == "DELETE":
                request_token = result.get("request_token", "")
                identifier = result.get("identifier")
                return f"I've started deleting the {type_name} resource with identifier '{identifier}'. You can check the status using the request token: {request_token}"
        
        # Default response if none of the above conditions are met
        return "I've processed your request, but I'm not sure how to describe the result." 