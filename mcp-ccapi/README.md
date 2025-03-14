# MCP Server for AWS CloudControl API

This project implements a Model-Cloud-Provisioning (MCP) server that allows Large Language Models (LLMs) to create and manage AWS cloud resources using the AWS CloudControl API.

## Overview

The MCP server provides a RESTful API that LLMs can use to:

1. Request the creation of AWS resources
2. Check the status of resource creation requests
3. List existing resources
4. Update resource properties
5. Delete resources

The server acts as a middleware between LLMs and AWS CloudControl API, providing a simplified interface for cloud resource provisioning.

## Architecture

- **FastAPI Backend**: Provides RESTful endpoints for resource management
- **AWS CloudControl API**: Used to provision and manage AWS resources
- **Schema Manager**: Loads and manages CloudFormation resource provider schemas
- **LLM Interface**: Processes natural language requests from LLMs

## Key Features

- **Schema-based Resource Creation**: Uses CloudFormation resource provider schemas to validate and create resources
- **Natural Language Interface**: Allows LLMs to create resources using natural language
- **Resource Templates**: Generates templates for resources based on their schemas
- **Schema Management**: Downloads and manages CloudFormation resource provider schemas

## Getting Started

### Prerequisites

- Python 3.8+
- AWS account with appropriate permissions
- AWS credentials configured

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure AWS credentials:
   ```
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_REGION=your_region
   ```
   Or create a `.env` file with these variables.

### Running the Server

```
cd mcp-ccapi
python run.py
```

The API will be available at http://localhost:8000

## API Documentation

Once the server is running, you can access the API documentation at http://localhost:8000/docs

## Example Usage

### Creating an S3 Bucket Using Schema-Based Approach

```bash
# Download common schemas
python examples/schema_based_resource.py --download-schemas --list-types

# Create an S3 bucket
python examples/schema_based_resource.py --type AWS::S3::Bucket --name my-example-bucket --execute
```

### Creating an S3 Bucket Using Natural Language

```python
import requests

response = requests.post(
    "http://localhost:8000/llm/resources",
    json={
        "text": "Create an S3 bucket with name 'my-example-bucket' and versioning enabled",
        "execute": True
    }
)

print(response.json())
```

## Schema Management

The MCP server uses CloudFormation resource provider schemas to validate and create resources. These schemas are downloaded from AWS CloudFormation registry and stored locally in the `schemas` directory.

You can download schemas for commonly used resource types:

```bash
curl -X POST "http://localhost:8000/schemas/download?common_only=true"
```

Or download schemas for all available resource types:

```bash
curl -X POST "http://localhost:8000/schemas/download?common_only=false"
```

## License

MIT 