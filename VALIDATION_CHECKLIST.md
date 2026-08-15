# Validation Checklist — Pre-Demo Testing

Complete these checks before showing to internship reviewers.

---

## ✅ Phase 1: Environment Setup

```bash
cd d:\MCP Project\github-analyzer-mcp

# Check Python version
python --version  # Should be 3.10+

# Create venv
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Verify installations
python -c "import mcp; print(mcp.__version__)"
python -c "import google.genai; print('Gemini SDK OK')"
python -c "import groq; print('Groq SDK OK')"
```

**Expected:** All imports succeed, no ModuleNotFoundError

---

## ✅ Phase 2: Configuration

```bash
# Copy env template
cp .env.example .env

# Edit .env with your real keys
# GEMINI_API_KEY=...
# GROQ_API_KEY=...
```

**Verify:**
- [ ] `.env` file exists
- [ ] GEMINI_API_KEY is set
- [ ] GROQ_API_KEY is set

---

## ✅ Phase 3: Standalone Pipeline Test

```bash
python test_standalone.py
```

**Expected output:**
```
🔍 Fetching https://github.com/tiangolo/fastapi...
✅ Fetched tiangolo/fastapi: 12 source files
📝 Building summary...
✅ Summary: ~8000 chars
🤖 Running Gemini analysis...
✅ Gemini: overall score estimate ~ 85-95
⚡ Running Groq scoring...
✅ Groq: 8-12 recommendations
📊 Generating final report...
✅ Final score: 88 (B)
======================================================================
FULL REPORT (first 1000 chars):
======================================================================
{
  "repo_full_name": "tiangolo/fastapi",
  "analyzed_at": "2026-08-15...",
  ...
}
✅ All systems working! MCP server is ready to run.
```

**Checks:**
- [ ] No errors
- [ ] Gemini returns valid JSON
- [ ] Groq returns recommendations array
- [ ] Final score is 0-100
- [ ] Grade is A/B/C/D/F

---

## ✅ Phase 4: MCP Server Starts

```bash
python server.py
```

**Expected:**
- Nothing prints to console (waiting on stdin)
- Process doesn't exit
- No error traceback

**If you see errors here, common causes:**
- Missing `.env` file
- Invalid API keys
- Import errors (missing dependencies)

Press Ctrl+C to stop.

---

## ✅ Phase 5: MCP Inspector Test

**Prerequisites:**
- Node.js installed
- npx available

```bash
npx @modelcontextprotocol/inspector python server.py
```

**Expected:**
```
MCP Inspector running on http://localhost:5173
```

**In browser:**
1. Open http://localhost:5173
2. Should see "github-analyzer" server connected
3. Click "Tools" tab → see "analyze_repo"
4. Click "analyze_repo" → see input schema with `repo_url` field
5. Enter: `https://github.com/tiangolo/fastapi`
6. Click "Call Tool"
7. Wait 30-60 seconds
8. Should see JSON response with:
   - `repo_full_name`
   - `overall_score`
   - `code_quality`, `security`, etc.
   - `prioritized_recommendations`

**Checks:**
- [ ] Inspector connects
- [ ] Tool appears in list
- [ ] Schema shows `repo_url: string`
- [ ] Tool call succeeds
- [ ] Response is valid JSON
- [ ] No errors in console

---

## ✅ Phase 6: Error Handling Test

In MCP Inspector, try:

**Test 1: Invalid URL**
```
Input: https://invalid-url
Expected: {"error": "Invalid GitHub URL: ..."}
```

**Test 2: Non-existent repo**
```
Input: https://github.com/nonexistent/repo123456
Expected: {"error": "...404..."}
```

**Test 3: Private repo (no token)**
```
Input: https://github.com/some-private-org/private-repo
Expected: {"error": "...404..." or "...403..."}
```

**Checks:**
- [ ] Errors are caught gracefully
- [ ] Response is valid JSON (not Python traceback)
- [ ] Error messages are descriptive

---

## ✅ Phase 7: Multiple Repos Test

Test with different types of repos:

```bash
# Small Python repo
https://github.com/pallets/click

# Large TypeScript repo
https://github.com/microsoft/vscode

# Go repo
https://github.com/golang/go

# Minimal repo (few files)
https://github.com/octocat/Hello-World
```

**Checks:**
- [ ] All complete successfully
- [ ] Scores vary appropriately
- [ ] Recommendations are relevant to each language/size

---

## ✅ Phase 8: Claude Desktop Integration (Optional)

**Windows:**
```
File: %APPDATA%\Claude\claude_desktop_config.json
```

