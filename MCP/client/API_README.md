# Taipei City Dashboard AI API

FastAPI service wrapper for the MCP + Ollama client, providing REST API endpoints for querying the Taipei City Dashboard system.

## Quick Start

### 1. Install Dependencies

```bash
# Make sure you're in the client directory
cd MCP/client

# Install dependencies using uv
uv sync
```

### 2. Start Ollama Service

```bash
# Install Ollama (if not already installed)
# Visit: https://ollama.ai

# Start Ollama service
ollama serve

# Pull a model (in another terminal)
ollama pull qwen3:4b
```

### 3. Start the API Service

```bash
# Option 1: Using the startup script
python start_api.py

# Option 2: Direct uvicorn command
uvicorn api_service:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### GET `/health`

Check system status and connections

**Response:**

```json
{
  "status": "healthy",
  "ollama_connected": true,
  "mcp_server_connected": true,
  "available_models": ["qwen3:4b", "llama2:7b"]
}
```

### POST `/query`

Process a user query using MCP + Ollama integration

**Request:**

```json
{
  "prompt": "告訴我台北市的垃圾車位置",
  "model": "qwen3:4b",
  "ollama_host": "http://localhost:11434"
}
```

**Response:**

```json
{
  "result": "根據系統資料，台北市目前有多個垃圾車運行路線...",
  "status": "success",
  "model_used": "qwen3:4b"
}
```

### GET `/components`

Get available dashboard components

**Response:**

```json
{
  "components": [
    { "index": "1", "name": "垃圾車位置" },
    { "index": "2", "name": "YouBike 站點" }
  ],
  "total_count": 9
}
```

### POST `/components/read`

Read specific components by indices

**Request:**

```json
["1", "2", "3"]
```

**Response:**

```json
{
  "status": "success",
  "result": "Reading component: 1\nReading component: 2\nReading component: 3",
  "queried_indices": ["1", "2", "3"]
}
```

### GET `/models`

Get available Ollama models

**Response:**

```json
{
  "models": [
    {
      "name": "qwen3:4b",
      "size": 2654926849,
      "modified_at": "2024-01-15T10:30:00Z"
    }
  ],
  "current_model": "qwen3:4b",
  "total_count": 1
}
```

## Example Usage with curl

### Health Check

```bash
curl -X GET "http://localhost:8000/health"
```

### Query Processing

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "台北市有多少個YouBike站點？",
    "model": "qwen3:4b"
  }'
```

### Get Components

```bash
curl -X GET "http://localhost:8000/components"
```

### Read Multiple Components

```bash
curl -X POST "http://localhost:8000/components/read" \
  -H "Content-Type: application/json" \
  -d '["1", "2", "3"]'
```

## Example Usage with Python

```python
import requests
import json

# Base URL
base_url = "http://localhost:8000"

# Health check
response = requests.get(f"{base_url}/health")
print("Health:", response.json())

# Process query
query_data = {
    "prompt": "請告訴我台北市的空氣品質狀況",
    "model": "qwen3:4b"
}
response = requests.post(f"{base_url}/query", json=query_data)
print("Query result:", response.json())

# Get components
response = requests.get(f"{base_url}/components")
print("Components:", response.json())

# Read specific components
response = requests.post(f"{base_url}/components/read",
                        json=["1", "2"])
print("Component data:", response.json())
```

## CORS Configuration

The API includes CORS middleware allowing requests from any origin. For production, update the `allow_origins` setting in `api_service.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific domains
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Environment Variables

You can configure the service using environment variables:

```bash
export OLLAMA_HOST=http://localhost:11434
export DEFAULT_MODEL=qwen3:4b
export API_PORT=8000
```

## Development

### Running in Development Mode

```bash
uvicorn api_service:app --reload --port 8000
```

### Testing the API

```bash
# Run the test script
python test_api.py
```

### Logs

The service provides detailed logging. Check the console output for connection status and error messages.

## Troubleshooting

### Common Issues

1. **Ollama connection failed**

   - Ensure Ollama service is running: `ollama serve`
   - Check if the model is available: `ollama list`

2. **MCP server connection failed**

   - Verify the MCP server script path in `api_service.py`
   - Check database connections in the MCP server

3. **Port already in use**

   - Change the port: `uvicorn api_service:app --port 8001`
   - Or kill the process using port 8000

4. **Missing dependencies**
   - Run: `uv sync` to install all required packages

### Debug Mode

Enable debug logging by setting the log level:

```python
logging.basicConfig(level=logging.DEBUG)
```
