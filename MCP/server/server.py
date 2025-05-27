# server.py
import asyncio
import asyncpg
import os
import json
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv("../../docker/.env")

# Create an MCP server
mcp = FastMCP("Demo")

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

@mcp.tool()
async def get_components() -> List[Dict[str, str]]:
    """Fetch components from db_mannager.components"""
    connection = None
    try:
        connection = await get_db_connection("manager")
        query = """SELECT index,name FROM public.components
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

# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add database table reading tool
# @mcp.tool()
# async def read_table(table_name: str, limit: int = 100) -> str:
#     """
#     讀取指定資料庫表格的資料
    
#     Args:
#         table_name: 表格名稱
#         limit: 限制返回的記錄數量 (預設: 100)
    
#     Returns:
#         JSON格式的表格資料
#     """
#     try:
#         data = await fetch_table_data(table_name, limit)
#         return json.dumps({
#             "table_name": table_name,
#             "record_count": len(data),
#             "limit": limit,
#             "data": data
#         }, ensure_ascii=False, indent=2, default=str)
#     except Exception as e:
#         return json.dumps({
#             "error": str(e),
#             "table_name": table_name
#         }, ensure_ascii=False, indent=2)


# # Add table schema tool
# @mcp.tool()
# async def get_table_info(table_name: str) -> str:
#     """
#     獲取指定表格的結構資訊
    
#     Args:
#         table_name: 表格名稱
    
#     Returns:
#         JSON格式的表格結構資訊
#     """
#     try:
#         schema = await get_table_schema(table_name)
#         return json.dumps(schema, ensure_ascii=False, indent=2)
#     except Exception as e:
#         return json.dumps({
#             "error": str(e),
#             "table_name": table_name
#         }, ensure_ascii=False, indent=2)


# Add list tables tool
@mcp.tool()
async def list_tables() -> str:
    """
    列出資料庫中所有可用的表格
    
    Returns:
        JSON格式的表格列表
    """
    connection = None
    try:
        connection = await get_db_connection()
        
        query = """
        SELECT table_name, table_type
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """
        
        tables = await connection.fetch(query)
        
        result = {
            "database": DB_CONFIG["database"],
            "schema": "public",
            "tables": []
        }
        
        for table in tables:
            result["tables"].append({
                "name": table["table_name"],
                "type": table["table_type"]
            })
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Error listing tables: {str(e)}"
        }, ensure_ascii=False, indent=2)
    finally:
        if connection:
            await connection.close()


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# Run the server in stdio mode
if __name__ == "__main__":
    # # Test database connection first (optional)
    # try:
    #     import asyncio
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    #     result = loop.run_until_complete(get_components())
    #     print(f"✅ Successfully connected to database! Found {len(result)} components.")
    #     loop.close()
    # except Exception as e:
    #     print(f"⚠️  Database connection test failed: {e}")
    #     print("MCP server will start anyway - database features may not work until connection is fixed.")
    
    # print("🚀 Starting MCP server...")
    mcp.run()