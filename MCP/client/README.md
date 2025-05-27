# MCP + Ollama Integration Client

This project demonstrates a breakthrough integration between **Model Context Protocol (MCP)** and **Ollama**, enabling Ollama to directly call MCP tools during chat conversations.

## 🎯 Key Achievement

**Ollama can now use MCP tools as native functions!** When you chat with Ollama, it can automatically call MCP server tools and integrate the results back into the conversation.

## 🏗️ Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Ollama    │◄──►│ MCP Client   │◄──►│ MCP Server  │
│  (AI Chat)  │    │ (Integration)│    │ (Tools)     │
└─────────────┘    └──────────────┘    └─────────────┘
```

1. **Ollama**: Provides AI chat with function calling capability
2. **MCP Client**: Bridges Ollama and MCP server, handles tool integration
3. **MCP Server**: Exposes tools (add, greeting) via Model Context Protocol

## 🚀 Features

### Enhanced Chat with Tool Calling

- **`tools <message>`**: Chat with Ollama where it can call MCP tools automatically
- **`chat <message>`**: Regular chat without tool access
- **`process <query>`**: Process query with dynamic tool discovery
- **`add <a> <b>`**: Direct MCP tool usage
- **`greeting <name>`**: Direct MCP resource access

### Database Operations (新功能)

- **`tables`**: 列出所有資料庫表格
- **`table <name> [limit]`**: 讀取指定表格資料 (可選限制筆數)
- **`schema <name>`**: 查看表格結構資訊

### Available MCP Tools

- **`add(a, b)`**: Mathematical addition
- **`read_table(table_name, limit)`**: 讀取指定資料庫表格的資料
- **`get_table_info(table_name)`**: 獲取表格結構資訊
- **`list_tables()`**: 列出所有可用的資料庫表格
- **`get_greeting(name)`**: Personalized greeting generation

## 📋 Prerequisites

1. **Python 3.12+** with **uv** package manager
2. **Ollama** running locally:
   ```bash
   ollama serve
   ollama pull qwen3:4b  # or your preferred model
   ```
3. **PostgreSQL Database** (for database features):
   - Dashboard database running on configured host/port
   - Proper credentials in environment variables

## 🔧 Setup

1. **Install dependencies**:

   ```bash
   uv sync
   ```

2. **Database Configuration** (for database features):

   ```bash
   # Copy environment template
   cp ../server/.env.example ../server/.env

   # Edit .env file with your database settings
   # DB_DASHBOARD_HOST=postgres-data
   # DB_DASHBOARD_PORT=5432
   # DB_DASHBOARD_NAME=dashboard
   # DB_DASHBOARD_USER=postgres
   # DB_DASHBOARD_PASSWORD=postgres
   ```

3. **Start MCP server** (in another terminal):

   ```bash
   cd ../server
   uv run python server.py
   ```

4. **Run the client**:
   ```bash
   uv run python client.py
   ```

## 💡 Usage Examples

### Interactive Mode

```bash
> tools What is 25 plus 17?
🤖 Ollama + MCP Tools: I'll calculate that for you.

Tool Results:
🔧 add({"a": 25, "b": 17}) → 42

The answer is 42.

> tools Please greet Alice
🤖 Ollama + MCP Tools: I'll get a personalized greeting.

Tool Results:
🔧 get_greeting({"name": "Alice"}) → Hello Alice! Welcome to the MCP demo.

Hello Alice! Welcome to the MCP demo.
```

### Demo Script

```bash
uv run python demo.py
```

### Integration Test

```bash
uv run python test_integration.py
```

### Database Features Test

```bash
uv run python test_database.py
```

## 💾 Database Features Usage Examples

### List All Tables

```bash
> tables
📋 Database Tables:
{
  "database": "dashboard",
  "schema": "public",
  "tables": [
    {"name": "users", "type": "BASE TABLE"},
    {"name": "dashboards", "type": "BASE TABLE"}
  ]
}
```

### Read Table Data

```bash
> table users 5
📊 Table Data for 'users':
{
  "table_name": "users",
  "record_count": 5,
  "limit": 5,
  "data": [
    {"id": 1, "name": "Admin", "email": "admin@example.com"},
    ...
  ]
}
```

### Get Table Schema

```bash
> schema users
🔍 Table Schema for 'users':
{
  "table_name": "users",
  "columns": [
    {"name": "id", "type": "integer", "nullable": false},
    {"name": "name", "type": "character varying", "nullable": false},
    {"name": "email", "type": "character varying", "nullable": true}
  ]
}
```

## 🔍 How It Works

### 1. Tool Definition

The client exposes MCP tools to Ollama using OpenAI function calling format:

```python
tools=[{
    'type': 'function',
    'function': {
        'name': 'add',
        'description': 'Add two numbers',
        'parameters': {
            'type': 'object',
            'properties': {
                'a': {'type': 'integer', 'description': 'First number'},
                'b': {'type': 'integer', 'description': 'Second number'},
            },
            'required': ['a', 'b'],
        },
    },
}]
```

### 2. Tool Execution

When Ollama calls a tool:

1. Client receives tool call from Ollama
2. Client connects to MCP server via stdio
3. Client executes tool via MCP protocol
4. Results are returned to Ollama
5. Ollama incorporates results in response

### 3. Enhanced Chat Method

```python
async def chat_with_ollama_tools(self, prompt: str):
    # Send message with tools to Ollama
    response = self.ollama_client.chat(model=self.model, messages=[...], tools=[...])

    # Check if Ollama wants to call tools
    if 'tool_calls' in response['message']:
        for tool_call in response['message']['tool_calls']:
            # Execute via MCP server
            result = await self.call_mcp_tool(tool_call['function']['name'],
                                            tool_call['function']['arguments'])
            # Format results

    return formatted_response
```

## 📁 Project Structure

```
MCP/
├── client/
│   ├── client.py              # Main MCP + Ollama integration
│   ├── demo.py               # Demo script
│   ├── test_integration.py   # Integration tests
│   ├── pyproject.toml        # Dependencies
│   └── README.md             # This file
└── server/
    ├── server.py             # MCP server with tools
    ├── pyproject.toml        # Dependencies
    └── README.md             # Server documentation
```

## 🐛 Troubleshooting

### Ollama Not Responding

- Ensure Ollama is running: `ollama serve`
- Check if model is available: `ollama list`
- Try a different model in client initialization

### MCP Server Issues

- Verify server runs independently: `cd ../server && uv run python server.py`
- Check server logs for errors
- Ensure stdio communication works

### Tool Calls Not Working

- Verify Ollama model supports function calling
- Check tool definitions match MCP server capabilities
- Use `test` command to verify connections

## 🎉 Success Indicators

When working correctly, you should see:

- ✅ Ollama connected
- ✅ MCP Server connected
- 🔧 Tool calls in responses: `add({"a": 5, "b": 3}) → 8`
- 🎉 "MCP tools were successfully called by Ollama!"

## 🚀 Next Steps

This foundation enables:

- **Complex tool chains**: Multiple MCP tools in sequence
- **Custom tools**: Add domain-specific MCP tools
- **Resource access**: File systems, databases, APIs via MCP
- **Multi-modal integration**: Combine with other AI capabilities

## 📚 Related Documentation

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Ollama Function Calling](https://ollama.com/blog/tool-support)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)

---

**Built for Taipei City Dashboard Project** - Enabling AI-powered tool integration using industry-standard protocols.