**macOS:**
```
File: ~/Library/Application Support/Claude/claude_desktop_config.json
```

**Add:**
```json
{
  "mcpServers": {
    "github-analyzer": {
      "command": "python",
      "args": ["d:\\MCP Project\\github-analyzer-mcp\\server.py"],
      "env": {
        "GEMINI_API_KEY": "your_key_here",
        "GROQ_API_KEY": "your_key_here"
      }
    }
  }
}
```

**Test:**
1. Restart Claude Desktop
2. Start new conversation
3. Click attachments (paperclip icon)
4. Should see "github-analyzer" in tools list
5. Select it, paste GitHub URL
6. Claude should invoke tool and summarize results

**Checks:**
- [ ] Tool appears in Claude
- [ ] Tool invocation works
- [ ] Claude receives and parses JSON
- [ ] Claude summarizes results naturally

---

## ✅ Phase 9: Deployment Test (HTTP Transport)

**Edit `server.py` bottom:**
```python
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

**Run:**
```bash
python server.py
```

**Expected:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test from another terminal:**
```bash
curl http://localhost:8000/mcp
```

**Expected:**
- Some JSON response (MCP handshake)
- NOT a 404 or connection refused

**Revert `server.py` back to stdio after testing.**

---

## ✅ Phase 10: Code Quality Checks

```bash
# Check for syntax errors
python -m py_compile server.py
python -m py_compile src/**/*.py

# Check imports
python -c "from src.github.fetcher import fetch_repo; print('OK')"
python -c "from src.analyzers.gemini import GeminiAnalyzer; print('OK')"
python -c "from src.analyzers.groq import GroqAnalyzer; print('OK')"
python -c "from src.report.generator import generate; print('OK')"
```

**Checks:**
- [ ] No syntax errors
- [ ] All imports resolve
- [ ] No circular dependencies

---

## ✅ Phase 11: Documentation Review

**Check README.md:**
- [ ] All code blocks have correct syntax
- [ ] File paths are accurate
- [ ] Example outputs are realistic
- [ ] Links work (if any)

**Check other docs:**
- [ ] QUICKSTART.md is accurate
- [ ] DEPLOYMENT.md instructions are complete
- [ ] MCP_KNOWLEDGE_CHECKLIST.md is thorough

---

## ✅ Phase 12: Final Demo Rehearsal

**Scenario: Live interview demo**

1. Open MCP Inspector: `npx @modelcontextprotocol/inspector python server.py`
2. Navigate to http://localhost:5173
3. Show tool schema
4. Invoke with `https://github.com/fastapi/fastapi`
5. While waiting, explain:
   - "It's fetching repo metadata via GitHub REST API"
   - "Building a summary from README + source files"
   - "Calling Gemini for deep analysis of 8 categories"
   - "Calling Groq for prioritized recommendations"
   - "Merging results into a typed Pydantic model"
6. When complete, highlight:
   - Overall score and grade
   - Category breakdown
   - Top 3 recommendations

**Practice this 3 times until smooth.**

---

## ✅ Common Issues & Fixes

| Issue | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: mcp` | Not installed | `pip install -r requirements.txt` |
| `ValueError: Invalid GitHub URL` | Wrong URL format | Use `https://github.com/owner/repo` |
| `API key not found` | `.env` not loaded | Check `.env` exists, keys are set |
| `Rate limit exceeded` | Too many requests | Wait 1 hour or add GITHUB_TOKEN |
| `Inspector won't connect` | Node.js not installed | Install Node.js from nodejs.org |
| `Tool returns empty string` | Async error silently caught | Check `test_standalone.py` output |

---

## ✅ Pre-Submission Checklist

Before sharing with recruiters:

- [ ] `.env` is in `.gitignore` (don't commit secrets!)
- [ ] All placeholder text replaced (e.g., `[Your Name]`, `[Company]`)
- [ ] `test_standalone.py` runs successfully
- [ ] MCP Inspector demo works
- [ ] README examples are tested and accurate
- [ ] No hardcoded API keys in any file
- [ ] All TODO comments removed
- [ ] Code is formatted consistently

---

## ✅ Interview Readiness

- [ ] Can explain MCP vs REST in 30 seconds
- [ ] Can walk through `server.py` line by line
- [ ] Can explain stdio vs HTTP transport
- [ ] Can demo live with MCP Inspector
- [ ] Can explain why Gemini + Groq together
- [ ] Can describe the full data flow (GitHub → summary → AI → report)
- [ ] Can answer "How would you add caching?" or "How would you handle private repos?"

---

**When all boxes are checked, you're ready to submit and interview.**
