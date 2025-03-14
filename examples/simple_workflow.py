#!/usr/bin/env python3
"""
Simple workflow example for the MCP server.

This script demonstrates a complete workflow:
1. Create an S3 bucket
2. Check the status of the creation
3. Get details of the created bucket
4. List all S3 buckets
5. Delete the bucket
"""

import requests
import json
import time
import uuid
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MCP server URL
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

def print_step(step_number, description):
    """Print a step header."""
    print(f"\n{'='*80}")
    print(f"STEP {step_number}: {description}")
    print(f"{'='*80}")

def wait_for_operation(request_token, max_attempts=10, sleep_time=5):
    """
    Wait for an operation to complete.
    
    Args:
        request_token: The request token
        max_attempts: Maximum number of polling attempts
        sleep_time: Time to sleep between polling attempts (seconds)
        
    Returns:
        The final status data or None if timed out
    """
    print(f"Waiting for operation to complete (request token: {request_token})...")
    
    for attempt in range(1, max_attempts + 1):
        print(f"Checking status (attempt {attempt}/{max_attempts})...")
        
        # Wait before checking
        time.sleep(sleep_time)
        
        # Get status
        response = requests.get(f"{MCP_SERVER_URL}/resources/status/{request_token}")
        
        if response.status_code != 200:
            print(f"Error getting status: {response.text}")
            continue
        
        status_data = response.json()
        operation_status = status_data.get("operation_status")
        
        print(f"Status: {operation_status}")
        
        if operation_status == "SUCCESS":
            print("Operation completed successfully!")
            return status_data
        elif operation_status == "FAILED":
            error_code = status_data.get("error_code")
            status_message = status_data.get("status_message")
            print(f"Operation failed: {error_code} - {status_message}")
            return status_data
    
    print("Timed out waiting for operation to complete.")
    return None

def main():
    """Run the simple workflow."""
    # Generate a unique bucket name
    bucket_name = f"mcp-demo-{uuid.uuid4().hex[:8]}"
    
    if len(sys.argv) > 1:
        bucket_name = sys.argv[1]
    
    print(f"Starting simple workflow with bucket name: {bucket_name}")
    
    # STEP 1: Create an S3 bucket
    print_step(1, "Creating an S3 bucket")
    
    create_payload = {
        "type_name": "AWS::S3::Bucket",
        "desired_state": {
            "BucketName": bucket_name,
            "VersioningConfiguration": {
                "Status": "Enabled"
            },
            "Tags": [
                {
                    "Key": "CreatedBy",
                    "Value": "MCP-Demo"
                }
            ]
        }
    }
    
    create_response = requests.post(
        f"{MCP_SERVER_URL}/resources",
        json=create_payload
    )
    
    if create_response.status_code != 200:
        print(f"Error creating bucket: {create_response.text}")
        return
    
    create_data = create_response.json()
    request_token = create_data.get("request_token")
    
    print(f"Create request submitted. Response:")
    print(json.dumps(create_data, indent=2))
    
    # STEP 2: Check the status of the creation
    print_step(2, "Checking creation status")
    
    status_data = wait_for_operation(request_token)
    
    if not status_data or status_data.get("operation_status") != "SUCCESS":
        print("Failed to create bucket. Exiting workflow.")
        return
    
    # STEP 3: Get details of the created bucket
    print_step(3, "Getting bucket details")
    
    details_response = requests.get(
        f"{MCP_SERVER_URL}/resources/AWS::S3::Bucket/{bucket_name}"
    )
    
    if details_response.status_code != 200:
        print(f"Error getting bucket details: {details_response.text}")
    else:
        details_data = details_response.json()
        print("Bucket details:")
        print(json.dumps(details_data, indent=2))
    
    # STEP 4: List all S3 buckets
    print_step(4, "Listing all S3 buckets")
    
    list_response = requests.get(
        f"{MCP_SERVER_URL}/resources/AWS::S3::Bucket"
    )
    
    if list_response.status_code != 200:
        print(f"Error listing buckets: {list_response.text}")
    else:
        list_data = list_response.json()
        print(f"Found {len(list_data.get('resources', []))} S3 buckets:")
        for bucket in list_data.get("resources", []):
            print(f"  - {bucket.get('identifier')}")
    
    # STEP 5: Delete the bucket
    print_step(5, "Deleting the bucket")
    
    delete_payload = {
        "type_name": "AWS::S3::Bucket",
        "identifier": bucket_name
    }
    
    delete_response = requests.delete(
        f"{MCP_SERVER_URL}/resources",
        json=delete_payload
    )
    
    if delete_response.status_code != 200:
        print(f"Error deleting bucket: {delete_response.text}")
        return
    
    delete_data = delete_response.json()
    delete_token = delete_data.get("request_token")
    
    print(f"Delete request submitted. Response:")
    print(json.dumps(delete_data, indent=2))
    
    # Wait for delete operation to complete
    delete_status = wait_for_operation(delete_token)
    
    if delete_status and delete_status.get("operation_status") == "SUCCESS":
        print(f"\nBucket {bucket_name} was successfully deleted.")
    else:
        print(f"\nNote: Bucket {bucket_name} may need to be manually deleted.")
    
    print("\nWorkflow completed!")

if __name__ == "__main__":
    main() 