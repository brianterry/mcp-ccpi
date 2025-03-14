#!/usr/bin/env python3
"""
Natural language interface demo for the MCP server.

This script demonstrates how to use the natural language interface
to create and manage AWS resources using simple English commands.
"""

import requests
import json
import time
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MCP server URL
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

def process_nl_request(text, execute=False):
    """
    Process a natural language request.
    
    Args:
        text: The natural language request text
        execute: Whether to execute the request or just preview
        
    Returns:
        The response data or None if there was an error
    """
    print(f"\nSending natural language request: \"{text}\"")
    print(f"Execute mode: {'ON' if execute else 'OFF (preview only)'}")
    
    # Prepare the request payload
    payload = {
        "text": text,
        "execute": execute
    }
    
    # Send the request
    response = requests.post(
        f"{MCP_SERVER_URL}/llm/resources",
        json=payload
    )
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.text}")
        return None
    
    # Get the response data
    response_data = response.json()
    
    # Print the natural language response
    print("\nResponse from MCP server:")
    print("-" * 40)
    print(response_data["response"])
    print("-" * 40)
    
    return response_data

def wait_for_completion(request_token, max_attempts=10, sleep_time=5):
    """
    Wait for an operation to complete.
    
    Args:
        request_token: The request token
        max_attempts: Maximum number of polling attempts
        sleep_time: Time to sleep between polling attempts (seconds)
        
    Returns:
        The final status data or None if timed out
    """
    print(f"\nWaiting for operation to complete (request token: {request_token})...")
    
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
        
        if operation_status in ["SUCCESS", "FAILED"]:
            return status_data
    
    print("Timed out waiting for operation to complete.")
    return None

def main():
    """Run the natural language demo."""
    if len(sys.argv) < 2:
        print("Usage: python natural_language_demo.py \"<natural language request>\" [--execute]")
        print("\nExample requests:")
        print("  - \"Create an S3 bucket named my-test-bucket with versioning enabled\"")
        print("  - \"List all S3 buckets\"")
        print("  - \"Get details of S3 bucket my-test-bucket\"")
        print("  - \"Delete S3 bucket my-test-bucket\"")
        sys.exit(1)
    
    # Get the natural language request and execute flag
    nl_request = sys.argv[1]
    execute_mode = "--execute" in sys.argv
    
    # Process the natural language request
    response_data = process_nl_request(nl_request, execute_mode)
    
    if not response_data:
        print("Failed to process request.")
        sys.exit(1)
    
    # If not executing, exit
    if not execute_mode:
        print("\nThis was just a preview. Run with --execute to actually perform the operation.")
        sys.exit(0)
    
    # If there's a result with a request token, wait for completion
    if response_data.get("result") and response_data["result"].get("request_token"):
        request_token = response_data["result"]["request_token"]
        
        final_status = wait_for_completion(request_token)
        
        if final_status:
            print("\nFinal operation status:")
            print(json.dumps(final_status, indent=2))
    
    print("\nOperation completed!")

if __name__ == "__main__":
    main() 