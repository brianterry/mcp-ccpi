#!/usr/bin/env python3
"""
Example script for creating an S3 bucket using the MCP server.
"""

import requests
import json
import sys
import time
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MCP server URL
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

def create_s3_bucket(bucket_name=None):
    """
    Create an S3 bucket using the MCP server.
    
    Args:
        bucket_name: Name of the bucket to create (optional, will generate a name if not provided)
    
    Returns:
        The response from the server
    """
    if not bucket_name:
        # Generate a unique bucket name
        bucket_name = f"mcp-example-{uuid.uuid4().hex[:8]}"
    
    # Prepare the request payload
    payload = {
        "type_name": "AWS::S3::Bucket",
        "desired_state": {
            "BucketName": bucket_name,
            "AccessControl": "Private",
            "VersioningConfiguration": {
                "Status": "Enabled"
            },
            "Tags": [
                {
                    "Key": "CreatedBy",
                    "Value": "MCP-Example"
                },
                {
                    "Key": "Environment",
                    "Value": "Development"
                }
            ]
        }
    }
    
    # Send the request to create the bucket
    print(f"Creating S3 bucket: {bucket_name}")
    response = requests.post(
        f"{MCP_SERVER_URL}/resources",
        json=payload
    )
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error creating bucket: {response.text}")
        return None
    
    # Get the response data
    response_data = response.json()
    request_token = response_data.get("request_token")
    
    print(f"Request submitted. Request token: {request_token}")
    
    # Poll for the status of the request
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        
        # Wait before checking status
        time.sleep(5)
        
        # Get the status of the request
        status_response = requests.get(
            f"{MCP_SERVER_URL}/resources/status/{request_token}"
        )
        
        if status_response.status_code != 200:
            print(f"Error getting status: {status_response.text}")
            continue
        
        status_data = status_response.json()
        operation_status = status_data.get("operation_status")
        
        print(f"Status: {operation_status}")
        
        # Check if the operation is complete
        if operation_status == "SUCCESS":
            identifier = status_data.get("identifier")
            print(f"Bucket created successfully. Identifier: {identifier}")
            return status_data
        
        elif operation_status == "FAILED":
            error_code = status_data.get("error_code")
            status_message = status_data.get("status_message")
            print(f"Operation failed. Error: {error_code} - {status_message}")
            return status_data
        
        # If still in progress, continue polling
        print("Operation in progress. Waiting...")
    
    print("Timed out waiting for operation to complete.")
    return None

def main():
    """Main function."""
    # Get bucket name from command line argument if provided
    bucket_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Create the bucket
    result = create_s3_bucket(bucket_name)
    
    # Print the result
    if result:
        print("\nFinal result:")
        print(json.dumps(result, indent=2))
    else:
        print("\nFailed to create bucket.")

if __name__ == "__main__":
    main() 