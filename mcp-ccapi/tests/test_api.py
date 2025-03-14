"""
Tests for the API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)

def test_health_endpoint():
    """Test the health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@patch("boto3.client")
def test_create_resource(mock_boto_client):
    """Test creating a resource."""
    # Mock the CloudControl client
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    
    # Mock the response from CloudControl API
    mock_client.create_resource.return_value = {
        "ProgressEvent": {
            "RequestToken": "test-token",
            "Operation": "CREATE",
            "OperationStatus": "IN_PROGRESS",
            "TypeName": "AWS::S3::Bucket",
            "Identifier": "test-bucket"
        }
    }
    
    # Test request
    request_data = {
        "type_name": "AWS::S3::Bucket",
        "desired_state": {
            "BucketName": "test-bucket"
        }
    }
    
    response = client.post("/resources", json=request_data)
    
    assert response.status_code == 200
    assert response.json()["request_token"] == "test-token"
    assert response.json()["operation"] == "CREATE"
    assert response.json()["operation_status"] == "IN_PROGRESS"
    assert response.json()["type_name"] == "AWS::S3::Bucket"
    assert response.json()["identifier"] == "test-bucket"
    
    # Verify the CloudControl client was called with the correct parameters
    mock_client.create_resource.assert_called_once()
    call_args = mock_client.create_resource.call_args[1]
    assert call_args["TypeName"] == "AWS::S3::Bucket"
    assert "test-bucket" in call_args["DesiredState"]

@patch("boto3.client")
def test_get_resource_request_status(mock_boto_client):
    """Test getting the status of a resource request."""
    # Mock the CloudControl client
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    
    # Mock the response from CloudControl API
    mock_client.get_resource_request_status.return_value = {
        "ProgressEvent": {
            "RequestToken": "test-token",
            "Operation": "CREATE",
            "OperationStatus": "SUCCESS",
            "TypeName": "AWS::S3::Bucket",
            "Identifier": "test-bucket"
        }
    }
    
    response = client.get("/resources/status/test-token")
    
    assert response.status_code == 200
    assert response.json()["request_token"] == "test-token"
    assert response.json()["operation"] == "CREATE"
    assert response.json()["operation_status"] == "SUCCESS"
    assert response.json()["type_name"] == "AWS::S3::Bucket"
    assert response.json()["identifier"] == "test-bucket"
    
    # Verify the CloudControl client was called with the correct parameters
    mock_client.get_resource_request_status.assert_called_once_with(RequestToken="test-token")

@patch("boto3.client")
def test_list_resources(mock_boto_client):
    """Test listing resources of a specific type."""
    # Mock the CloudControl client
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    
    # Mock the response from CloudControl API
    mock_client.list_resources.return_value = {
        "ResourceDescriptions": [
            {
                "Identifier": "bucket1",
                "Properties": '{"Name":"bucket1"}'
            },
            {
                "Identifier": "bucket2",
                "Properties": '{"Name":"bucket2"}'
            }
        ]
    }
    
    response = client.get("/resources/AWS::S3::Bucket")
    
    assert response.status_code == 200
    assert response.json()["type_name"] == "AWS::S3::Bucket"
    assert len(response.json()["resources"]) == 2
    assert response.json()["resources"][0]["identifier"] == "bucket1"
    assert response.json()["resources"][1]["identifier"] == "bucket2"
    
    # Verify the CloudControl client was called with the correct parameters
    mock_client.list_resources.assert_called_once_with(TypeName="AWS::S3::Bucket")

@patch("boto3.client")
def test_natural_language_request_preview(mock_boto_client):
    """Test processing a natural language request in preview mode."""
    # Mock the CloudControl client
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    
    # Test request
    request_data = {
        "text": "Create an S3 bucket with name 'test-bucket' and versioning enabled",
        "execute": False
    }
    
    response = client.post("/llm/resources", json=request_data)
    
    assert response.status_code == 200
    assert "I'll create an S3 bucket named 'test-bucket'" in response.json()["response"]
    assert "Versioning: enabled" in response.json()["response"]
    assert response.json()["resource_config"]["type_name"] == "AWS::S3::Bucket"
    assert response.json()["resource_config"]["desired_state"]["BucketName"] == "test-bucket"
    assert response.json()["result"] is None
    
    # Verify the CloudControl client was not called
    mock_client.create_resource.assert_not_called()

@patch("boto3.client")
def test_natural_language_request_execute(mock_boto_client):
    """Test processing a natural language request in execute mode."""
    # Mock the CloudControl client
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    
    # Mock the response from CloudControl API
    mock_client.create_resource.return_value = {
        "ProgressEvent": {
            "RequestToken": "test-token",
            "Operation": "CREATE",
            "OperationStatus": "IN_PROGRESS",
            "TypeName": "AWS::S3::Bucket",
            "Identifier": "test-bucket"
        }
    }
    
    # Test request
    request_data = {
        "text": "Create an S3 bucket with name 'test-bucket' and versioning enabled",
        "execute": True
    }
    
    response = client.post("/llm/resources", json=request_data)
    
    assert response.status_code == 200
    assert "I've started the CREATE operation" in response.json()["response"]
    assert "test-bucket" in response.json()["response"]
    assert response.json()["resource_config"]["type_name"] == "AWS::S3::Bucket"
    assert response.json()["resource_config"]["desired_state"]["BucketName"] == "test-bucket"
    assert response.json()["result"]["request_token"] == "test-token"
    assert response.json()["result"]["operation"] == "CREATE"
    assert response.json()["result"]["operation_status"] == "IN_PROGRESS"
    
    # Verify the CloudControl client was called with the correct parameters
    mock_client.create_resource.assert_called_once()
    call_args = mock_client.create_resource.call_args[1]
    assert call_args["TypeName"] == "AWS::S3::Bucket"
    assert "test-bucket" in call_args["DesiredState"] 