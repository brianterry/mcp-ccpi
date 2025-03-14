#!/usr/bin/env python3
"""
Schema management example for the MCP server.

This script demonstrates how to:
1. Download resource schemas
2. List available resource types
3. Get a schema for a specific resource type
4. Generate a template from a schema
5. Create a resource using a template
"""

import requests
import json
import time
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MCP server URL
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

def print_section(title):
    """Print a section header."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")

def download_schemas(common_only=True):
    """
    Download resource schemas.
    
    Args:
        common_only: Whether to download only common schemas or all schemas
    """
    print_section(f"Downloading {'common' if common_only else 'all'} schemas")
    
    response = requests.post(
        f"{MCP_SERVER_URL}/schemas/download",
        params={"common_only": common_only}
    )
    
    if response.status_code != 200:
        print(f"Error downloading schemas: {response.text}")
        return False
    
    print(f"Schemas downloaded successfully: {response.json()['message']}")
    return True

def list_resource_types(query=None):
    """
    List available resource types.
    
    Args:
        query: Optional search query to filter resource types
    """
    print_section(f"Listing resource types{' matching ' + query if query else ''}")
    
    params = {}
    if query:
        params["query"] = query
    
    response = requests.get(
        f"{MCP_SERVER_URL}/schemas",
        params=params
    )
    
    if response.status_code != 200:
        print(f"Error listing resource types: {response.text}")
        return []
    
    resource_types = response.json()["resource_types"]
    
    print(f"Found {len(resource_types)} resource types:")
    for i, resource_type in enumerate(resource_types[:10], 1):
        print(f"  {i}. {resource_type}")
    
    if len(resource_types) > 10:
        print(f"  ... and {len(resource_types) - 10} more")
    
    return resource_types

def get_resource_schema(type_name):
    """
    Get a schema for a specific resource type.
    
    Args:
        type_name: The resource type name (e.g., AWS::S3::Bucket)
    """
    print_section(f"Getting schema for {type_name}")
    
    response = requests.get(
        f"{MCP_SERVER_URL}/schemas/{type_name}"
    )
    
    if response.status_code != 200:
        print(f"Error getting schema: {response.text}")
        return None
    
    schema = response.json()["schema"]
    
    print(f"Schema retrieved successfully. Schema size: {len(json.dumps(schema))} bytes")
    print("Schema structure:")
    
    # Print the top-level structure of the schema
    for key, value in schema.items():
        if isinstance(value, dict):
            print(f"  {key}: {{{len(value)} keys}}")
        elif isinstance(value, list):
            print(f"  {key}: [{len(value)} items]")
        else:
            print(f"  {key}: {value}")
    
    return schema

def generate_template(type_name, include_optional=False):
    """
    Generate a template for a resource type.
    
    Args:
        type_name: The resource type name (e.g., AWS::S3::Bucket)
        include_optional: Whether to include optional properties
    """
    print_section(f"Generating template for {type_name}")
    
    response = requests.get(
        f"{MCP_SERVER_URL}/templates/{type_name}",
        params={"include_optional": include_optional}
    )
    
    if response.status_code != 200:
        print(f"Error generating template: {response.text}")
        return None
    
    template = response.json()["template"]
    
    print(f"Template generated successfully with {len(template)} properties:")
    print(json.dumps(template, indent=2))
    
    return template

def create_resource_from_template(type_name, template, resource_name):
    """
    Create a resource using a template.
    
    Args:
        type_name: The resource type name (e.g., AWS::S3::Bucket)
        template: The resource template
        resource_name: The name to give to the resource
    """
    print_section(f"Creating {type_name} from template")
    
    # Customize the template
    if "BucketName" in template and type_name == "AWS::S3::Bucket":
        template["BucketName"] = resource_name
    elif "Name" in template:
        template["Name"] = resource_name
    
    # Create the resource
    response = requests.post(
        f"{MCP_SERVER_URL}/resources",
        json={
            "type_name": type_name,
            "desired_state": template
        }
    )
    
    if response.status_code != 200:
        print(f"Error creating resource: {response.text}")
        return None
    
    result = response.json()
    
    print("Resource creation initiated:")
    print(json.dumps(result, indent=2))
    
    # Wait for the resource creation to complete
    request_token = result.get("request_token")
    if request_token:
        print("\nWaiting for resource creation to complete...")
        
        max_attempts = 10
        for attempt in range(1, max_attempts + 1):
            print(f"Checking status (attempt {attempt}/{max_attempts})...")
            
            # Wait before checking
            time.sleep(5)
            
            # Get status
            status_response = requests.get(
                f"{MCP_SERVER_URL}/resources/status/{request_token}"
            )
            
            if status_response.status_code != 200:
                print(f"Error getting status: {status_response.text}")
                continue
            
            status_data = status_response.json()
            operation_status = status_data.get("operation_status")
            
            print(f"Status: {operation_status}")
            
            if operation_status == "SUCCESS":
                print("Resource created successfully!")
                return status_data
            elif operation_status == "FAILED":
                error_code = status_data.get("error_code")
                status_message = status_data.get("status_message")
                print(f"Resource creation failed: {error_code} - {status_message}")
                return status_data
        
        print("Timed out waiting for resource creation to complete.")
    
    return result

def main():
    """Run the schema management example."""
    # Check if we should download all schemas
    download_all = "--all" in sys.argv
    
    # Download schemas
    if not download_schemas(common_only=not download_all):
        print("Failed to download schemas. Exiting.")
        return
    
    # List resource types
    resource_types = list_resource_types()
    
    if not resource_types:
        print("No resource types found. Exiting.")
        return
    
    # Choose a resource type to work with
    type_name = "AWS::S3::Bucket"  # Default to S3 bucket
    
    # Get the schema for the resource type
    schema = get_resource_schema(type_name)
    
    if not schema:
        print(f"Failed to get schema for {type_name}. Exiting.")
        return
    
    # Generate a template for the resource type
    include_optional = "--include-optional" in sys.argv
    template = generate_template(type_name, include_optional)
    
    if not template:
        print(f"Failed to generate template for {type_name}. Exiting.")
        return
    
    # Create a resource from the template if requested
    if "--create" in sys.argv:
        # Generate a unique resource name
        import uuid
        resource_name = f"schema-example-{uuid.uuid4().hex[:8]}"
        
        # Allow specifying a resource name
        for i, arg in enumerate(sys.argv):
            if arg == "--name" and i + 1 < len(sys.argv):
                resource_name = sys.argv[i + 1]
                break
        
        create_resource_from_template(type_name, template, resource_name)

if __name__ == "__main__":
    print("Schema Management Example")
    print("Usage: python schema_management.py [options]")
    print("Options:")
    print("  --all               Download all schemas (not just common ones)")
    print("  --include-optional  Include optional properties in the template")
    print("  --create            Create a resource from the template")
    print("  --name NAME         Specify a name for the created resource")
    print("\nStarting example...")
    main() 