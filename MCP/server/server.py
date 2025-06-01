# server.py
import asyncio
import asyncpg
import os
import json
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from fastapi import FastAPI
from cors_middleware import setup_cors

# Load environment variables
load_dotenv("../../docker/.env")

# Create an MCP server
mcp = FastMCP("Demo")

# Setup CORS middleware
app = mcp.get_app()
setup_cors(app)

# Database configuration
# Note: postgres-manager has external port access (5432:5432), postgres-data is internal only
DB_CONFIG = {
    "host": os.getenv("DB_DASHBOARD_HOST", "localhost"),
    "port": int(os.getenv("DB_DASHBOARD_PORT", "5433")),  # Dashboard DB needs different port or proxy
    "database": os.getenv("DB_DASHBOARD_DBNAME", "dashboard"),
    "user": os.getenv("DB_DASHBOARD_USER", "postgres"),
    "password": os.getenv("DB_DASHBOARD_PASSWORD", "postgres")
}
DB_MANAGER_CONFIG = {
    "host": "localhost",  # Use localhost for external access via port mapping
    "port": 5432,         # Manager DB external port (mapped from container)
    "database": os.getenv("DB_MANAGER_DBNAME", "dashboardmanager"),
    "user": os.getenv("DB_MANAGER_USER", "postgres"),
    "password": os.getenv("DB_MANAGER_PASSWORD", "m5ERvB38")
}
async def get_db_connection(db_type: str = "dashboard") -> asyncpg.Connection:
    """Create and return a database connection
    
    Args:
        db_type: Either "dashboard" or "manager" to specify which database to connect to
    """
    try:
        if db_type == "manager":
            config = DB_MANAGER_CONFIG
        elif db_type == "dashboard":
            config = DB_CONFIG
        else:
            raise ValueError("db_type must be either 'dashboard' or 'manager'")
            
        connection = await asyncpg.connect(
            host=config["host"],
            port=config["port"],
            database=config["database"],
            user=config["user"],
            password=config["password"]
        )
        return connection
    except Exception as e:
        raise Exception(f"Database connection failed: {str(e)}")

@mcp.resource("components://")
async def get_components() -> List[Dict[str, str]]:
    """Fetch components from db_mannager.components"""
    connection = None
    try:
        connection = await get_db_connection("manager")
        query = """SELECT id,name FROM public.components
        ORDER BY id ASC """
        rows = await connection.fetch(query)
        # Convert rows to list of dictionaries
        result = []
        for row in rows:
            print(row)
            result.append(dict(row))
        
        return result
        
    except Exception as e:
        raise Exception(f"Error fetching components: {str(e)}")
    finally:
        if connection:
            await connection.close()

# Add database table reading tool
@mcp.tool()
async def read_component(components_topic: str,component_ids: list[str]) -> str:
    """
    讀取指定組件資料 (支援多個組件查詢)
    
    Args:
		components_topic: 獲取組件之共同主題，例如 "高齡照護狀況"
        component_ids: 組件索引列表，例如 ["212", "213", "214"]
        參數皆為字串類型
    
    Returns:
        所有查詢組件的資訊
    """
    if not component_ids:
        return "No components specified"
    
    results = [components_topic]
    for id in component_ids:
        results.append(id)
    
    return "\n".join(results)
# Add a dynamic greeting resource
# Run the server in stdio mode
if __name__ == "__main__":
    mcp.run()