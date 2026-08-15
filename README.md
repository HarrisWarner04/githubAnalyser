# GitHub Analyzer — MCP Server

A **proper Model Context Protocol (MCP) server** that analyses any public GitHub repository against industry best practices. Built with the official `mcp` Python SDK v2, using Gemini 2.5 Flash for deep code analysis and Groq/LLaMA 3 for fast structured scoring — both on generous free tiers.

This project demonstrates **real MCP protocol implementation** — not just a REST API with MCP-inspired endpoints.

---

## What is MCP?

**Model Context Protocol (MCP)** is an open standard that lets AI assistants (Claude, Cursor, VS Code Copilot, Kiro IDE, etc.) connect to external tools and data sources in a unified way. Think of it like USB for AI — one protocol, many hosts, any server.

### Key MCP Concepts This Project Uses

| Concept | What it is | In this project |
|---|---|---|
| **Server** | A process that exposes tools, resources, or prompts | `server.py` — exposes `analyze_repo` tool |
| **Transport** | How bytes move between client & server | stdio (subprocess stdin/stdout) |
| **Protocol** | JSON-RPC 2.0 messages | Handled by `mcp.server.MCPServer` |
| **Tool** | A function the AI can invoke | `@mcp.tool()` decorated `analyze_repo()` |
| **Host/Client** | The AI app that discovers and calls tools | Claude Desktop, Kiro, Cursor, MCP Inspector |

**What makes this "real" MCP:**
- ✅ Uses official `mcp` SDK v2 (`pip install mcp[cli]`)
- ✅ Implements JSON-RPC over stdio transport (subprocess protocol)
- ✅ Tool schema auto-generated from Python type hints
- ✅ Can be registered in Claude Desktop, Kiro `.kiro/settings/mcp.json`, Cursor, etc.
- ✅ Works with MCP Inspector CLI for testing

---

## What the Tool Does

The `analyze_repo` tool:

1. **Fetches** repo metadata, file tree, and content from GitHub REST API
2. **Analyses** with Gemini 2.5 Flash — produces scores (0-100) and narrative for 8 categories
3. **Scores** with Groq LLaMA 3 8B — generates up to 12 prioritised recommendations
4. **Returns** a structured JSON report with:
   - Per-category scores and letter grades (A–F)
   - Weighted overall score (20% code quality, 20% security, 15% testing, etc.)
   - Executive summary, top strengths, top issues
   - Prioritised recommendations (critical → high → medium → low)

### Categories Evaluated

| Category | Weight | What we check |
|---|---|---|
| **Code Quality** | 20% | Style consistency, complexity, type hints, linting |
| **Security** | 20% | Secrets in code, dependency vulnerabilities, auth patterns |
| **Testing** | 15% | Test coverage, CI integration, test quality |
| **Documentation** | 10% | README, API docs, code comments |
| **CI/CD** | 10% | GitHub Actions, automated checks, deployment pipeline |
| **Project Structure** | 10% | Directory layout, module organisation |
| **Dependencies** | 10% | Lock files, version pinning, update cadence |
| **Best Practices** | 5% | Gitignore, license, contributing guidelines |

---

## Setup

### Prerequisites

