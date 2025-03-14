"""
Tests for the schema manager module.
"""

import pytest
import os
import json
from unittest.mock import patch, MagicMock
from app.schema_manager import SchemaManager

@pytest.fixture
def schema_manager():
    """Create a schema manager for testing."""
    # Use a temporary directory for testing
    test_schema_dir = "test_schemas"
    os.makedirs(test_schema_dir, exist_ok=True)
    
    # Create a test schema
    test_schema = {
        "typeName": "AWS::S3::Bucket",
        "description": "Test schema for S3 bucket",
        "primaryIdentifier": [
            "/properties/BucketName"
        ],
        "properties": {
            "BucketName": {
                "type": "string"
            }
        },
        "definitions": {
            "AWS::S3::Bucket.Properties": {
                "properties": {
                    "BucketName": {
                        "type": "string"
                    },
                    "VersioningConfiguration": {
                        "type": "object",
                        "properties": {
                            "Status": {
                                "type": "string"
                            }
                        }
                    }
                },
                "required": [
                    "BucketName"
                ]
            }
        }
    }
    
    # Write the test schema to a file
    with open(os.path.join(test_schema_dir, "AWS-S3-Bucket.json"), "w") as f:
        json.dump(test_schema, f)
    
    # Create the schema manager
    manager = SchemaManager(schema_dir=test_schema_dir)
    
    yield manager
    
    # Clean up
    import shutil
    shutil.rmtree(test_schema_dir)

def test_load_local_schemas(schema_manager):
    """Test loading schemas from local files."""
    assert "AWS::S3::Bucket" in schema_manager.schemas
    assert "AWS::S3::Bucket" in schema_manager.loaded_schemas

def test_get_schema(schema_manager):
    """Test getting a schema."""
    schema = schema_manager.get_schema("AWS::S3::Bucket")
    assert schema is not None
    assert schema["typeName"] == "AWS::S3::Bucket"

def test_get_property_types(schema_manager):
    """Test getting property types."""
    property_types = schema_manager.get_property_types("AWS::S3::Bucket")
    assert "BucketName" in property_types
    assert "VersioningConfiguration" in property_types

def test_get_required_properties(schema_manager):
    """Test getting required properties."""
    required_props = schema_manager.get_required_properties("AWS::S3::Bucket")
    assert "BucketName" in required_props

def test_validate_resource_config_valid(schema_manager):
    """Test validating a valid resource configuration."""
    config = {
        "BucketName": "test-bucket"
    }
    
    result = schema_manager.validate_resource_config("AWS::S3::Bucket", config)
    assert result["valid"] is True
    assert len(result["errors"]) == 0

def test_validate_resource_config_invalid(schema_manager):
    """Test validating an invalid resource configuration."""
    config = {}  # Missing required BucketName
    
    result = schema_manager.validate_resource_config("AWS::S3::Bucket", config)
    assert result["valid"] is False
    assert len(result["errors"]) > 0
    assert "Missing required properties: BucketName" in result["errors"][0]

def test_generate_resource_template(schema_manager):
    """Test generating a resource template."""
    template = schema_manager.generate_resource_template("AWS::S3::Bucket")
    assert "BucketName" in template
    
    # Optional properties should not be included by default
    assert "VersioningConfiguration" not in template
    
    # Include optional properties
    template = schema_manager.generate_resource_template("AWS::S3::Bucket", include_optional=True)
    assert "BucketName" in template
    assert "VersioningConfiguration" in template

def test_get_resource_identifier_property(schema_manager):
    """Test getting the resource identifier property."""
    identifier_prop = schema_manager.get_resource_identifier_property("AWS::S3::Bucket")
    assert identifier_prop == "BucketName"

@patch("boto3.client")
def test_download_schema(mock_boto_client, schema_manager):
    """Test downloading a schema."""
    # Mock the CloudFormation client
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    
    # Mock the response from CloudFormation
    mock_client.describe_type.return_value = {
        "Schema": json.dumps({
            "typeName": "AWS::DynamoDB::Table",
            "description": "Test schema for DynamoDB table",
            "primaryIdentifier": [
                "/properties/TableName"
            ],
            "properties": {
                "TableName": {
                    "type": "string"
                }
            },
            "definitions": {
                "AWS::DynamoDB::Table.Properties": {
                    "properties": {
                        "TableName": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "TableName"
                    ]
                }
            }
        })
    }
    
    # Download the schema
    result = schema_manager.download_schema("AWS::DynamoDB::Table")
    
    assert result is True
    assert "AWS::DynamoDB::Table" in schema_manager.schemas
    assert "AWS::DynamoDB::Table" in schema_manager.loaded_schemas
    
    # Verify the CloudFormation client was called with the correct parameters
    mock_client.describe_type.assert_called_once_with(
        Type='RESOURCE',
        TypeName='AWS::DynamoDB::Table'
    ) 