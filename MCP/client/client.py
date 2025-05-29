"""
Enhanced MCP Client with Ollama Integration and Dynamic Tool Discovery
"""
import asyncio
import logging
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ollama

# Fix for Windows subprocess issue with asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleMCPOllamaClient:
    
    def __init__(self, ollama_host: str = "http://localhost:11434", model: str = "qwen3:4b"):
        self.ollama_host = ollama_host
        self.model = model
        self.ollama_client = ollama.Client(host=ollama_host)
        self.available_tools = []  # Cache for MCP tools
    
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
            print("📡 Connecting to MCP server...")    
            print(f"Server params: command={server_params.command}, args={server_params.args}")
            async with stdio_client(server_params) as (read, write):
                print("✅ MCP server connected successfully")
                async with ClientSession(read, write) as session:
                    print("🔧 Initializing MCP session...")
                    await session.initialize()     
                    print("✅ MCP session initialized")     
                    components = await session.read_resource("components://")
                    # Step 1: Get available tools from MCP server (like Claude example)
                    tools = await session.list_tools()
                    available_tools = [{ 
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    } for tool in tools.tools]
                    print(f"🛠️  Found {len(available_tools)} available tools")    
                    if not available_tools:
                        # Fallback to basic chat without tools
                        print("⚠️  No tools available, falling back to basic chat")
                        ollama_response = self.ollama_client.chat(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": query}
                                ]
                        )
                        return ollama_response['message']['content']
                    print("🔄 Converting tools to Ollama format...")    
                    # Step 2: Convert tools to Ollama format
                    ollama_tools = self.convert_mcp_tools_to_ollama_format(available_tools)
                    
                    # Step 3: Initial Ollama call with tools
                    print("🤖 Sending query to Ollama...")
                    ollama_response = self.ollama_client.chat(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": f"available components: {components.contents[0].text}"},
                            {"role": "user", "content": query}
                            ],
                        tools=ollama_tools
                    )
                    print("✅ Received response from Ollama")    
                    message = ollama_response['message']
                    final_text = []
                    component_ids = []
                    
                    # Step 4: Process response and handle tool calls (like Claude example)
                    if message.get('content'):
                        final_text.append(message['content'])
                    
                    print("🔍 Processing tool calls...")    
                    if message.get('tool_calls'):
                        for tool_call in message['tool_calls']:
                            tool_name = tool_call['function']['name']
                            tool_args = tool_call['function']['arguments']
                            
                            # Execute tool call via MCP
                            result = await session.call_tool(tool_name, tool_args)
                            final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                            final_text.append(f"Tool result: {result.content}")
                              # Extract component IDs from the result
                            if result.content:
                                for content_item in result.content:
                                    if hasattr(content_item, 'text'):
                                        # Parse the text content to extract component IDs
                                        text_content = content_item.text
                                        # Split by newlines and filter out empty lines
                                        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                                        
                                        # Filter lines to only include valid component IDs
                                        # Component IDs are typically alphanumeric with underscores
                                        import re
                                        for line in lines:
                                            # Match lines that look like component IDs (alphanumeric + underscores)
                                            if re.match(r'^[a-zA-Z0-9_]+$', line):
                                                component_ids.append(line)
                    
                    # Return only component IDs if found, otherwise return full text
                    if component_ids:
                        print(f"📋 Found component IDs: {component_ids}")
                        # Return as JSON string for API compatibility
                        import json
                        return json.dumps(component_ids)
                    else:
                        print("📄 No component IDs found, returning full response")
                        return "\n".join(final_text)
        except Exception as e:
            import traceback
            full_traceback = traceback.format_exc()
            logger.error(f"Error in process_query: {e}")
            logger.error(f"Full traceback: {full_traceback}")
            print(f"❌ Exception occurred: {e}")
            print(f"❌ Full traceback: {full_traceback}")
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
        print("  process <query>    - Process query with dynamic tool discovery")
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
                elif command == "process" and len(parts) == 2:
                    print("🔍 Processing query with dynamic tool discovery...")
                    response = await self.process_query(parts[1])
                    print(f"🤖 Result: {response}")
                elif command == "test":
                    print("Testing connections...")
                    ollama_ok = await self.test_ollama_connection()
                    mcp_ok = await self.test_mcp_server()
                    print(f"Ollama: {'✅' if ollama_ok else '❌'}")
                    print(f"MCP Server: {'✅' if mcp_ok else '❌'}")
                else:
                    print("Invalid command. Available commands:")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

async def main():
    """Main function demonstrating the enhanced MCP + Ollama integration"""    
    client = SimpleMCPOllamaClient()
    await client.interactive_chat()

if __name__ == "__main__":
    asyncio.run(main())