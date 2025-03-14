#!/usr/bin/env python3
"""
Policy validation example for the MCP server.

This script demonstrates how to:
1. Create and manage CloudFormation Guard rules
2. Validate resource configurations against policy rules
3. Use natural language to validate resources
"""

import requests
import json
import sys
import os
import argparse
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

def generate_example_rules():
    """Generate example CloudFormation Guard rules."""
    print_section("Generating example rules")
    
    response = requests.post(f"{MCP_SERVER_URL}/rules/generate-examples")
    
    if response.status_code != 200:
        print(f"Error generating example rules: {response.text}")
        return False
    
    rules = response.json().get("rules", [])
    print(f"Generated {len(rules)} example rules:")
    for rule in rules:
        print(f"  - {rule}")
    
    return True

def list_rules():
    """List all available CloudFormation Guard rules."""
    print_section("Listing available rules")
    
    response = requests.get(f"{MCP_SERVER_URL}/rules")
    
    if response.status_code != 200:
        print(f"Error listing rules: {response.text}")
        return []
    
    rules = response.json().get("rules", [])
    print(f"Found {len(rules)} rules:")
    for rule in rules:
        print(f"  - {rule}")
    
    return rules

def get_rule_content(rule_name):
    """Get the content of a CloudFormation Guard rule."""
    print_section(f"Getting content of rule '{rule_name}'")
    
    response = requests.get(f"{MCP_SERVER_URL}/rules/{rule_name}")
    
    if response.status_code != 200:
        print(f"Error getting rule content: {response.text}")
        return None
    
    rule_content = response.json().get("rule_content")
    print(f"Rule content:")
    print(rule_content)
    
    return rule_content

def create_custom_rule():
    """Create a custom CloudFormation Guard rule."""
    print_section("Creating a custom rule")
    
    # Example rule for S3 bucket logging
    rule_name = "s3_bucket_logging.guard"
    rule_content = """
# Rule to ensure S3 buckets have logging enabled
rule s3_bucket_logging_enabled {
    AWS::S3::Bucket {
        # Check if logging is configured
        LoggingConfiguration exists
        LoggingConfiguration is_struct
        
        # Check if destination bucket is specified
        LoggingConfiguration {
            DestinationBucketName exists
            DestinationBucketName != ""
        }
    }
}
"""
    
    print(f"Creating rule '{rule_name}' with content:")
    print(rule_content)
    
    response = requests.post(
        f"{MCP_SERVER_URL}/rules",
        json={
            "rule_name": rule_name,
            "rule_content": rule_content
        }
    )
    
    if response.status_code != 200:
        print(f"Error creating rule: {response.text}")
        return False
    
    result = response.json()
    print(f"Rule created successfully: {result.get('message')}")
    
    return True

def validate_resource_config(resource_type, resource_config, rule_names=None):
    """
    Validate a resource configuration against CloudFormation Guard rules.
    
    Args:
        resource_type: The resource type (e.g., AWS::S3::Bucket)
        resource_config: The resource configuration to validate
        rule_names: List of rule names to validate against (optional)
    """
    print_section(f"Validating {resource_type} configuration")
    
    print(f"Resource configuration:")
    print(json.dumps(resource_config, indent=2))
    
    request_data = {
        "type_name": resource_type,
        "resource_config": resource_config
    }
    
    if rule_names:
        request_data["rule_names"] = rule_names
        print(f"Validating against rules: {', '.join(rule_names)}")
    else:
        print("Validating against all available rules")
    
    response = requests.post(
        f"{MCP_SERVER_URL}/validate",
        json=request_data
    )
    
    if response.status_code != 200:
        print(f"Error validating resource: {response.text}")
        return False
    
    result = response.json()
    is_valid = result.get("valid", False)
    validation_results = result.get("results", [])
    
    print(f"Validation result: {'VALID' if is_valid else 'INVALID'}")
    
    for i, result in enumerate(validation_results, 1):
        rule_file = result.get("rule_file", "unknown")
        valid = result.get("valid", False)
        status = result.get("status", "unknown")
        
        print(f"\nRule {i}: {rule_file}")
        print(f"  Status: {status}")
        print(f"  Valid: {valid}")
        
        if "details" in result:
            print("  Details:")
            for detail in result["details"]:
                rule_name = detail.get("rule_name", "unknown")
                detail_status = detail.get("status", "unknown")
                message = detail.get("message", "No message")
                
                print(f"    - Rule: {rule_name}")
                print(f"      Status: {detail_status}")
                if message != "No message":
                    print(f"      Message: {message}")
    
    return is_valid

