"""
Enhanced MCP Client with Ollama Integration and Dynamic Tool Discovery
"""
import asyncio
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ollama

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMCPOllamaClient:
    
    def __init__(self, ollama_host: str = "http://localhost:11434", model: str = "qwen3:4b"):
        self.ollama_host = ollama_host
        self.model = model
        self.ollama_client = ollama.Client(host=ollama_host)
        self.available_tools = []  # Cache for MCP tools
        self.get_mcp_tools()
    
    async def get_mcp_tools(self):
        """Get available tools from MCP server and cache them"""
        server_params = StdioServerParameters(
            command="python",
            args=["../server/server.py"]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Get tools from MCP server
                    response = await session.list_tools()
                    self.available_tools = [{
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    } for tool in response.tools]
                    
                    logger.info(f"Loaded {len(self.available_tools)} MCP tools")
                    return self.available_tools
        except Exception as e:
            logger.error(f"Failed to get MCP tools: {e}")
            return []
    
    def convert_mcp_tools_to_ollama_format(self, mcp_tools):
        """Convert MCP tool schemas to Ollama function calling format"""
        ollama_tools = []
        for tool in mcp_tools:
            ollama_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
            ollama_tools.append(ollama_tool)
        return ollama_tools
    
    async def process_query(self, query: str) -> str:
        """Process a query using dynamic tool discovery, similar to Claude integration"""
        server_params = StdioServerParameters(
            command="python",
            args=["../server/server.py"]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Step 1: Get available tools from MCP server (like Claude example)
                    response = await session.list_tools()
                    available_tools = [{ 
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    } for tool in response.tools]
                    
                    if not available_tools:
                        # Fallback to basic chat without tools
                        ollama_response = self.ollama_client.chat(
                            model=self.model,
                            messages=[{"role": "user", "content": query}]
                        )
                        return ollama_response['message']['content']
                    
                    # Step 2: Convert tools to Ollama format
                    ollama_tools = self.convert_mcp_tools_to_ollama_format(available_tools)
                    
                    # Step 3: Initial Ollama call with tools
                    ollama_response = self.ollama_client.chat(
                        model=self.model,
                        messages=[{"role": "user", "content": query}],
                        tools=ollama_tools
                    )
                    
                    message = ollama_response['message']
                    print(message)
                    final_text = []
                    
                    # Step 4: Process response and handle tool calls (like Claude example)
                    if message.get('content'):
                        final_text.append(message['content'])
                    
                    if message.get('tool_calls'):
                        for tool_call in message['tool_calls']:
                            tool_name = tool_call['function']['name']
                            tool_args = tool_call['function']['arguments']
                            
                            # Execute tool call via MCP
                            result = await session.call_tool(tool_name, tool_args)
                            final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                            final_text.append(f"Tool result: {result.content}")
                    
                    return "\n".join(final_text)
                    
        except Exception as e:
            logger.error(f"Error in process_query: {e}")
            return f"Error processing query: {e}"
    
    async def test_ollama_connection(self):
        """Test Ollama connection"""
        try:
            models = self.ollama_client.list()
            logger.info(f"Raw Ollama response: {models}")
            
            # Handle Ollama client response structure
            available_models = []
            if isinstance(models, dict) and 'models' in models:
                for m in models['models']:
                    if hasattr(m, 'model'):
                        available_models.append(m.model)
                    elif isinstance(m, dict):
                        model_name = m.get('name') or m.get('model') or m.get('id')
                        if model_name:
                            available_models.append(model_name)
                    else:
                        available_models.append(str(m))
            elif hasattr(models, 'models'):
                for m in models.models:
                    if hasattr(m, 'model'):
                        available_models.append(m.model)
                    else:
                        available_models.append(str(m))
            elif isinstance(models, list):
                for m in models:
                    if hasattr(m, 'model'):
                        available_models.append(m.model)
                    elif isinstance(m, dict):
                        model_name = m.get('name') or m.get('model') or m.get('id')
                        if model_name:
                            available_models.append(model_name)
                    else:
                        available_models.append(str(m))
                
            logger.info(f"Available Ollama models: {available_models}")
            
            if not available_models:
                logger.error("No models found in Ollama")
                return False
            
            if self.model not in available_models:
                logger.warning(f"Model {self.model} not found. Available models: {available_models}")
                self.model = available_models[0]
                logger.info(f"Using model: {self.model}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            return False
    
    async def chat_with_ollama(self, prompt: str):
        """Send a prompt to Ollama and get response"""
        try:
            response = self.ollama_client.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }]
            )
            return response['message']['content']
        except Exception as e:
            logger.error(f"Error chatting with Ollama: {e}")
            return None
    
    async def test_mcp_server(self):
        """Test connection to MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=["../server/server.py"]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # List available tools
                    tools = await session.list_tools()
                    logger.info(f"Available MCP tools: {[tool.name for tool in tools.tools]}")
                    
                    # Test the add tool
                    result = await session.call_tool("add", {"a": 10, "b": 15})
                    add_result = result.content[0].text
                    logger.info(f"MCP add tool result (10 + 15): {add_result}")
                    
                    # Test the greeting resource
                    greeting = await session.read_resource("greeting://World")
                    greeting_text = greeting.contents[0].text
                    logger.info(f"MCP greeting resource: {greeting_text}")
                    
                    return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False

    async def interactive_chat(self):
        """Interactive chat session combining MCP and Ollama"""
        print("=== Enhanced MCP + Ollama Client ===")
        print("Commands:")
        print("  chat <message>     - Chat with Ollama")
        print("  process <query>    - Process query with dynamic tool discovery")
        print("  add <a> <b>        - Use MCP add tool")
        print("  greeting <name>    - Use MCP greeting resource")
        print("  components         - Get dashboard components from database")
        print("  tables             - List all database tables")
        print("  test               - Test both connections")
        print("  quit               - Exit")
        print()
        
        # Test connections first
        ollama_ok = await self.test_ollama_connection()
        if not ollama_ok:
            print("⚠️  Ollama connection failed")
        else:
            print("✅ Ollama connected")
        
        while True:
            try:
                user_input = input("> ").strip()
                if not user_input:
                    continue
                    
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                
                if command == "quit":
                    break
                elif command == "chat" and len(parts) == 2:
                    if ollama_ok:
                        response = await self.chat_with_ollama(parts[1])
                        if response:
                            print(f"🤖 Ollama: {response}")
                        else:
                            print("❌ Failed to get response from Ollama")
                    else:
                        print("❌ Ollama not available")
                elif command == "process" and len(parts) == 2:
                    print("🔍 Processing query with dynamic tool discovery...")
                    response = await self.process_query(parts[1])
                    print(f"🤖 Result: {response}")
                elif command == "add" and len(parts) == 2:
                    try:
                        nums = parts[1].split()
                        if len(nums) == 2:
                            a, b = int(nums[0]), int(nums[1])
                            await self._use_mcp_add(a, b)
                        else:
                            print("Usage: add <number1> <number2>")
                    except ValueError:
                        print("Please provide valid numbers")
                elif command == "greeting" and len(parts) == 2:
                    await self._use_mcp_greeting(parts[1])
                elif command == "tables":
                    await self._use_mcp_list_tables()
                elif command == "components":
                    await self._use_mcp_get_components()
                elif command == "table" and len(parts) == 2:
                    print("❌ Table reading feature is currently disabled")
                elif command == "schema" and len(parts) == 2:
                    print("❌ Schema info feature is currently disabled")
                elif command == "test":
                    print("Testing connections...")
                    ollama_ok = await self.test_ollama_connection()
                    mcp_ok = await self.test_mcp_server()
                    print(f"Ollama: {'✅' if ollama_ok else '❌'}")
                    print(f"MCP Server: {'✅' if mcp_ok else '❌'}")
                else:
                    print("Invalid command. Available commands:")
                    print("  chat <message>, process <query>, add <a> <b>, greeting <name>")
                    print("  tables, table <name> [limit], schema <name>, test, quit")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        print("Goodbye! 👋")
    
    async def _use_mcp_add(self, a: int, b: int):
        """Use MCP server add tool"""
        server_params = StdioServerParameters(
            command="python",
            args=["../server/server.py"]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("add", {"a": a, "b": b})
                    print(f"➕ MCP Add Result: {a} + {b} = {result.content[0].text}")
        except Exception as e:
            print(f"❌ MCP add failed: {e}")

    async def _use_mcp_greeting(self, name: str):
        """Use MCP server greeting resource"""
        server_params = StdioServerParameters(
            command="python",
            args=["../server/simple_server.py"]  # Use simple server for now
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    greeting = await session.read_resource(f"greeting://{name}")
                    print(f"👋 MCP Greeting: {greeting.contents[0].text}")
        except Exception as e:
            print(f"❌ MCP greeting failed: {e}")

    async def _use_mcp_get_components(self):
        """Get components from database using MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=["../server/simple_server.py"]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("get_components", {})
                    print(f"🧩 Components:\n{result.content[0].text}")
        except Exception as e:
            print(f"❌ Get components failed: {e}")

    async def _use_mcp_list_tables(self):
        """List all database tables using MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=["../server/simple_server.py"]  # Use simple server for now
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("list_tables", {})
                    print(f"📋 Database Tables:\n{result.content[0].text}")
        except Exception as e:
            print(f"❌ List tables failed: {e}")
    
    async def _use_mcp_read_table(self, table_name: str, limit: int = 100):
        """Read data from specified table using MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=["../server/server.py"]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("read_table", {
                        "table_name": table_name,
                        "limit": limit
                    })
                    print(f"📊 Table Data for '{table_name}':\n{result.content[0].text}")
        except Exception as e:
            print(f"❌ Read table failed: {e}")
    
    async def _use_mcp_get_table_info(self, table_name: str):
        """Get table schema information using MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=["../server/server.py"]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("get_table_info", {
                        "table_name": table_name
                    })
                    print(f"🔍 Table Schema for '{table_name}':\n{result.content[0].text}")
        except Exception as e:
            print(f"❌ Get table info failed: {e}")

async def main():
    """Main function demonstrating the enhanced MCP + Ollama integration"""    
    client = SimpleMCPOllamaClient()
    await client.interactive_chat()

if __name__ == "__main__":
    asyncio.run(main())