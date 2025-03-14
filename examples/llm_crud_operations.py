#!/usr/bin/env python3
"""
Example script that demonstrates how to use the MCP server's natural language interface
for CRUD (Create, Read, Update, Delete) operations.

This script shows how to:
1. Create a resource using natural language
2. Read/get details of a resource using natural language
3. List resources using natural language
4. Update a resource using natural language
5. Delete a resource using natural language
"""

import requests
import json
import time
import sys
import argparse

# MCP server URL
MCP_SERVER_URL = "http://localhost:8000"

def send_natural_language_request(text, execute=False):
    """
    Send a natural language request to the MCP server.
    
    Args:
        text: The natural language request text
        execute: Whether to execute the request or just preview it
        
    Returns:
        The response from the MCP server
    """
    # Prepare the request
    request_data = {
        "text": text,
        "execute": execute
    }
    
    # Send the request
    response = requests.post(f"{MCP_SERVER_URL}/llm/resources", json=request_data)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()

def create_resource(resource_type, resource_name, additional_params="", execute=False):
    """
    Create a resource using natural language.
    
    Args:
        resource_type: The type of resource to create (e.g., S3 bucket, DynamoDB table)
        resource_name: The name of the resource
        additional_params: Additional parameters for the resource
        execute: Whether to execute the request or just preview it
        
    Returns:
        The response from the MCP server
    """
    # Construct the natural language request
    text = f"Create a {resource_type} named '{resource_name}'"
    if additional_params:
        text += f" with {additional_params}"
    
    # Send the request
    return send_natural_language_request(text, execute)

def get_resource(resource_type, resource_name, execute=False):
    """
    Get details of a resource using natural language.
    
    Args:
        resource_type: The type of resource (e.g., S3 bucket, DynamoDB table)
        resource_name: The name of the resource
        execute: Whether to execute the request or just preview it
        
    Returns:
        The response from the MCP server
    """
    # Construct the natural language request
    text = f"Get details of {resource_type} '{resource_name}'"
    
    # Send the request
    return send_natural_language_request(text, execute)

def list_resources(resource_type, execute=False):
    """
    List resources of a specific type using natural language.
    
    Args:
        resource_type: The type of resources to list (e.g., S3 buckets, DynamoDB tables)
        execute: Whether to execute the request or just preview it
        
    Returns:
        The response from the MCP server
    """
    # Construct the natural language request
    text = f"List all {resource_type}"
    
    # Send the request
    return send_natural_language_request(text, execute)

def update_resource(resource_type, resource_name, update_params, execute=False):
    """
    Update a resource using natural language.
    
    Args:
        resource_type: The type of resource (e.g., S3 bucket, DynamoDB table)
        resource_name: The name of the resource
        update_params: The parameters to update
        execute: Whether to execute the request or just preview it
        
    Returns:
        The response from the MCP server
    """
    # Construct the natural language request
    text = f"Update {resource_type} '{resource_name}' to {update_params}"
    
    # Send the request
    return send_natural_language_request(text, execute)

def delete_resource(resource_type, resource_name, execute=False):
    """
    Delete a resource using natural language.
    
    Args:
        resource_type: The type of resource (e.g., S3 bucket, DynamoDB table)
        resource_name: The name of the resource
        execute: Whether to execute the request or just preview it
        
    Returns:
        The response from the MCP server
    """
    # Construct the natural language request
    text = f"Delete {resource_type} '{resource_name}'"
    
    # Send the request
    return send_natural_language_request(text, execute)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Demonstrate CRUD operations using natural language")
    parser.add_argument("--operation", required=True, choices=["create", "read", "list", "update", "delete"], 
                        help="The CRUD operation to perform")
    parser.add_argument("--type", required=True, help="Resource type (e.g., 'S3 bucket', 'DynamoDB table')")
    parser.add_argument("--name", help="Resource name (required for create, read, update, delete)")
    parser.add_argument("--params", help="Additional parameters for create or update operations")
    parser.add_argument("--execute", action="store_true", help="Execute the operation (default is preview only)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.operation in ["create", "read", "update", "delete"] and not args.name:
        parser.error(f"--name is required for {args.operation} operation")
    
    if args.operation in ["create", "update"] and not args.params:
        parser.error(f"--params is required for {args.operation} operation")
    
    # Perform the requested operation
    if args.operation == "create":
        print(f"Creating {args.type} '{args.name}'...")
        response = create_resource(args.type, args.name, args.params, args.execute)
    elif args.operation == "read":
        print(f"Getting details of {args.type} '{args.name}'...")
        response = get_resource(args.type, args.name, args.execute)
    elif args.operation == "list":
        print(f"Listing all {args.type}...")
        response = list_resources(args.type, args.execute)
    elif args.operation == "update":
        print(f"Updating {args.type} '{args.name}'...")
        response = update_resource(args.type, args.name, args.params, args.execute)
    elif args.operation == "delete":
        print(f"Deleting {args.type} '{args.name}'...")
        response = delete_resource(args.type, args.name, args.execute)
    
    # Print the response
    print("\nResponse from MCP server:")
    print(response["response"])
    
    # Print additional information if available
    if "resource_config" in response and response["resource_config"]:
        print("\nResource configuration:")
        print(json.dumps(response["resource_config"], indent=2))
    
    if "result" in response and response["result"]:
        print("\nOperation result:")
        print(json.dumps(response["result"], indent=2))
    
    # Print execution status
    if not args.execute:
        print("\nThis was just a preview. Run with --execute to actually perform the operation.")

if __name__ == "__main__":
    main() 