# MCP Server for AWS CloudControl API

A Model-Cloud-Provisioning (MCP) server that enables Large Language Models (LLMs) to create and manage AWS cloud resources using Python.

## Overview

The MCP server provides a RESTful API that allows LLMs to:

1. Create, read, update, and delete AWS resources using the AWS CloudControl API
2. Process natural language requests to manage cloud resources
3. Access resource schemas and templates
4. Validate resource configurations against schemas

## Architecture

The following diagram illustrates how an LLM interacts with the MCP server to manage AWS resources:

```
┌─────────┐     Natural Language      ┌─────────────┐      REST API       ┌─────────────┐
│         │    Request (e.g. "Create  │             │    (CloudControl    │             │
│   LLM   │ ─────────────────────────>│  MCP Server │ ─────────────────── │     AWS     │
│         │    an S3 bucket named     │             │      Wrapper)       │             │
└─────────┘    'my-bucket'")          └──────┬──────┘                     └─────────────┘
     ^                                        │                                  ^
     │                                        │                                  │
     │                                        │                                  │
     │                                        │                                  │
     │         Natural Language               │      CloudControl API            │
     │         Response (e.g. "I've           │      (Create/Read/Update/        │
     └─────────────────────────────────────────      Delete Resources)          │
                created the S3 bucket                                            │
                'my-bucket' for you")                                            │
                                                                                 │
                                                                                 │
┌─────────────────────────────────────────────────────────────────┐             │
│                                                                 │             │
│                      MCP Server Components                      │             │
│                                                                 │             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │             │
│  │                 │    │                 │    │             │  │             │
│  │  LLM Interface  │    │  REST API       │    │  Schema     │──┼─────────────┘
│  │  (Natural Lang  │    │  Endpoints      │    │  Manager    │  │   (Download Schemas)
│  │   Processing)   │    │  (CRUD Ops)     │    │             │  │
│  │                 │    │                 │    │             │  │
│  └────────┬────────┘    └────────┬────────┘    └─────────────┘  │
│           │                      │                              │
│           │                      │                              │
│           └──────────────────────┼──────────────────────────────┘
│                                  │                               
│                                  │                               
│                                  ▼                               
│                        ┌─────────────────┐                       
│                        │                 │                       
│                        │  CloudControl   │                       
│                        │  Client         │                       
│                        │                 │                       
│                        └─────────────────┘                       
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Flow Description

1. **LLM to MCP Server**: 
   - The LLM sends a natural language request to the MCP server (e.g., "Create an S3 bucket named 'my-bucket'").
   - This request is sent to the `/llm/resources` endpoint.

2. **Natural Language Processing**:
   - The `LLMInterface` component parses the natural language request.
   - It extracts the operation type (CREATE, READ, UPDATE, DELETE), resource type, and properties.
   - It generates a structured resource configuration.

3. **Resource Management**:
   - The server uses the CloudControl client to perform the requested operation.
   - For resource creation/updates, the `SchemaManager` validates the configuration against the resource schema.

4. **AWS Interaction**:
   - The CloudControl API client sends the appropriate API calls to AWS.
   - AWS processes the request and returns the result.

5. **Response to LLM**:
   - The MCP server generates a natural language response based on the operation result.
   - This response is sent back to the LLM.

## Features

- **RESTful API**: Provides endpoints for managing AWS resources
- **Natural Language Interface**: Allows LLMs to use natural language to manage resources
- **Schema Management**: Downloads, validates, and uses AWS CloudFormation resource schemas
- **Resource Templates**: Generates templates for resource creation
- **Resource Validation**: Validates resource configurations against schemas

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                # Main FastAPI application
│   ├── llm_interface.py       # Natural language interface for LLMs
│   └── schema_manager.py      # Schema management functionality
├── examples/
│   ├── create_s3_bucket.py    # Example script for creating an S3 bucket
│   ├── llm_integration.py     # Example script for LLM integration
│   ├── simple_workflow.py     # Example of a complete workflow
│   ├── natural_language_demo.py # Demo of natural language interface
│   └── schema_management.py   # Example of working with resource schemas
├── schemas/                   # Directory for storing resource schemas
├── tests/
│   ├── __init__.py
│   ├── test_api.py            # Tests for API endpoints
│   └── test_llm_interface.py  # Tests for LLM interface
├── .env.example               # Example environment variables
├── .gitignore                 # Git ignore file
├── README.md                  # Project documentation
├── requirements.txt           # Project dependencies
├── run.py                     # Script to run the server
└── run_tests.py               # Script to run tests
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcp-ccapi.git
   cd mcp-ccapi
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure AWS credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials
   ```

## Usage

### Running the Server

```bash
python run.py
```

The server will be available at http://localhost:8000. API documentation is available at http://localhost:8000/docs.

### Running Tests

```bash
python run_tests.py
```

## Simple Example Flow

Here's a simple example flow demonstrating how to use the MCP server:

### 1. Start the Server

```bash
python run.py
```

### 2. Run the Simple Workflow Example

This example demonstrates a complete workflow including creating, reading, and deleting an S3 bucket:

```bash
python examples/simple_workflow.py my-test-bucket
```

