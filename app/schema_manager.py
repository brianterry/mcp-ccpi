"""
Schema Manager module for the MCP server.

This module provides functionality to manage AWS CloudFormation resource schemas,
including downloading, validating, and generating templates from schemas.
"""

import os
import json
import logging
import re
import boto3
import jsonschema
from typing import Dict, Any, List, Optional, Union
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaManager:
    """
    Manager for AWS CloudFormation resource schemas.
    """
    
    def __init__(self, schemas_dir: str = None):
        """
        Initialize the schema manager.
        
        Args:
            schemas_dir: Directory to store schemas (default: ./schemas)
        """
        self.schemas_dir = schemas_dir or os.path.join(os.getcwd(), "schemas")
        
        # Create schemas directory if it doesn't exist
        if not os.path.exists(self.schemas_dir):
            os.makedirs(self.schemas_dir)
        
        # Initialize CloudFormation client
        self.cfn_client = boto3.client('cloudformation')
        
        # Common resource types
        self.common_resource_types = [
            "AWS::S3::Bucket",
            "AWS::EC2::Instance",
            "AWS::Lambda::Function",
            "AWS::DynamoDB::Table",
            "AWS::RDS::DBInstance",
            "AWS::SNS::Topic",
            "AWS::SQS::Queue",
            "AWS::IAM::Role",
            "AWS::CloudFront::Distribution",
            "AWS::ApiGateway::RestApi",
            "AWS::ElasticLoadBalancingV2::LoadBalancer",
            "AWS::ElasticLoadBalancingV2::TargetGroup",
            "AWS::CloudWatch::Alarm",
            "AWS::Route53::RecordSet",
            "AWS::EC2::SecurityGroup",
            "AWS::EC2::VPC",
            "AWS::EC2::Subnet",
            "AWS::EC2::RouteTable",
            "AWS::EC2::InternetGateway",
            "AWS::KMS::Key"
        ]
    
    def get_schema_path(self, type_name: str) -> str:
        """
        Get the file path for a schema.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            
        Returns:
            The file path for the schema
        """
        # Replace colons with underscores for file name
        file_name = type_name.replace("::", "_") + ".json"
        return os.path.join(self.schemas_dir, file_name)
    
    def get_schema(self, type_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a schema for a resource type.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            
        Returns:
            The schema as a dictionary, or None if not found
        """
        schema_path = self.get_schema_path(type_name)
        
        if os.path.exists(schema_path):
            try:
                with open(schema_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading schema for {type_name}: {str(e)}")
                return None
        else:
            return None
    
    def download_schema(self, type_name: str) -> bool:
        """
        Download a schema for a resource type.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the schema from CloudFormation
            response = self.cfn_client.describe_type(
                Type='RESOURCE',
                TypeName=type_name
            )
            
            # Extract the schema
            schema_str = response.get('Schema')
            if not schema_str:
                logger.error(f"No schema found for {type_name}")
                return False
            
            # Parse the schema
            schema = json.loads(schema_str)
            
            # Save the schema to file
            schema_path = self.get_schema_path(type_name)
            with open(schema_path, 'w') as f:
                json.dump(schema, f, indent=2)
            
            logger.info(f"Downloaded schema for {type_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading schema for {type_name}: {str(e)}")
            return False
    
    def download_common_schemas(self) -> None:
        """
        Download schemas for common resource types.
        """
        for type_name in self.common_resource_types:
            self.download_schema(type_name)
    
    def download_all_schemas(self) -> None:
        """
        Download schemas for all available resource types.
        """
        try:
            # Get all resource types
            paginator = self.cfn_client.get_paginator('list_types')
            
            for page in paginator.paginate(Type='RESOURCE', Visibility='PUBLIC'):
                for type_summary in page.get('TypeSummaries', []):
                    type_name = type_summary.get('TypeName')
                    if type_name:
                        self.download_schema(type_name)
            
            logger.info("Downloaded all available schemas")
            
        except Exception as e:
            logger.error(f"Error downloading all schemas: {str(e)}")
    
    def list_available_resource_types(self) -> List[str]:
        """
        List all available resource types.
        
        Returns:
            A list of resource type names
        """
        resource_types = []
        
        # Check local schemas directory
        for file_name in os.listdir(self.schemas_dir):
            if file_name.endswith('.json'):
                # Convert file name to resource type name
                type_name = file_name[:-5].replace('_', '::')
                resource_types.append(type_name)
        
        # If no local schemas, try to get from CloudFormation
        if not resource_types:
            try:
                paginator = self.cfn_client.get_paginator('list_types')
                
                for page in paginator.paginate(Type='RESOURCE', Visibility='PUBLIC'):
                    for type_summary in page.get('TypeSummaries', []):
                        type_name = type_summary.get('TypeName')
                        if type_name:
                            resource_types.append(type_name)
            
            except Exception as e:
                logger.error(f"Error listing resource types from CloudFormation: {str(e)}")
        
        return sorted(resource_types)
    
    def search_resource_types(self, query: str) -> List[str]:
        """
        Search for resource types matching a query.
        
        Args:
            query: The search query
            
        Returns:
            A list of matching resource type names
        """
        all_types = self.list_available_resource_types()
        
        # Convert query to lowercase for case-insensitive search
        query_lower = query.lower()
        
        # Filter types that match the query
        matching_types = [
            type_name for type_name in all_types
            if query_lower in type_name.lower()
        ]
        
        return matching_types
    
    def validate_resource_config(self, type_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a resource configuration against its schema.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            config: The resource configuration
            
        Returns:
            A dictionary with validation results
        """
        # Get the schema
        schema = self.get_schema(type_name)
        if not schema:
            # Try to download the schema
            if not self.download_schema(type_name):
                return {
                    "valid": False,
                    "errors": [f"Schema not found for resource type: {type_name}"]
                }
            schema = self.get_schema(type_name)
        
        # Extract the properties schema
        properties_schema = schema.get('properties', {}).get('Properties', {})
        
        # Validate the configuration
        try:
            jsonschema.validate(instance=config, schema=properties_schema)
            return {
                "valid": True
            }
        except jsonschema.exceptions.ValidationError as e:
            return {
                "valid": False,
                "errors": [str(e)]
            }
    
    def generate_resource_template(self, type_name: str, include_optional: bool = False) -> Optional[Dict[str, Any]]:
        """
        Generate a template for a resource type.
        
        Args:
            type_name: The resource type name (e.g., AWS::S3::Bucket)
            include_optional: Whether to include optional properties
            
        Returns:
            A template dictionary, or None if the schema is not found
        """
        # Get the schema
        schema = self.get_schema(type_name)
        if not schema:
            # Try to download the schema
            if not self.download_schema(type_name):
                return None
            schema = self.get_schema(type_name)
        
        # Extract the properties schema
        properties_schema = schema.get('properties', {}).get('Properties', {}).get('properties', {})
        
        # Generate template
        template = {}
        
        for prop_name, prop_schema in properties_schema.items():
            # Skip optional properties if not including them
            if not include_optional and not self._is_required_property(prop_name, schema):
                continue
            
            # Generate a value for the property
            template[prop_name] = self._generate_property_value(prop_schema)
        
        return template
    
    def _is_required_property(self, prop_name: str, schema: Dict[str, Any]) -> bool:
        """
        Check if a property is required.
        
        Args:
            prop_name: The property name
            schema: The resource schema
            
        Returns:
            True if the property is required, False otherwise
        """
        required_props = schema.get('properties', {}).get('Properties', {}).get('required', [])
        return prop_name in required_props
    
    def _generate_property_value(self, prop_schema: Dict[str, Any]) -> Any:
        """
        Generate a value for a property based on its schema.
        
        Args:
            prop_schema: The property schema
            
        Returns:
            A generated value for the property
        """
        prop_type = prop_schema.get('type')
        
        if prop_type == 'string':
            # For strings, use the default or an example value
            if 'default' in prop_schema:
                return prop_schema['default']
            elif 'enum' in prop_schema and prop_schema['enum']:
                return prop_schema['enum'][0]
            else:
                return "example-value"
        
        elif prop_type == 'integer' or prop_type == 'number':
            # For numbers, use the default or a reasonable value
            if 'default' in prop_schema:
                return prop_schema['default']
            elif 'minimum' in prop_schema:
                return prop_schema['minimum']
            else:
                return 0
        
        elif prop_type == 'boolean':
            # For booleans, use the default or False
            return prop_schema.get('default', False)
        
        elif prop_type == 'array':
            # For arrays, create an empty array or an array with one item
            items_schema = prop_schema.get('items', {})
            if 'type' in items_schema:
                return [self._generate_property_value(items_schema)]
            else:
                return []
        
        elif prop_type == 'object':
            # For objects, recursively generate properties
            obj = {}
            for sub_prop_name, sub_prop_schema in prop_schema.get('properties', {}).items():
                # Only include required properties
                if sub_prop_name in prop_schema.get('required', []):
                    obj[sub_prop_name] = self._generate_property_value(sub_prop_schema)
            return obj
        
        # Default case
        return None 