- **Python 3.10+**
- **API keys** (both free):
  - [Google AI Studio](https://aistudio.google.com/apikey) for Gemini
  - [Groq Console](https://console.groq.com/keys) for Groq
- *(Optional)* [GitHub personal access token](https://github.com/settings/tokens) to raise rate limit from 60/h to 5000/h

### Install

```bash
# Clone / download this repo
cd github-analyzer-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure secrets
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY and GROQ_API_KEY
```

---

## Usage

### 1. Test with MCP Inspector (local development)

The **MCP Inspector** is the official CLI tool for testing MCP servers. It launches your server as a subprocess (stdio transport) and gives you a web UI to invoke tools.

```bash
# Install Node.js if you don't have it (Inspector is a Node app)
# Then run:
uv run mcp dev server.py

# Or without uv:
npx @modelcontextprotocol/inspector python server.py
```

This opens `http://localhost:5173` where you can:
- See the `analyze_repo` tool schema (auto-generated from type hints)
- Call it with a GitHub URL like `https://github.com/fastapi/fastapi`
- View the full JSON response

**Why this matters for interviews:** You can demo your MCP server live without needing Claude Desktop or any paid AI service.

---

### 2. Connect to Claude Desktop

Register your server so Claude Desktop launches it automatically:

```bash
uv run mcp install server.py --name "GitHub Analyzer" \
  -v GEMINI_API_KEY=your_key \
  -v GROQ_API_KEY=your_key
```

Or manually edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) / `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
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
```

Restart Claude Desktop. The tool appears in the attachments menu.

---

### 3. Connect to Kiro IDE

Add to `.kiro/settings/mcp.json` in your workspace:

```json
{
  "mcpServers": {
    "github-analyzer": {
      "command": "python",
      "args": ["d:\\MCP Project\\github-analyzer-mcp\\server.py"],
      "env": {
        "GEMINI_API_KEY": "your_gemini_key",
        "GROQ_API_KEY": "your_groq_key"
      }
    }
  }
}
```

Reload the window. Kiro discovers the `analyze_repo` tool automatically via MCP's `tools/list` RPC call.

---

### 4. Connect to Cursor / VS Code

Similar config in Cursor's `mcp.json` or VS Code Copilot settings:

```json
{
  "mcpServers": {
    "github-analyzer": {
      "command": "python",
      "args": ["/full/path/to/server.py"],
      "env": {
        "GEMINI_API_KEY": "...",
        "GROQ_API_KEY": "..."
      }
    }
  }
}
```

---

## How MCP Works Under the Hood (For Interviews)

When a host like Claude Desktop connects to this server:

1. **Host launches** `python server.py` as a subprocess
2. **Server writes** to stdout: `{"jsonrpc": "2.0", "method": "server/capabilities", ...}`
3. **Host sends** `initialize` request via stdin
4. **Server responds** with its capabilities (we support `tools`)
5. **Host sends** `tools/list` → server returns `[{"name": "analyze_repo", "inputSchema": {...}}]`
6. **User invokes** tool in the AI chat
7. **Host sends** `tools/call` with `{"name": "analyze_repo", "arguments": {"repo_url": "..."}}`
8. **Server executes** the decorated function, returns JSON result
9. **Host** feeds the result back into the LLM context

**Why stdio instead of HTTP?** Stdio is simpler for local tools — no ports, no certificates, no CORS. The host manages the subprocess lifecycle. For remote/deployed servers, MCP also supports Streamable HTTP transport (see "Deployment" below).

---

## Project Structure

```
github-analyzer-mcp/
├── server.py                    # MCP server entry point (uses mcp.server.MCPServer)
├── src/
│   ├── config.py                # Loads .env (GEMINI_API_KEY, GROQ_API_KEY, etc.)
│   ├── models.py                # Pydantic models (RepoData, AnalysisResult, etc.)
│   ├── github/
│   │   └── fetcher.py           # GitHub REST API client (async httpx)
│   ├── analyzers/
│   │   ├── summarizer.py        # RepoData → token-safe text summary
│   │   ├── prompts.py           # AI prompt templates
│   │   ├── gemini.py            # Gemini 2.5 Flash deep analysis
│   │   └── groq.py              # Groq LLaMA 3 fast scoring
│   └── report/
│       └── generator.py         # Merge AI outputs → AnalysisResult
├── requirements.txt             # Pinned dependencies
├── pyproject.toml               # Project metadata
├── .env.example                 # Environment variable template
└── README.md                    # This file
```

---

## Deployment (Streamable HTTP Transport)

For production / remote access, switch from stdio to Streamable HTTP:

```python
# server.py (bottom)
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

Now clients connect to `http://your-server:8000/mcp` instead of launching a subprocess.

**Docker example:**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "server.py"]
```

```bash
docker build -t github-analyzer-mcp .
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -e GROQ_API_KEY=your_key \
  github-analyzer-mcp
```

Client config for HTTP transport:

```json
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

## Why This Showcases MCP Knowledge

| MCP Concept | What this project does |
|---|---|
| **MCP SDK usage** | Uses official `mcp` package v2 (not a custom REST API) |
| **Tool declaration** | `@mcp.tool()` decorator with typed args → auto-generates JSON schema |
| **Stdio transport** | Default `mcp.run()` — works with subprocess-based hosts |
| **HTTP transport** | Can switch to `transport="streamable-http"` for deployment |
| **JSON-RPC protocol** | SDK handles all `initialize`, `tools/list`, `tools/call` messages |
| **Host compatibility** | Works with Claude Desktop, Kiro, Cursor, MCP Inspector |
| **Real-world tool** | Not a toy — analyses actual repos with 2 AI models, 8 categories, prioritised output |

---

## Free-Tier Usage Notes

- **Gemini 2.5 Flash:** 1 500 req/day, 1M tokens/min free. One repo analysis ≈ 3k–8k tokens.
- **Groq LLaMA 3 8B:** 14 400 req/day, 30k tokens/min free. One scoring pass ≈ 1k–2k tokens.
- **GitHub API:** 60 req/h unauthenticated, 5 000 req/h with token. Fetching a repo ≈ 5–20 requests.

Tune limits in `.env`:

```bash
MAX_SOURCE_FILES=8      # Fetch fewer files for large repos
MAX_FILE_SIZE_KB=50     # Skip very large files
```

---

## Example Output (abbreviated)

```json
{
  "repo_full_name": "fastapi/fastapi",
  "analyzed_at": "2026-08-15T14:30:00Z",
  "overall_score": 88,
  "overall_grade": "B",
  "executive_summary": "FastAPI is a well-architected, production-grade framework...",
  "code_quality": {"score": 92, "grade": "A", "issues": [], "recommendations": [...]},
  "security": {"score": 78, "grade": "C", "issues": ["No SECURITY.md"], ...},
  "testing": {"score": 85, "grade": "B", ...},
  ...
  "prioritized_recommendations": [
    {
      "priority": "high",
      "category": "Security",
      "title": "Add vulnerability disclosure policy",
      "description": "Create SECURITY.md with contact info and process.",
      "effort": "low"
    }
  ]
}
```

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'mcp'"**
→ `pip install mcp[cli]`

**"ValueError: Invalid GitHub URL"**
→ URL must be `https://github.com/owner/repo` (not a file path or wiki link)

**"Gemini API error: PERMISSION_DENIED"**
→ Check `GEMINI_API_KEY` in `.env`. Get one at https://aistudio.google.com/apikey

**Server starts but nothing happens**
→ Normal for stdio mode! It's waiting on stdin for a host to connect. Use `uv run mcp dev server.py` to test.

**Tool doesn't appear in Claude Desktop**
→ Check `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows). Restart Claude Desktop after editing.

---

## License

MIT — free to use, modify, and distribute.

---

## For Internship Reviewers

**What this project demonstrates:**

✅ **MCP protocol knowledge** — uses official SDK, not a custom REST wrapper  
✅ **Stdio transport** — understands subprocess-based MCP (the default for local tools)  
✅ **Tool schema generation** — `@mcp.tool()` with type hints → JSON schema auto-generated  
✅ **Real-world AI integration** — Gemini + Groq, async Python, structured prompts  
✅ **GitHub API mastery** — fetches metadata, file tree, content with rate-limit awareness  
✅ **Production-ready patterns** — Pydantic models, tenacity retries, logging, .env config  
✅ **Deployment understanding** — can switch to HTTP transport + Docker for VM/cloud  

**Talking points for interviews:**

- "I chose stdio transport because MCP hosts like Claude Desktop manage the subprocess lifecycle — no need for ports or HTTPS certificates for local tools."
- "The `@mcp.tool()` decorator introspects the function signature and auto-generates the JSON-RPC tool schema from type hints."
- "I used Gemini for deep analysis (1M token context) and Groq for fast structured scoring — shows understanding of model selection for different tasks."
- "The project can run in MCP Inspector (no AI service needed) to demo the protocol live."

---

**Questions? Issues?** Open a GitHub issue or email me at [your-email].

**Built for internship at:** [Company Name]  
**Author:** [Your Name]
