"""
Tests for the LLM interface module.
"""

import pytest
from app.llm_interface import LLMInterface

def test_parse_s3_bucket_request():
    """Test parsing a natural language request for an S3 bucket."""
    request_text = "Create an S3 bucket with name 'my-test-bucket' and versioning enabled"
    
    parsed_request = LLMInterface.parse_request(request_text)
    
    assert parsed_request["resource_type"] == "AWS::S3::Bucket"
    assert parsed_request["params"]["bucket_name"] == "my-test-bucket"
    assert parsed_request["params"]["versioning_enabled"] is True

def test_parse_dynamodb_table_request():
    """Test parsing a natural language request for a DynamoDB table."""
    request_text = "Create a DynamoDB table with name 'users-table', partition key 'userId', and read capacity 10"
    
    parsed_request = LLMInterface.parse_request(request_text)
    
    assert parsed_request["resource_type"] == "AWS::DynamoDB::Table"
    assert parsed_request["params"]["table_name"] == "users-table"
    assert parsed_request["params"]["partition_key"] == "userId"
    assert parsed_request["params"]["read_capacity"] == 10

def test_generate_s3_bucket_config():
    """Test generating a resource configuration for an S3 bucket."""
    parsed_request = {
        "resource_type": "AWS::S3::Bucket",
        "params": {
            "bucket_name": "my-test-bucket",
            "versioning_enabled": True,
            "public_access_blocked": True,
            "encryption_enabled": True
        }
    }
    
    resource_config = LLMInterface.generate_resource_config(parsed_request)
    
    assert resource_config["type_name"] == "AWS::S3::Bucket"
    assert resource_config["desired_state"]["BucketName"] == "my-test-bucket"
    assert resource_config["desired_state"]["VersioningConfiguration"]["Status"] == "Enabled"
    assert "PublicAccessBlockConfiguration" in resource_config["desired_state"]
    assert "BucketEncryption" in resource_config["desired_state"]

def test_generate_dynamodb_table_config():
    """Test generating a resource configuration for a DynamoDB table."""
    parsed_request = {
        "resource_type": "AWS::DynamoDB::Table",
        "params": {
            "table_name": "users-table",
            "partition_key": "userId",
            "read_capacity": 10,
            "write_capacity": 5
        }
    }
    
    resource_config = LLMInterface.generate_resource_config(parsed_request)
    
    assert resource_config["type_name"] == "AWS::DynamoDB::Table"
    assert resource_config["desired_state"]["TableName"] == "users-table"
    assert resource_config["desired_state"]["KeySchema"][0]["AttributeName"] == "userId"
    assert resource_config["desired_state"]["ProvisionedThroughput"]["ReadCapacityUnits"] == 10
    assert resource_config["desired_state"]["ProvisionedThroughput"]["WriteCapacityUnits"] == 5

def test_generate_response_preview():
    """Test generating a preview response."""
    resource_config = {
        "type_name": "AWS::S3::Bucket",
        "desired_state": {
            "BucketName": "my-test-bucket",
            "VersioningConfiguration": {
                "Status": "Enabled"
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True
            },
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }
        }
    }
    
    response = LLMInterface.generate_response(resource_config)
    
    assert "my-test-bucket" in response
    assert "Versioning: enabled" in response
    assert "Server-side encryption: enabled" in response
    assert "Public access: blocked" in response
    assert "Would you like me to proceed" in response

def test_generate_response_in_progress():
    """Test generating a response for an in-progress operation."""
    resource_config = {
        "type_name": "AWS::S3::Bucket",
        "desired_state": {
            "BucketName": "my-test-bucket"
        }
    }
    
    result = {
        "request_token": "abc123",
        "operation": "CREATE",
        "operation_status": "IN_PROGRESS",
        "type_name": "AWS::S3::Bucket",
        "identifier": "my-test-bucket"
    }
    
    response = LLMInterface.generate_response(resource_config, result)
    
    assert "started the CREATE operation" in response
    assert "my-test-bucket" in response
    assert "IN_PROGRESS" in response
    assert "abc123" in response

def test_generate_response_error():
    """Test generating a response for an error."""
    resource_config = {
        "error": "Bucket name is required"
    }
    
    response = LLMInterface.generate_response(resource_config)
    
    assert "couldn't create the resource" in response
    assert "Bucket name is required" in response 