def validate_with_natural_language(text):
    """
    Validate a resource using natural language.
    
    Args:
        text: The natural language text describing the resource to validate
    """
    print_section("Validating with natural language")
    
    print(f"Natural language request: {text}")
    
    response = requests.post(
        f"{MCP_SERVER_URL}/llm/validate",
        json={
            "text": text
        }
    )
    
    if response.status_code != 200:
        print(f"Error validating with natural language: {response.text}")
        return False
    
    result = response.json()
    llm_response = result.get("response", "No response")
    resource_config = result.get("resource_config", {})
    validation_results = result.get("validation_results", {})
    
    print("\nResource configuration extracted from natural language:")
    print(json.dumps(resource_config, indent=2))
    
    print("\nValidation results:")
    print(f"Valid: {validation_results.get('valid', False)}")
    
    print("\nNatural language response:")
    print(llm_response)
    
    return validation_results.get("valid", False)

def create_compliant_resource():
    """Create a compliant S3 bucket resource."""
    print_section("Creating a compliant S3 bucket resource")
    
    # Get a template for an S3 bucket
    response = requests.get(f"{MCP_SERVER_URL}/templates/AWS::S3::Bucket")
    
    if response.status_code != 200:
        print(f"Error getting template: {response.text}")
        return None
    
    template = response.json().get("template", {})
    
    # Make the resource compliant with all example rules
    template["BucketName"] = "my-compliant-bucket"
    
    # Add encryption
    template["BucketEncryption"] = {
        "ServerSideEncryptionConfiguration": [
            {
                "ServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }
        ]
    }
    
    # Add versioning
    template["VersioningConfiguration"] = {
        "Status": "Enabled"
    }
    
    # Add public access block
    template["PublicAccessBlockConfiguration"] = {
        "BlockPublicAcls": True,
        "BlockPublicPolicy": True,
        "IgnorePublicAcls": True,
        "RestrictPublicBuckets": True
    }
    
    # Add logging
    template["LoggingConfiguration"] = {
        "DestinationBucketName": "my-logging-bucket",
        "LogFilePrefix": "logs/"
    }
    
    print("Compliant S3 bucket configuration:")
    print(json.dumps(template, indent=2))
    
    # Validate the compliant resource
    validate_resource_config("AWS::S3::Bucket", template)
    
    return template

def create_non_compliant_resource():
    """Create a non-compliant S3 bucket resource."""
    print_section("Creating a non-compliant S3 bucket resource")
    
    # Get a template for an S3 bucket
    response = requests.get(f"{MCP_SERVER_URL}/templates/AWS::S3::Bucket")
    
    if response.status_code != 200:
        print(f"Error getting template: {response.text}")
        return None
    
    template = response.json().get("template", {})
    
    # Make the resource non-compliant (missing required configurations)
    template["BucketName"] = "my-non-compliant-bucket"
    
    # No encryption, versioning, public access block, or logging
    
    print("Non-compliant S3 bucket configuration:")
    print(json.dumps(template, indent=2))
    
    # Validate the non-compliant resource
    validate_resource_config("AWS::S3::Bucket", template)
    
    return template

def main():
    """Run the policy validation example."""
    parser = argparse.ArgumentParser(description="Policy validation example for the MCP server")
    parser.add_argument("--create-rule", action="store_true", help="Create a custom rule")
    parser.add_argument("--compliant", action="store_true", help="Create and validate a compliant resource")
    parser.add_argument("--non-compliant", action="store_true", help="Create and validate a non-compliant resource")
    parser.add_argument("--natural-language", type=str, help="Validate a resource using natural language")
    
    args = parser.parse_args()
    
    # Generate example rules if they don't exist
    rules = list_rules()
    if not rules:
        generate_example_rules()
        rules = list_rules()
    
    # Get content of a rule
    if rules:
        get_rule_content(rules[0])
    
    # Create a custom rule if requested
    if args.create_rule:
        create_custom_rule()
    
    # Create and validate a compliant resource if requested
    if args.compliant:
        create_compliant_resource()
    
    # Create and validate a non-compliant resource if requested
    if args.non_compliant:
        create_non_compliant_resource()
    
    # Validate a resource using natural language if requested
    if args.natural_language:
        validate_with_natural_language(args.natural_language)
    
    # If no specific action is requested, run the full example
    if not (args.create_rule or args.compliant or args.non_compliant or args.natural_language):
        # Create a custom rule
        create_custom_rule()
        
        # Create and validate a compliant resource
        create_compliant_resource()
        
        # Create and validate a non-compliant resource
        create_non_compliant_resource()
        
        # Validate a resource using natural language
        validate_with_natural_language(
            "Validate an S3 bucket with versioning enabled but no encryption"
        )

if __name__ == "__main__":
    print("Policy Validation Example")
    print("Usage: python policy_validation.py [options]")
    print("Options:")
    print("  --create-rule         Create a custom rule")
    print("  --compliant           Create and validate a compliant resource")
    print("  --non-compliant       Create and validate a non-compliant resource")
    print("  --natural-language    Validate a resource using natural language")
    print("\nStarting example...")
    main() 