The script will:
1. Create an S3 bucket named "my-test-bucket"
2. Check the status of the creation operation
3. Get details of the created bucket
4. List all S3 buckets
5. Delete the bucket

### 3. Use the Natural Language Interface

You can also use natural language to manage resources:

```bash
# Preview mode (doesn't actually create the resource)
python examples/natural_language_demo.py "Create an S3 bucket named my-nl-bucket with versioning enabled"

# Execute mode (actually creates the resource)
python examples/natural_language_demo.py "Create an S3 bucket named my-nl-bucket with versioning enabled" --execute

# List all buckets
python examples/natural_language_demo.py "List all S3 buckets" --execute

# Delete the bucket
python examples/natural_language_demo.py "Delete S3 bucket my-nl-bucket" --execute
```

### 4. Working with Resource Schemas

The schema management example demonstrates how to work with CloudFormation resource schemas:

```bash
# Download common schemas and work with S3 bucket schema
python examples/schema_management.py

# Download all schemas (this may take some time)
python examples/schema_management.py --all

# Include optional properties in the template
python examples/schema_management.py --include-optional

# Create a resource from the template
python examples/schema_management.py --create --name my-schema-bucket
```

## Working with CloudFormation Resource Schemas

The MCP server uses CloudFormation resource schemas to validate resource configurations and generate templates. These schemas define the structure and properties of AWS resources that can be managed through the CloudControl API.

### Downloading Resource Schemas

Before you can create resources, you need to download the corresponding schemas. The MCP server provides endpoints to download schemas:

#### 1. Download Common Schemas

This will download schemas for commonly used resource types like S3 buckets, EC2 instances, Lambda functions, etc.

```bash
curl -X POST "http://localhost:8000/schemas/download?common_only=true"
```

Or using Python:

```python
import requests
requests.post("http://localhost:8000/schemas/download", params={"common_only": True})
```

#### 2. Download All Schemas

This will download schemas for all available resource types (this may take some time):

```bash
curl -X POST "http://localhost:8000/schemas/download?common_only=false"
```

Or using Python:

```python
import requests
requests.post("http://localhost:8000/schemas/download", params={"common_only": False})
```

#### 3. Download a Specific Schema

You can also download a schema for a specific resource type:

```bash
curl -X GET "http://localhost:8000/schemas/AWS::S3::Bucket"
```

Or using Python:

```python
import requests
requests.get("http://localhost:8000/schemas/AWS::S3::Bucket")
```

### Using Resource Schemas

Once you have downloaded the schemas, you can use them to:

#### 1. Generate Resource Templates

Get a template for a resource type to help you create resources:

```bash
curl -X GET "http://localhost:8000/templates/AWS::S3::Bucket"
```

Or using Python:

```python
import requests
response = requests.get("http://localhost:8000/templates/AWS::S3::Bucket")
template = response.json()["template"]
print(template)
```

To include optional properties in the template:

```bash
curl -X GET "http://localhost:8000/templates/AWS::S3::Bucket?include_optional=true"
```

#### 2. List Available Resource Types

List all resource types for which schemas are available:

```bash
curl -X GET "http://localhost:8000/schemas"
```

Or search for specific resource types:

```bash
curl -X GET "http://localhost:8000/schemas?query=s3"
```

#### 3. Validate Resource Configurations

The MCP server automatically validates resource configurations against their schemas when you create or update resources. If the configuration is invalid, the server will return an error with details about the validation failure.

### Example: Creating a Resource Using a Template

1. Get a template for the resource type:

```python
import requests
import json

# Get a template for an S3 bucket
response = requests.get("http://localhost:8000/templates/AWS::S3::Bucket")
template = response.json()["template"]

# Customize the template
template["BucketName"] = "my-unique-bucket-name"
template["VersioningConfiguration"] = {"Status": "Enabled"}

# Create the resource
create_response = requests.post(
    "http://localhost:8000/resources",
    json={
        "type_name": "AWS::S3::Bucket",
        "desired_state": template
    }
)

print(json.dumps(create_response.json(), indent=2))
```

## API Endpoints

### Resources

- `POST /resources`: Create a new resource
- `GET /resources/{type_name}`: List resources of a specific type
- `GET /resources/{type_name}/{identifier}`: Get details of a specific resource
- `PATCH /resources`: Update an existing resource
- `DELETE /resources`: Delete a resource
- `GET /resources/status/{request_token}`: Get the status of a resource request

### LLM Interface

- `POST /llm/resources`: Process a natural language request from an LLM

### Schemas

- `GET /schemas/{type_name}`: Get the schema for a resource type
- `GET /schemas`: List available resource types
- `POST /schemas/download`: Download resource schemas

### Templates

- `GET /templates/{type_name}`: Get a template for a resource type

## AWS CloudControl API

The MCP server uses the AWS CloudControl API to manage AWS resources. The CloudControl API provides a unified API for creating, reading, updating, and deleting resources across AWS services.

For more information, see the [AWS CloudControl API documentation](https://docs.aws.amazon.com/cloudcontrolapi/latest/userguide/what-is-cloudcontrolapi.html).

## License

This project is licensed under the MIT License - see the LICENSE file for details. 