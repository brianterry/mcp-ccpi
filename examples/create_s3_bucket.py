#!/usr/bin/env python3
"""
Example script that demonstrates how to use the MCP server to create an S3 bucket.

This script shows how to:
1. Send a natural language request to create an S3 bucket
2. Check the status of the resource creation request
3. Get details of the created resource
"""

import requests
import json
import time
import sys

# MCP server URL
MCP_SERVER_URL = "http://localhost:8000"

def create_s3_bucket(bucket_name, execute=False):
    """
    Send a natural language request to create an S3 bucket.
    
    Args:
        bucket_name: The name of the S3 bucket to create
        execute: Whether to execute the request or just preview it
        
    Returns:
        The response from the MCP server
    """
    # Prepare the request
    request_data = {
        "text": f"Create an S3 bucket with name '{bucket_name}' and versioning enabled, public access blocked, and encryption enabled",
        "execute": execute
    }
    
    # Send the request
    response = requests.post(f"{MCP_SERVER_URL}/llm/resources", json=request_data)
    
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

def get_resource_details(type_name, identifier):
    """
    Get details of a resource.
    
    Args:
        type_name: The type name of the resource
        identifier: The identifier of the resource
        
    Returns:
        The response from the MCP server
    """
    # Send the request
    response = requests.get(f"{MCP_SERVER_URL}/resources/{type_name}/{identifier}")
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python create_s3_bucket.py <bucket_name> [--execute]")
        sys.exit(1)
    
    bucket_name = sys.argv[1]
    execute = "--execute" in sys.argv
    
    # Step 1: Send a natural language request to create an S3 bucket
    print(f"Sending request to create S3 bucket '{bucket_name}'...")
    response = create_s3_bucket(bucket_name, execute)
    
    print("\nResponse from MCP server:")
    print(response["response"])
    
    if not execute:
        print("\nThis was just a preview. Run with --execute to actually create the bucket.")
        sys.exit(0)
    
    # Step 2: Check the status of the resource creation request
    request_token = response["result"]["request_token"]
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
    
    # Step 3: Get details of the created resource
    print(f"\nGetting details of bucket '{bucket_name}'...")
    resource_details = get_resource_details("AWS::S3::Bucket", bucket_name)
    
    print("\nResource details:")
    print(json.dumps(resource_details, indent=2))
    
    print(f"\nS3 bucket '{bucket_name}' created successfully!")

if __name__ == "__main__":
    main() 