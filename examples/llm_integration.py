#!/usr/bin/env python3
"""
Example script for LLM integration with the MCP server.

This script demonstrates how to use the natural language interface
to create, read, update, and delete AWS resources.
"""

import requests
import json
import sys
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MCP server URL
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")

def process_llm_request(text, execute=False):
    """
    Process a natural language request from an LLM.
    
    Args:
        text: The natural language request text
        execute: Whether to execute the request or just preview it
    
    Returns:
        The response from the server
    """
    # Prepare the request payload
    payload = {
        "text": text,
        "execute": execute
    }
    
    # Send the request
    print(f"Sending request: {text}")
    response = requests.post(
        f"{MCP_SERVER_URL}/llm/resources",
        json=payload
    )
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error processing request: {response.text}")
        return None
    
    # Get the response data
    response_data = response.json()
    
    return response_data

def check_resource_status(request_token):
    """
    Check the status of a resource request.
    
    Args:
        request_token: The request token
    
    Returns:
        The status response
    """
    # Send the request
    response = requests.get(
        f"{MCP_SERVER_URL}/resources/status/{request_token}"
    )
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error getting status: {response.text}")
        return None
    
    # Get the response data
    status_data = response.json()
    
    return status_data

def wait_for_operation_completion(request_token):
    """
    Wait for an operation to complete.
    
    Args:
        request_token: The request token
    
    Returns:
        The final status
    """
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        
        # Wait before checking status
        time.sleep(5)
        
        # Get the status
        status_data = check_resource_status(request_token)
        
        if not status_data:
            print("Failed to get status. Retrying...")
            continue
        
        operation_status = status_data.get("operation_status")
        print(f"Status: {operation_status}")
        
        # Check if the operation is complete
        if operation_status in ["SUCCESS", "FAILED"]:
            return status_data
        
        # If still in progress, continue polling
        print("Operation in progress. Waiting...")
    
    print("Timed out waiting for operation to complete.")
    return None

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python llm_integration.py <request_text> [--execute]")
        sys.exit(1)
    
    # Get the request text and execute flag
    request_text = sys.argv[1]
    execute = "--execute" in sys.argv
    
    # Process the request
    response = process_llm_request(request_text, execute)
    
    if not response:
        print("Failed to process request.")
        sys.exit(1)
    
    # Print the response
    print("\nResponse from MCP server:")
    print(response["response"])
    
    # If not executing, exit
    if not execute:
        print("\nThis was just a preview. Run with --execute to actually perform the operation.")
        sys.exit(0)
    
    # If there's a result with a request token, wait for completion
    if response.get("result") and response["result"].get("request_token"):
        request_token = response["result"]["request_token"]
        
        print(f"\nWaiting for operation to complete (request token: {request_token})...")
        final_status = wait_for_operation_completion(request_token)
        
        if final_status:
            print("\nFinal status:")
            print(json.dumps(final_status, indent=2))
    
    print("\nOperation completed.")

if __name__ == "__main__":
    main() 