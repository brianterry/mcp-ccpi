#!/usr/bin/env python3
"""
Example script that demonstrates how to integrate the MCP server with an LLM.

This script shows how to:
1. Process a user request with an LLM
2. Generate a natural language request for the MCP server
3. Send the request to the MCP server
4. Process the response and provide feedback to the user

Note: This example uses a simulated LLM for demonstration purposes.
In a real-world scenario, you would use an actual LLM API like OpenAI, Anthropic, etc.
"""

import requests
import json
import sys

# MCP server URL
MCP_SERVER_URL = "http://localhost:8000"

class SimulatedLLM:
    """
    A simulated LLM for demonstration purposes.
    
    In a real-world scenario, you would use an actual LLM API like OpenAI, Anthropic, etc.
    """
    
    def process_user_request(self, user_request):
        """
        Process a user request and generate a natural language request for the MCP server.
        
        Args:
            user_request: The user's request
            
        Returns:
            A natural language request for the MCP server
        """
        # In a real-world scenario, you would send the user request to an LLM API
        # and get back a response. Here, we'll just simulate it with some basic logic.
        
        if "s3" in user_request.lower() and "bucket" in user_request.lower():
            # Extract bucket name from the request
            import re
            bucket_name_match = re.search(r'(?:bucket|name)[:\s]+["\']([\w.-]+)["\']', user_request)
            bucket_name = bucket_name_match.group(1) if bucket_name_match else "example-bucket"
            
            # Generate a natural language request for the MCP server
            return f"Create an S3 bucket with name '{bucket_name}' and versioning enabled, public access blocked, and encryption enabled"
        
        elif "dynamodb" in user_request.lower() and "table" in user_request.lower():
            # Extract table name from the request
            import re
            table_name_match = re.search(r'(?:table|name)[:\s]+["\']([\w.-]+)["\']', user_request)
            table_name = table_name_match.group(1) if table_name_match else "example-table"
            
            # Generate a natural language request for the MCP server
            return f"Create a DynamoDB table with name '{table_name}', partition key 'id', and read capacity 5"
        
        else:
            return "I'm not sure what resource you want to create. Please specify the resource type and name."
    
    def generate_user_response(self, mcp_response):
        """
        Generate a response to the user based on the MCP server response.
        
        Args:
            mcp_response: The response from the MCP server
            
        Returns:
            A response to the user
        """
        # In a real-world scenario, you would send the MCP response to an LLM API
        # and get back a user-friendly response. Here, we'll just return the MCP response.
        
        return mcp_response["response"]

def send_to_mcp_server(natural_language_request, execute=False):
    """
    Send a natural language request to the MCP server.
    
    Args:
        natural_language_request: The natural language request
        execute: Whether to execute the request or just preview it
        
    Returns:
        The response from the MCP server
    """
    # Prepare the request
    request_data = {
        "text": natural_language_request,
        "execute": execute
    }
    
    # Send the request
    response = requests.post(f"{MCP_SERVER_URL}/llm/resources", json=request_data)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        sys.exit(1)
    
    return response.json()

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python llm_integration.py \"<user request>\" [--execute]")
        sys.exit(1)
    
    user_request = sys.argv[1]
    execute = "--execute" in sys.argv
    
    # Step 1: Process the user request with the LLM
    llm = SimulatedLLM()
    natural_language_request = llm.process_user_request(user_request)
    
    print(f"User request: {user_request}")
    print(f"LLM generated request: {natural_language_request}")
    
    # Step 2: Send the natural language request to the MCP server
    print("\nSending request to MCP server...")
    mcp_response = send_to_mcp_server(natural_language_request, execute)
    
    # Step 3: Generate a response to the user
    user_response = llm.generate_user_response(mcp_response)
    
    print("\nResponse to user:")
    print(user_response)
    
    if not execute:
        print("\nThis was just a preview. Run with --execute to actually create the resource.")

if __name__ == "__main__":
    main() 