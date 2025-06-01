"""
FastAPI service wrapper for MCP + Ollama Client
Provides REST API endpoints for querying the Taipei City Dashboard system
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Fix for Windows subprocess issue with asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from client import SimpleMCPOllamaClient
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ollama

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Application state
class AppState:
    """Application state container"""
    def __init__(self):
        self.mcp_client: Optional[SimpleMCPOllamaClient] = None
        self.is_initialized: bool = False

# Global state instance
app_state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting Taipei City Dashboard AI API...")
    
    # Force Windows ProactorEventLoop policy for subprocess support
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            logger.info("✅ Set Windows ProactorEventLoop policy for subprocess support")
        except Exception as e:
            logger.warning(f"⚠️  Failed to set Windows event loop policy: {e}")
    
    try:
        # Initialize MCP + Ollama client
        app_state.mcp_client = SimpleMCPOllamaClient()
        
        # Test connections
        ollama_ok = await app_state.mcp_client.test_ollama_connection()
        if ollama_ok:
            logger.info("✅ Ollama connection established")
        else:
            logger.warning("⚠️  Ollama connection failed")
            
        app_state.is_initialized = True
        logger.info("✅ Application initialized successfully")
        
    except Exception as e:
        logger.error("❌ Failed to initialize application: %s", str(e))
        app_state.is_initialized = False
    
    # Yield control to the application
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Taipei City Dashboard AI API...")
    
    try:
        if app_state.mcp_client:
            # Clean up resources if needed
            logger.info("🧹 Cleaning up resources...")
        
        app_state.mcp_client = None
        app_state.is_initialized = False
        logger.info("✅ Application shutdown completed")
        
    except Exception as e:
        logger.error("❌ Error during shutdown: %s", str(e))

# Pydantic models for API request/response
class QueryRequest(BaseModel):
    prompt: str
    model: Optional[str] = "llama3.2:3b"
    ollama_host: Optional[str] = "http://localhost:11434"

class QueryResponse(BaseModel):
    result: str
    status: str

class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    mcp_server_connected: bool
    available_models: List[str]

class ComponentsResponse(BaseModel):
    components: List[Dict]
    total_count: int

# FastAPI app initialization with lifespan management
app = FastAPI(
    title="Taipei City Dashboard AI API",
    description="REST API for querying Taipei City Dashboard data using MCP + Ollama integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Taipei City Dashboard AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify system status"""
    if not app_state.is_initialized or not app_state.mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    try:
        # Test Ollama connection
        ollama_ok = await app_state.mcp_client.test_ollama_connection()
        
        # Test MCP server connection
        mcp_ok = await app_state.mcp_client.test_mcp_server()
        
        # Get available models
        available_models = []
        try:
            models = app_state.mcp_client.ollama_client.list()
            if isinstance(models, dict) and 'models' in models:
                available_models = [m.get('name', 'unknown') for m in models['models']]
        except Exception as e:
            logger.warning("Failed to get model list: %s", str(e))
        
        return HealthResponse(
            status="healthy" if (ollama_ok and mcp_ok) else "degraded",
            ollama_connected=ollama_ok,
            mcp_server_connected=mcp_ok,
            available_models=available_models
        )
    
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}") from e

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a user query using MCP + Ollama integration
    
    - **prompt**: The user's question or request
    - **model**: Ollama model to use (optional, defaults to llama3.2:3b)
    - **ollama_host**: Ollama host URL (optional, defaults to localhost:11434)
    """
    if not app_state.is_initialized or not app_state.mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    try:
        # Update client configuration if provided
        if request.model != app_state.mcp_client.model:
            app_state.mcp_client.model = request.model
        
        if request.ollama_host != app_state.mcp_client.ollama_host:
            app_state.mcp_client.ollama_host = request.ollama_host
            app_state.mcp_client.ollama_client = ollama.Client(host=request.ollama_host)
        # Process the query
        logger.info("Processing query: %s", request.prompt)
        result = await app_state.mcp_client.process_query(query=request.prompt)
        logger.info("Query processed successfully")
        return QueryResponse(
            result=result,
            status="success"
        )
    
    except Exception as e:
        logger.error("Query processing failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}") from e

@app.get("/components", response_model=ComponentsResponse)
async def get_components():
    """
    Get available dashboard components from the database
    """
    if not app_state.is_initialized or not app_state.mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    try:
        server_params = StdioServerParameters(
            command="python",
            args=["../server/server.py"]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                components = await session.read_resource("components://")
                
                # Parse the components data
                import json
                components_data = json.loads(components.contents[0].text)
                
                return ComponentsResponse(
                    components=components_data.get("components", []),
                    total_count=components_data.get("total_components", 0)
                )
    
    except Exception as e:
        logger.error("Failed to get components: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get components: {str(e)}") from e

@app.post("/components/read")
async def read_components(component_indices: List[str]):
    """
    Read specific components by their indices
    
    - **component_indices**: List of component indices to query
    """
    if not app_state.is_initialized or not app_state.mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    if not component_indices:
        raise HTTPException(status_code=400, detail="component_indices cannot be empty")
    
    try:
        server_params = StdioServerParameters(
            command="python",
            args=["../server/server.py"]
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Call the read_component tool with multiple indices
                result = await session.call_tool("read_component", {
                    "component_indices": component_indices
                })
                
                return {
                    "status": "success",
                    "result": result.content[0].text,
                    "queried_indices": component_indices
                }
    
    except Exception as e:
        logger.error("Failed to read components: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to read components: {str(e)}") from e

@app.get("/models")
async def get_available_models():
    """Get list of available Ollama models"""
    if not app_state.is_initialized or not app_state.mcp_client:
        raise HTTPException(status_code=503, detail="MCP client not initialized")
    
    try:
        models = app_state.mcp_client.ollama_client.list()
        available_models = []
        
        if isinstance(models, dict) and 'models' in models:
            for m in models['models']:
                model_info = {
                    "name": m.get('name', 'unknown'),
                    "size": m.get('size', 0),
                    "modified_at": m.get('modified_at', '')
                }
                available_models.append(model_info)
        
        return {
            "models": available_models,
            "current_model": app_state.mcp_client.model,
            "total_count": len(available_models)
        }
    
    except Exception as e:
        logger.error("Failed to get models: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}") from e

if __name__ == "__main__":
    """Run the FastAPI server"""
    # Fix for Windows subprocess issue with asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print("✅ Set Windows ProactorEventLoop policy for subprocess support")
    
    logger.info("🚀 Starting Taipei City Dashboard AI API Server...")
    uvicorn.run(
        "api_service:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload for Windows compatibility
        log_level="info"
    )
