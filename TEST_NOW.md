# Test Right Now — 5 Steps

## Step 1: Set up environment (2 minutes)

```powershell
cd "d:\MCP Project\github-analyzer-mcp"

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure API keys (1 minute)

```powershell
# Create .env file from template
copy .env.example .env

# Edit .env with notepad
notepad .env
```

**Add your real keys:**
```bash
GEMINI_API_KEY=AIzaSy...your_actual_key_here
GROQ_API_KEY=gsk_...your_actual_key_here
GITHUB_TOKEN=  # Optional, leave blank for now
```

Save and close.

---

## Step 3: Test core pipeline (30 seconds)

```powershell
python test_standalone.py
```

**What to look for:**
- ✅ "Fetching ..." — GitHub API works
- ✅ "Running Gemini..." — Gemini API key valid
- ✅ "Running Groq..." — Groq API key valid
- ✅ "Final score: XX" — Everything worked
- ❌ Any "error" or traceback — check API keys

---

## Step 4: Test MCP server starts (10 seconds)

```powershell
python server.py
```

**Expected:** 
- Cursor blinks, no output, no errors
- This is normal — it's waiting for MCP host to connect via stdin
- Press `Ctrl+C` to stop

**If you see errors:** Check `.env` file, make sure API keys are set

---

## Step 5: Test with MCP Inspector (BEST TEST)

**Install Node.js first if you don't have it:**
https://nodejs.org/en/download/ (LTS version)

```powershell
# Test with Inspector
npx @modelcontextprotocol/inspector python server.py
```

**What happens:**
1. Downloads Inspector (first time only, ~30 seconds)
2. Opens browser to http://localhost:5173
3. Shows "github-analyzer" connected

**In the browser:**
1. Click "Tools" tab
2. Click "analyze_repo"
3. Paste: `https://github.com/pallets/click`
4. Click "Call Tool"
5. Wait 30-60 seconds
6. See full JSON report

**Success = JSON response with scores and recommendations**

---

## Quick Troubleshooting

| What you see | What it means | Fix |
|---|---|---|
| `ModuleNotFoundError: mcp` | Deps not installed | `pip install -r requirements.txt` |
| `KeyError: 'GEMINI_API_KEY'` | `.env` not loaded | Make sure `.env` file exists in project root |
| `401 Unauthorized` from Gemini | Bad API key | Check key at https://aistudio.google.com/apikey |
| `401 Unauthorized` from Groq | Bad API key | Check key at https://console.groq.com/keys |
| Inspector shows "Connection failed" | Server not running | Check `python server.py` works first |
| Tool returns `{"error": "..."}` | Normal — bad URL or API issue | Check error message for details |

---

## If Everything Works

**You're ready!** The MCP server is functional. Now you can:

1. **Add to Claude Desktop** — Edit config JSON, add the server
2. **Deploy to VM** — Follow DEPLOYMENT.md
3. **Practice demo** — Use Inspector, memorize talking points
4. **Review docs** — Read MCP_KNOWLEDGE_CHECKLIST.md

---

## If Something Fails

**Run validation step by step:**

```powershell
# 1. Check Python
python --version  # Should be 3.10+

# 2. Check imports
python -c "import mcp; print('MCP OK')"
python -c "import google.genai; print('Gemini OK')"
python -c "import groq; print('Groq OK')"

# 3. Check .env
type .env  # Should show GEMINI_API_KEY=... and GROQ_API_KEY=...

# 4. Test GitHub API (no auth needed)
python -c "import httpx; r = httpx.get('https://api.github.com'); print(r.status_code)"
# Should print 200

# 5. Test config loading
python -c "from src import config; print(config.GEMINI_API_KEY[:10])"
# Should print first 10 chars of your key
```

---

**Once `test_standalone.py` succeeds, your MCP server is working. The rest is just integration.**
