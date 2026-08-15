# Quick Start — 5 Minutes to Working MCP Server

```bash
# 1. Install dependencies
cd github-analyzer-mcp
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
# Edit .env: add GEMINI_API_KEY and GROQ_API_KEY

# 3. Test the core logic (no MCP needed yet)
python test_standalone.py
# ✅ Should fetch a repo, analyse it, print scores

# 4. Test with MCP Inspector (requires Node.js + npx)
npx @modelcontextprotocol/inspector python server.py
# Opens http://localhost:5173
# Click "analyze_repo", enter https://github.com/tiangolo/fastapi, invoke
# ✅ Should return full JSON analysis report

# 5. Register in Claude Desktop (optional)
# macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
# Windows: %APPDATA%\Claude\claude_desktop_config.json
# Add:
{
  "mcpServers": {
    "github-analyzer": {
      "command": "python",
      "args": ["C:\\path\\to\\github-analyzer-mcp\\server.py"],
      "env": {
        "GEMINI_API_KEY": "your_gemini_key",
        "GROQ_API_KEY": "your_groq_key"
      }
    }
  }
}
# Restart Claude Desktop
# ✅ Tool appears in attachments menu
```

---

## What You Now Have

✅ A **real MCP server** using official `mcp` Python SDK v2  
✅ **stdio transport** (works with Claude Desktop, Kiro, Cursor)  
✅ **HTTP transport** ready (uncomment 2 lines in `server.py` for deployment)  
✅ **8-category analysis** powered by Gemini + Groq  
✅ **MCP Inspector** compatible (test without any AI service)  
✅ **Production-ready** patterns (Pydantic, async, retries, logging)  

---

## For Your Internship Interview

**"Show me your MCP project"**

```bash
# Live demo
npx @modelcontextprotocol/inspector python server.py
```

Open browser, invoke tool, show JSON output.

**"Explain the architecture"**

1. MCP host (Claude/Kiro) launches `server.py` as subprocess
2. Host sends `initialize` → server responds with capabilities
3. Host sends `tools/list` → server returns `[{"name": "analyze_repo", ...}]`
4. User invokes tool → host sends `tools/call` with `{"repo_url": "..."}`
5. Server fetches repo (GitHub API), analyses (Gemini + Groq), returns JSON
6. Host inserts JSON into LLM context

**"Why is this better than a REST API?"**

- Bidirectional (server can stream progress)
- Session-aware (one connection, many calls)
- Schema auto-discovery (`tools/list`)
- AI assistant-native (every MCP host understands it)

---

## Deployment (5 More Minutes)

```bash
# Edit server.py (bottom):
mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)

# Build Docker image
docker build -t github-analyzer-mcp .

# Run on VM
docker run -d -p 8000:8000 --env-file .env github-analyzer-mcp

# Test
curl http://your-vm-ip:8000/mcp

# Give reviewers this config:
{
  "mcpServers": {
    "github-analyzer": {
      "url": "http://your-vm-ip:8000/mcp",
      "transport": "http"
    }
  }
}
```

---

**You're ready. Go get that internship.**
