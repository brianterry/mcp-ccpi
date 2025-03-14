# MCP Server for AWS CloudControl API

A Model-Cloud-Provisioning (MCP) server that enables Large Language Models (LLMs) to create and manage AWS cloud resources using Python.

## Overview

The MCP server provides a RESTful API that allows LLMs to:

1. Create, read, update, and delete AWS resources using the AWS CloudControl API
2. Process natural language requests to manage cloud resources
3. Access resource schemas and templates
4. Validate resource configurations against schemas

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
│   └── natural_language_demo.py # Demo of natural language interface
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