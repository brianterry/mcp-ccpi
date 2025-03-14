"""
CloudFormation Guard validator module.

This module provides functionality to validate AWS resource configurations
against policy rules using AWS CloudFormation Guard.
"""

import os
import json
import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

# Import the CloudFormation Guard Python wrapper
try:
    from cfn_guard_rs_python import Guard
except ImportError:
    logging.error("cfn-guard-rs-python package not installed. Please install it with pip.")
    raise

class GuardValidator:
    """
    CloudFormation Guard validator for AWS resource configurations.
    
    This class provides methods to validate resource configurations against
    policy rules using AWS CloudFormation Guard.
    """
    
    def __init__(self, rules_dir: str = "rules"):
        """
        Initialize the GuardValidator.
        
        Args:
            rules_dir: Directory containing CloudFormation Guard rule files
        """
        self.rules_dir = rules_dir
        self._ensure_rules_dir_exists()
        self.guard = Guard()
        
    def _ensure_rules_dir_exists(self) -> None:
        """Ensure the rules directory exists."""
        os.makedirs(self.rules_dir, exist_ok=True)
        
    def list_rules(self) -> List[str]:
        """
        List all available rule files.
        
        Returns:
            List of rule file names
        """
        rule_files = []
        for file in Path(self.rules_dir).glob("*.guard"):
            rule_files.append(file.name)
        return rule_files
    
    def get_rule_content(self, rule_name: str) -> Optional[str]:
        """
        Get the content of a rule file.
        
        Args:
            rule_name: Name of the rule file
            
        Returns:
            Content of the rule file or None if not found
        """
        rule_path = Path(self.rules_dir) / rule_name
        if not rule_path.exists() and not rule_name.endswith(".guard"):
            rule_path = Path(self.rules_dir) / f"{rule_name}.guard"
            
        if rule_path.exists():
            return rule_path.read_text()
        return None
    
    def save_rule(self, rule_name: str, rule_content: str) -> bool:
        """
        Save a rule file.
        
        Args:
            rule_name: Name of the rule file
            rule_content: Content of the rule file
            
        Returns:
            True if successful, False otherwise
        """
        if not rule_name.endswith(".guard"):
            rule_name = f"{rule_name}.guard"
            
        rule_path = Path(self.rules_dir) / rule_name
        try:
            rule_path.write_text(rule_content)
            return True
        except Exception as e:
            logging.error(f"Error saving rule file: {e}")
            return False
    
    def delete_rule(self, rule_name: str) -> bool:
        """
        Delete a rule file.
        
        Args:
            rule_name: Name of the rule file
            
        Returns:
            True if successful, False otherwise
        """
        if not rule_name.endswith(".guard"):
            rule_name = f"{rule_name}.guard"
            
        rule_path = Path(self.rules_dir) / rule_name
        if rule_path.exists():
            try:
                rule_path.unlink()
                return True
            except Exception as e:
                logging.error(f"Error deleting rule file: {e}")
                return False
        return False
    
    def validate_resource(
        self, 
        resource_type: str, 
        resource_config: Dict[str, Any], 
        rule_names: Optional[List[str]] = None
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate a resource configuration against policy rules.
        
        Args:
            resource_type: Type of the resource (e.g., AWS::S3::Bucket)
            resource_config: Resource configuration to validate
            rule_names: List of rule file names to validate against (optional)
                        If not provided, all rules will be used
                        
        Returns:
            Tuple of (is_valid, validation_results)
        """
        # Prepare the data for validation
        data = {
            "Resources": {
                "Resource": {
                    "Type": resource_type,
                    "Properties": resource_config
                }
            }
        }
        
        data_json = json.dumps(data)
        
        # Get the rules to validate against
        if rule_names:
            rule_files = [
                str(Path(self.rules_dir) / rule_name if not rule_name.endswith(".guard") 
                    else Path(self.rules_dir) / rule_name)
                for rule_name in rule_names
            ]
        else:
            rule_files = [str(file) for file in Path(self.rules_dir).glob("*.guard")]
            
        if not rule_files:
            return True, [{"message": "No rules found for validation"}]
            
        # Validate the resource configuration
        validation_results = []
        all_valid = True
        
        for rule_file in rule_files:
            if not Path(rule_file).exists():
                validation_results.append({
                    "rule_file": Path(rule_file).name,
                    "valid": True,
                    "message": "Rule file not found"
                })
                continue
                
            try:
                # Run the validation
                rule_content = Path(rule_file).read_text()
                check_result = self.guard.check_string(data_json, rule_content)
                
                # Process the results
                is_valid = check_result.status == "PASS"
                if not is_valid:
                    all_valid = False
                    
                result = {
                    "rule_file": Path(rule_file).name,
                    "valid": is_valid,
                    "status": check_result.status
                }
                
                # Add detailed results if available
                if hasattr(check_result, "rule_results") and check_result.rule_results:
                    result["details"] = []
                    for rule_result in check_result.rule_results:
                        rule_detail = {
                            "rule_name": rule_result.rule_name,
                            "status": rule_result.status
                        }
                        if hasattr(rule_result, "message") and rule_result.message:
                            rule_detail["message"] = rule_result.message
                        result["details"].append(rule_detail)
                        
                validation_results.append(result)
                
            except Exception as e:
                logging.error(f"Error validating resource against rule {rule_file}: {e}")
                validation_results.append({
                    "rule_file": Path(rule_file).name,
                    "valid": False,
                    "error": str(e)
                })
                all_valid = False
                
        return all_valid, validation_results
    
    def generate_example_rules(self) -> None:
        """Generate example rule files if the rules directory is empty."""
        if not list(Path(self.rules_dir).glob("*.guard")):
            # Example rule for S3 bucket encryption
            s3_encryption_rule = """
# Rule to ensure S3 buckets have encryption enabled
rule s3_bucket_encryption_enabled {
    AWS::S3::Bucket {
        # Check if server-side encryption is configured
        BucketEncryption exists
        BucketEncryption is_struct
        
        # Check if SSE-S3 or SSE-KMS is enabled
        BucketEncryption {
            ServerSideEncryptionConfiguration exists
            ServerSideEncryptionConfiguration is_list
            ServerSideEncryptionConfiguration[*] {
                ServerSideEncryptionByDefault exists
            }
        }
    }
}
"""
            self.save_rule("s3_bucket_encryption.guard", s3_encryption_rule)
            
            # Example rule for S3 bucket versioning
            s3_versioning_rule = """
# Rule to ensure S3 buckets have versioning enabled
rule s3_bucket_versioning_enabled {
    AWS::S3::Bucket {
        # Check if versioning is configured and enabled
        VersioningConfiguration exists
        VersioningConfiguration is_struct
        VersioningConfiguration {
            Status exists
            Status == "Enabled"
        }
    }
}
"""
            self.save_rule("s3_bucket_versioning.guard", s3_versioning_rule)
            
            # Example rule for S3 bucket public access block
            s3_public_access_rule = """
# Rule to ensure S3 buckets block public access
rule s3_bucket_public_access_blocked {
    AWS::S3::Bucket {
        # Check if public access block is configured
        PublicAccessBlockConfiguration exists
        PublicAccessBlockConfiguration is_struct
        PublicAccessBlockConfiguration {
            BlockPublicAcls == true
            BlockPublicPolicy == true
            IgnorePublicAcls == true
            RestrictPublicBuckets == true
        }
    }
}
"""
            self.save_rule("s3_bucket_public_access.guard", s3_public_access_rule) 