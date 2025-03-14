#!/usr/bin/env python3
"""
Example script that demonstrates how to use the MCP server with schema-based resource creation.

This script shows how to:
1. Get a resource schema
2. Generate a template for a resource
3. Create a resource using the template
4. Check the status of the resource creation request
"""

import requests
import json
import time
import sys
import argparse

# MCP server URL
MCP_SERVER_URL = "http://localhost:8000"

def get_resource_schema(type_name):
    """
    Get the schema for a resource type.
    
    Args:
        type_name: The name of the resource type (e.g., AWS::S3::Bucket)
        
    Returns:
        The schema for the resource type
    """
    # Send the request
    response = requests.get(f"{MCP_SERVER_URL}/schemas/{type_name}")
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()["schema"]

def get_resource_template(type_name, include_optional=False):
    """
    Get a template for a resource type.
    
    Args:
        type_name: The name of the resource type (e.g., AWS::S3::Bucket)
        include_optional: Whether to include optional properties
        
    Returns:
        The template for the resource type
    """
    # Send the request
    response = requests.get(
        f"{MCP_SERVER_URL}/templates/{type_name}",
        params={"include_optional": include_optional}
    )
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()["template"]

def create_resource(type_name, desired_state):
    """
    Create a resource.
    
    Args:
        type_name: The name of the resource type (e.g., AWS::S3::Bucket)
        desired_state: The desired state of the resource
        
    Returns:
        The response from the MCP server
    """
    # Prepare the request
    request_data = {
        "type_name": type_name,
        "desired_state": desired_state
    }
    
    # Send the request
    response = requests.post(f"{MCP_SERVER_URL}/resources", json=request_data)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()

def check_resource_status(request_token):
    """
    Check the status of a resource creation request.
    
    Args:
        request_token: The token of the resource creation request
        
    Returns:
        The response from the MCP server
    """
    # Send the request
    response = requests.get(f"{MCP_SERVER_URL}/resources/status/{request_token}")
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()

def list_resource_types(query=None):
    """
    List available resource types.
    
    Args:
        query: Search query for resource types
        
    Returns:
        The response from the MCP server
    """
    # Prepare the request parameters
    params = {}
    if query:
        params["query"] = query
    
    # Send the request
    response = requests.get(f"{MCP_SERVER_URL}/schemas", params=params)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()["resource_types"]

def download_schemas(common_only=True):
    """
    Download resource schemas.
    
    Args:
        common_only: Whether to download only common schemas or all schemas
        
    Returns:
        The response from the MCP server
    """
    # Prepare the request parameters
    params = {"common_only": common_only}
    
    # Send the request
    response = requests.post(f"{MCP_SERVER_URL}/schemas/download", params=params)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Create AWS resources using the MCP server")
    parser.add_argument("--type", required=True, help="Resource type (e.g., AWS::S3::Bucket)")
    parser.add_argument("--name", required=True, help="Resource name")
    parser.add_argument("--execute", action="store_true", help="Execute the resource creation")
    parser.add_argument("--list-types", action="store_true", help="List available resource types")
    parser.add_argument("--download-schemas", action="store_true", help="Download resource schemas")
    parser.add_argument("--all-schemas", action="store_true", help="Download all schemas (not just common ones)")
    
    args = parser.parse_args()
    
    # Download schemas if requested
    if args.download_schemas:
        print("Downloading schemas...")
        result = download_schemas(not args.all_schemas)
        print(result["message"])
        if not args.type:
            return
    
    # List resource types if requested
    if args.list_types:
        print("Available resource types:")
        resource_types = list_resource_types()
        for resource_type in resource_types:
            print(f"- {resource_type}")
        return
    
    type_name = args.type
    resource_name = args.name
    
    # Step 1: Get the resource schema
    print(f"Getting schema for {type_name}...")
    schema = get_resource_schema(type_name)
    
    # Step 2: Generate a template for the resource
    print(f"Generating template for {type_name}...")
    template = get_resource_template(type_name, include_optional=True)
    
    # Step 3: Customize the template
    # Find the identifier property
    identifier_prop = None
    primary_identifier = schema.get("primaryIdentifier", [])
    if primary_identifier and isinstance(primary_identifier, list) and len(primary_identifier) > 0:
        # Extract property name from the identifier path (e.g., /properties/BucketName -> BucketName)
        identifier_path = primary_identifier[0]
        import re
        match = re.search(r'/properties/(\w+)', identifier_path)
        if match:
            identifier_prop = match.group(1)
    
    # Fallback to common identifier properties
    if not identifier_prop:
        common_identifiers = {
            "AWS::S3::Bucket": "BucketName",
            "AWS::DynamoDB::Table": "TableName",
            "AWS::Lambda::Function": "FunctionName",
            "AWS::EC2::Instance": "InstanceId"
        }
        identifier_prop = common_identifiers.get(type_name)
    
    # Set the resource name in the template
    if identifier_prop and identifier_prop in template:
        template[identifier_prop] = resource_name
    
    # Add some common configurations based on resource type
    if type_name == "AWS::S3::Bucket":
        template["VersioningConfiguration"] = {"Status": "Enabled"}
        template["PublicAccessBlockConfiguration"] = {
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True
        }
        template["BucketEncryption"] = {
            "ServerSideEncryptionConfiguration": [
                {
                    "ServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        }
    elif type_name == "AWS::DynamoDB::Table":
        if "KeySchema" not in template:
            template["KeySchema"] = [
                {
                    "AttributeName": "id",
                    "KeyType": "HASH"
                }
            ]
        if "AttributeDefinitions" not in template:
            template["AttributeDefinitions"] = [
                {
                    "AttributeName": "id",
                    "AttributeType": "S"
                }
            ]
        if "ProvisionedThroughput" not in template:
            template["ProvisionedThroughput"] = {
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            }
    
    # Print the customized template
    print("\nCustomized template:")
    print(json.dumps(template, indent=2))
    
    if not args.execute:
        print("\nThis was just a preview. Run with --execute to actually create the resource.")
        return
    
    # Step 4: Create the resource
    print(f"\nCreating {type_name} resource...")
    response = create_resource(type_name, template)
    
    print("\nResponse from MCP server:")
    print(json.dumps(response, indent=2))
    
    # Step 5: Check the status of the resource creation request
    request_token = response["request_token"]
    print(f"\nChecking status of request {request_token}...")
    
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        status_response = check_resource_status(request_token)
        
        print(f"\nStatus: {status_response['operation_status']}")
        
        if status_response["operation_status"] in ["SUCCESS", "FAILED"]:
            break
        
        print("Waiting for resource creation to complete...")
        time.sleep(5)
    
    if status_response["operation_status"] == "FAILED":
        print(f"Resource creation failed: {status_response.get('status_message', 'Unknown error')}")
        sys.exit(1)
    
    print(f"\n{type_name} resource '{resource_name}' created successfully!")

if __name__ == "__main__":
    main() 