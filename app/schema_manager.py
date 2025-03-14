"""
CloudFormation resource provider schema manager.

This module provides functionality to load, validate, and use CloudFormation resource provider schemas.
These schemas define the structure and properties of AWS resources that can be created and managed
through the CloudControl API.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Set
import boto3
import requests
import re

logger = logging.getLogger(__name__)

class SchemaManager:
    """
    Manager for CloudFormation resource provider schemas.
    
    This class handles loading schemas from local files or downloading them from AWS,
    validating resource configurations against schemas, and providing information about
    available resource types.
    """
    
    def __init__(self, schema_dir: str = "schemas"):
        """
        Initialize the schema manager.
        
        Args:
            schema_dir: Directory where schemas are stored
        """
        self.schema_dir = schema_dir
        self.schemas: Dict[str, Any] = {}
        self.loaded_schemas: Set[str] = set()
        
        # Create schema directory if it doesn't exist
        os.makedirs(self.schema_dir, exist_ok=True)
        
        # Load schemas from local files
        self._load_local_schemas()
    
    def _load_local_schemas(self) -> None:
        """Load schemas from local files."""
        if not os.path.exists(self.schema_dir):
            logger.warning(f"Schema directory {self.schema_dir} does not exist")
            return
        
        for filename in os.listdir(self.schema_dir):
            if filename.endswith(".json"):
                try:
                    schema_path = os.path.join(self.schema_dir, filename)
                    with open(schema_path, "r") as f:
                        schema = json.load(f)
                    
                    # Extract type name from filename (e.g., AWS-S3-Bucket.json -> AWS::S3::Bucket)
                    type_name = filename.replace(".json", "").replace("-", "::")
                    self.schemas[type_name] = schema
                    self.loaded_schemas.add(type_name)
                    logger.info(f"Loaded schema for {type_name}")
                except Exception as e:
                    logger.error(f"Error loading schema from {filename}: {str(e)}")
    
    def download_schema(self, type_name: str) -> bool:
        """
        Download a schema from AWS CloudFormation registry.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            
        Returns:
            True if the schema was downloaded successfully, False otherwise
        """
        try:
            # Convert type name to filename format (e.g., AWS::S3::Bucket -> AWS-S3-Bucket.json)
            filename = type_name.replace("::", "-") + ".json"
            schema_path = os.path.join(self.schema_dir, filename)
            
            # Check if schema already exists locally
            if os.path.exists(schema_path):
                logger.info(f"Schema for {type_name} already exists locally")
                return True
            
            # Download schema from AWS CloudFormation registry
            cfn_client = boto3.client('cloudformation')
            response = cfn_client.describe_type(
                Type='RESOURCE',
                TypeName=type_name
            )
            
            schema_data = response.get('Schema')
            if not schema_data:
                logger.error(f"No schema found for {type_name}")
                return False
            
            # Parse the schema
            schema = json.loads(schema_data)
            
            # Save schema to local file
            with open(schema_path, "w") as f:
                json.dump(schema, f, indent=2)
            
            # Add schema to in-memory cache
            self.schemas[type_name] = schema
            self.loaded_schemas.add(type_name)
            
            logger.info(f"Downloaded schema for {type_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error downloading schema for {type_name}: {str(e)}")
            return False
    
    def get_schema(self, type_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema for a resource type.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            
        Returns:
            The schema if found, None otherwise
        """
        # Check if schema is already loaded
        if type_name in self.schemas:
            return self.schemas[type_name]
        
        # Try to download schema
        if self.download_schema(type_name):
            return self.schemas[type_name]
        
        return None
    
    def get_property_types(self, type_name: str) -> Dict[str, Any]:
        """
        Get the property types for a resource type.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            
        Returns:
            Dictionary of property types
        """
        schema = self.get_schema(type_name)
        if not schema:
            return {}
        
        # Extract property types from schema
        definitions = schema.get('definitions', {})
        properties = {}
        
        for key, value in definitions.items():
            if key.endswith('Properties'):
                properties = value.get('properties', {})
                break
        
        return properties
    
    def get_required_properties(self, type_name: str) -> List[str]:
        """
        Get the required properties for a resource type.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            
        Returns:
            List of required property names
        """
        schema = self.get_schema(type_name)
        if not schema:
            return []
        
        # Extract required properties from schema
        definitions = schema.get('definitions', {})
        required = []
        
        for key, value in definitions.items():
            if key.endswith('Properties'):
                required = value.get('required', [])
                break
        
        return required
    
    def validate_resource_config(self, type_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a resource configuration against its schema.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            config: The resource configuration
            
        Returns:
            Dictionary with validation results
        """
        schema = self.get_schema(type_name)
        if not schema:
            return {"valid": False, "errors": [f"No schema found for {type_name}"]}
        
        # Get required properties
        required_props = self.get_required_properties(type_name)
        
        # Check if all required properties are present
        missing_props = [prop for prop in required_props if prop not in config]
        if missing_props:
            return {
                "valid": False,
                "errors": [f"Missing required properties: {', '.join(missing_props)}"]
            }
        
        # TODO: Add more validation logic based on property types
        
        return {"valid": True, "errors": []}
    
    def generate_resource_template(self, type_name: str, include_optional: bool = False) -> Dict[str, Any]:
        """
        Generate a template for a resource type.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            include_optional: Whether to include optional properties
            
        Returns:
            Dictionary with the resource template
        """
        schema = self.get_schema(type_name)
        if not schema:
            return {}
        
        # Get property types and required properties
        property_types = self.get_property_types(type_name)
        required_props = self.get_required_properties(type_name)
        
        # Generate template
        template = {}
        
        for prop_name, prop_schema in property_types.items():
            if prop_name in required_props or include_optional:
                # Generate a default value based on the property type
                template[prop_name] = self._generate_default_value(prop_schema)
        
        return template
    
    def _generate_default_value(self, prop_schema: Dict[str, Any]) -> Any:
        """
        Generate a default value for a property based on its schema.
        
        Args:
            prop_schema: The property schema
            
        Returns:
            A default value for the property
        """
        prop_type = prop_schema.get('type')
        
        if prop_type == 'string':
            return ""
        elif prop_type == 'integer' or prop_type == 'number':
            return 0
        elif prop_type == 'boolean':
            return False
        elif prop_type == 'array':
            return []
        elif prop_type == 'object':
            return {}
        else:
            return None
    
    def list_available_resource_types(self) -> List[str]:
        """
        List all available resource types.
        
        Returns:
            List of resource type names
        """
        return list(self.loaded_schemas)
    
    def search_resource_types(self, query: str) -> List[str]:
        """
        Search for resource types matching a query.
        
        Args:
            query: The search query
            
        Returns:
            List of matching resource type names
        """
        query = query.lower()
        return [
            type_name for type_name in self.loaded_schemas
            if query in type_name.lower()
        ]
    
    def download_common_schemas(self) -> None:
        """Download schemas for commonly used resource types."""
        common_types = [
            "AWS::S3::Bucket",
            "AWS::DynamoDB::Table",
            "AWS::Lambda::Function",
            "AWS::EC2::Instance",
            "AWS::IAM::Role",
            "AWS::SNS::Topic",
            "AWS::SQS::Queue",
            "AWS::CloudFront::Distribution",
            "AWS::RDS::DBInstance",
            "AWS::ElasticLoadBalancingV2::LoadBalancer"
        ]
        
        for type_name in common_types:
            self.download_schema(type_name)
    
    def download_all_schemas(self) -> None:
        """Download schemas for all available resource types."""
        try:
            # Get list of all resource types
            cfn_client = boto3.client('cloudformation')
            paginator = cfn_client.get_paginator('list_types')
            
            for page in paginator.paginate(Type='RESOURCE', Visibility='PUBLIC'):
                for type_summary in page.get('TypeSummaries', []):
                    type_name = type_summary.get('TypeName')
                    if type_name:
                        self.download_schema(type_name)
        
        except Exception as e:
            logger.error(f"Error downloading all schemas: {str(e)}")
    
    def get_resource_identifier_property(self, type_name: str) -> Optional[str]:
        """
        Get the property that serves as the resource identifier.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            
        Returns:
            The name of the identifier property, or None if not found
        """
        schema = self.get_schema(type_name)
        if not schema:
            return None
        
        # Look for primaryIdentifier in the schema
        primary_identifier = schema.get('primaryIdentifier', [])
        if primary_identifier and isinstance(primary_identifier, list) and len(primary_identifier) > 0:
            # Extract property name from the identifier path (e.g., /properties/BucketName -> BucketName)
            identifier_path = primary_identifier[0]
            match = re.search(r'/properties/(\w+)', identifier_path)
            if match:
                return match.group(1)
        
        # Fallback to common identifier properties
        common_identifiers = {
            "AWS::S3::Bucket": "BucketName",
            "AWS::DynamoDB::Table": "TableName",
            "AWS::Lambda::Function": "FunctionName",
            "AWS::EC2::Instance": "InstanceId"
        }
        
        return common_identifiers.get(type_name) 