# Architecture — GitHub Analyzer MCP Server

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  MCP Host (Claude Desktop / Kiro / Cursor / MCP Inspector)          │
│                                                                      │
│  User: "Analyze github.com/fastapi/fastapi"                         │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         │ stdio (stdin/stdout) or HTTP POST
                         │ JSON-RPC: tools/call
                         │ {"name": "analyze_repo", "arguments": {...}}
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  server.py (MCPServer)                                               │
│                                                                      │
│  @mcp.tool()                                                         │
│  async def analyze_repo(repo_url: str) -> str                       │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ├─── 1. Fetch Repo ───────────────────────┐
                         │                                           │
                         ▼                                           │
           ┌─────────────────────────────┐                          │
           │  src/github/fetcher.py      │                          │
           │                             │                          │
           │  fetch_repo(url)            │                          │
           │  ├─ GET /repos/owner/name   │◄───── GitHub REST API   │
           │  ├─ GET /git/trees/branch   │       (httpx async)     │
           │  └─ GET /contents/file      │                          │
           │                             │                          │
           │  Returns: RepoData          │                          │
           │  - metadata (stars, forks)  │                          │
           │  - file_tree (all paths)    │                          │
           │  - source_files             │                          │
           │  - test_files               │                          │
           │  - config_files             │                          │
           │  - workflow_files           │                          │
           └─────────────┬───────────────┘                          │
                         │                                           │
                         ├─── 2. Build Summary ─────────────────────┤
                         │                                           │
                         ▼                                           │
           ┌─────────────────────────────┐                          │
           │  src/analyzers/             │                          │
           │  summarizer.py              │                          │
           │                             │                          │
           │  build_summary(repo)        │                          │
           │  ├─ Format metadata         │                          │
           │  ├─ Truncate file contents  │                          │
           │  └─ Return compact text     │                          │
           │                             │                          │
           │  Returns: str (4k-10k chars)│                          │
           └─────────────┬───────────────┘                          │
                         │                                           │
                         ├─── 3. Gemini Analysis ───────────────────┤
                         │                                           │
                         ▼                                           │
           ┌─────────────────────────────┐                          │
           │  src/analyzers/gemini.py    │                          │
           │                             │                          │
           │  GeminiAnalyzer.analyse()   │                          │
           │  ├─ Build prompt            │◄───── Gemini 2.5 Flash  │
           │  ├─ Call API                │       (google-genai)    │
           │  ├─ Parse JSON response     │       1M token context  │
           │  └─ Retry on failure        │                          │
           │                             │                          │
           │  Returns: dict              │                          │
           │  {                          │                          │
           │    "code_quality": {        │                          │
           │      "score": 85,           │                          │
           │      "issues": [...],       │                          │
           │      "recommendations": [...]│                          │
           │    },                       │                          │
           │    ... (8 categories) ...   │                          │
           │  }                          │                          │
           └─────────────┬───────────────┘                          │
                         │                                           │
                         ├─── 4. Groq Scoring ──────────────────────┤
                         │                                           │
                         ▼                                           │
           ┌─────────────────────────────┐                          │
           │  src/analyzers/groq.py      │                          │
           │                             │                          │
           │  GroqAnalyzer.score()       │                          │
           │  ├─ Build prompt w/ summary │◄───── Groq LLaMA 3 8B   │
           │  │   + Gemini output        │       (groq-sdk)        │
           │  ├─ Call API                │       Fast structured   │
           │  ├─ Parse JSON array        │       output            │
           │  └─ Retry on failure        │                          │
           │                             │                          │
           │  Returns: list[dict]        │                          │
           │  [                          │                          │
           │    {                        │                          │
           │      "priority": "critical",│                          │
           │      "category": "Security",│                          │
           │      "title": "...",        │                          │
           │      "description": "...",  │                          │
           │      "effort": "low"        │                          │
           │    },                       │                          │
           │    ...                      │                          │
           │  ]                          │                          │
           └─────────────┬───────────────┘                          │
                         │                                           │
                         ├─── 5. Generate Report ───────────────────┤
                         │                                           │
                         ▼                                           │
           ┌─────────────────────────────┐                          │
           │  src/report/generator.py    │                          │
           │                             │                          │
           │  generate(repo, gemini, groq)│                         │
           │  ├─ Create CategoryScore    │                          │
           │  │   for each category      │                          │
           │  ├─ Calculate weighted      │                          │
           │  │   overall score          │                          │
           │  ├─ Assign letter grades    │                          │
           │  ├─ Build recommendations   │                          │
           │  └─ Return AnalysisResult   │                          │
           │                             │                          │
           │  Returns: AnalysisResult    │                          │
           │  (Pydantic model)           │                          │
           └─────────────┬───────────────┘                          │
                         │                                           │
                         └─── 6. Serialize & Return ────────────────┘
                         │
                         │  result.model_dump_json(indent=2)
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  JSON Response (back to MCP Host)                                   │
│                                                                      │
│  {                                                                   │
│    "repo_full_name": "fastapi/fastapi",                             │
│    "overall_score": 88,                                             │
│    "overall_grade": "B",                                            │
│    "code_quality": { "score": 92, "grade": "A", ... },             │
│    "security": { "score": 78, "grade": "C", ... },                 │
│    ...                                                               │
│    "prioritized_recommendations": [...]                             │
│  }                                                                   │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         │ Host inserts into LLM context
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  LLM (Claude / GPT-4 / etc.)                                         │
│                                                                      │
│  "Based on the analysis, FastAPI scores 88/100 (B grade). Key       │
│   strengths include excellent type annotations and comprehensive    │
│   documentation. Priority improvements: add SECURITY.md and expand  │
│   test coverage for edge cases."                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## MCP Protocol Handshake (Before Tool Call)

```
┌─────────────┐                                    ┌─────────────┐
│  MCP Host   │                                    │  MCP Server │
│  (Claude)   │                                    │  (server.py)│
└──────┬──────┘                                    └──────┬──────┘
       │                                                  │
       │  1. Launch subprocess: python server.py         │
       ├────────────────────────────────────────────────►│
       │                                                  │
       │  2. initialize                                   │
       │  {"jsonrpc": "2.0", "method": "initialize"}     │
       ├────────────────────────────────────────────────►│
       │                                                  │
       │  3. initialized (server capabilities)            │
       │  {"result": {"capabilities": {"tools": {}}}}    │
       │◄─────────────────────────────────────────────────┤
       │                                                  │
       │  4. tools/list (discover available tools)        │
       │  {"jsonrpc": "2.0", "method": "tools/list"}     │
       ├────────────────────────────────────────────────►│
       │                                                  │
       │  5. tools/list result                            │
       │  {"result": {"tools": [                          │
       │    {                                             │
       │      "name": "analyze_repo",                     │
       │      "inputSchema": {                            │
       │        "type": "object",                         │
       │        "properties": {                           │
       │          "repo_url": {"type": "string"}          │
       │        }                                         │
       │      }                                           │
       │    }                                             │
       │  ]}}                                             │
       │◄─────────────────────────────────────────────────┤
       │                                                  │
       │  [User invokes tool in chat]                     │
       │                                                  │
       │  6. tools/call                                   │
       │  {"method": "tools/call",                        │
       │   "params": {                                    │
       │     "name": "analyze_repo",                      │
       │     "arguments": {                               │
       │       "repo_url": "https://..."                  │
       │     }                                            │
       │   }}                                             │
       ├────────────────────────────────────────────────►│
       │                                                  │
       │              [analysis runs]                     │
       │              (30-60 seconds)                     │
       │                                                  │
       │  7. tools/call result                            │
       │  {"result": {"content": [{                       │
       │    "type": "text",                               │
       │    "text": "{...full JSON...}"                   │
       │  }]}}                                            │
       │◄─────────────────────────────────────────────────┤
       │                                                  │
```

---

## Data Flow

```
GitHub URL
    │
    ▼
┌───────────────┐
│   RepoData    │  Pydantic model
│               │  - owner, name, stars, forks
│               │  - file_tree: list[str]
│               │  - source_files: list[RepoFile]
│               │  - test_files, config_files, etc.
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Text Summary │  str (4k-10k chars)
│               │  - Metadata
│               │  - File tree (first 100)
│               │  - README (first 1500 chars)
│               │  - Source files (first 500 chars each)
└───────┬───────┘
        │
        ├───────► Gemini 2.5 Flash
        │         (deep analysis)
        │
        ▼
┌───────────────┐
│  Gemini Dict  │  dict
│               │  {
│               │    "code_quality": {"score": 85, ...},
│               │    "security": {"score": 78, ...},
│               │    ...
│               │  }
└───────┬───────┘
        │
        ├───────► Groq LLaMA 3
        │         (+ summary, fast scoring)
        │
        ▼
┌───────────────┐
│  Groq List    │  list[dict]
│               │  [
│               │    {"priority": "critical", ...},
│               │    {"priority": "high", ...}
│               │  ]
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ AnalysisResult│  Pydantic model
│               │  - overall_score: int
│               │  - overall_grade: str
│               │  - code_quality: CategoryScore
│               │  - security: CategoryScore
│               │  - prioritized_recommendations: list[...]
│               │  - repo_metadata: dict
└───────┬───────┘
        │
        │ .model_dump_json()
        │
        ▼
┌───────────────┐
│  JSON String  │  str (return value of @mcp.tool())
│               │  MCP host parses and inserts into LLM context
└───────────────┘
```

---

## Category Scoring

```
Individual Category Scores (0-100)
    ↓
Letter Grades (A/B/C/D/F)
    ↓
Weighted Overall Score

Weights:
  Code Quality        20%  ████████████████████
  Security            20%  ████████████████████
  Testing             15%  ███████████████
  Documentation       10%  ██████████
  CI/CD               10%  ██████████
  Project Structure   10%  ██████████
  Dependencies        10%  ██████████
  Best Practices       5%  █████
                      ───
                     100%

Example:
  code_quality:       92 × 0.20 = 18.4
  security:           78 × 0.20 = 15.6
  testing:            85 × 0.15 = 12.75
  documentation:      90 × 0.10 =  9.0
  ci_cd:              75 × 0.10 =  7.5
  project_structure:  88 × 0.10 =  8.8
  dependencies:       82 × 0.10 =  8.2
  best_practices:     80 × 0.05 =  4.0
                              ───────
  Overall:                     84.25 → 84 (B)
```

---

## Transport Options

### stdio (Default)

```
┌─────────────────┐
│   MCP Host      │
│  (Claude / Kiro)│
└────────┬────────┘
         │
         │ spawns subprocess
         ▼
┌─────────────────┐
│  python server.py│
│  (child process)│
└────────┬────────┘
         │
    stdin/stdout (JSON-RPC messages)
         │
    No HTTP, no ports, no certificates
    Host manages lifecycle
```

### Streamable HTTP (Deployment)

```
┌─────────────────┐
│   MCP Host      │
│  (anywhere)     │
└────────┬────────┘
         │
         │ HTTP POST
         ▼
┌─────────────────┐
│  http://vm:8000/mcp │
│  (Starlette app)│
└────────┬────────┘
         │
    Multiple clients supported
    Requires deployment (Docker / VM)
```

---

## Error Handling Flow

```
analyze_repo() called
    │
    ├─► fetch_repo()
    │     └─► HTTP error → raise → catch in analyze_repo → return {"error": "..."}
    │
    ├─► GeminiAnalyzer.analyse()
    │     ├─► API error → tenacity retries 3×
    │     └─► Still fails → raise → catch → return {"error": "..."}
    │
    ├─► GroqAnalyzer.score()
    │     ├─► API error → tenacity retries 3×
    │     └─► Still fails → raise → catch → return {"error": "..."}
    │
    └─► All success → generate report → return JSON
```

---

## Free-Tier Rate Limits

```
┌──────────────────┬──────────────┬───────────────────┬──────────────┐
│  Service         │  Free Limit  │  Per Analysis     │  Daily Limit │
├──────────────────┼──────────────┼───────────────────┼──────────────┤
│  GitHub API      │  60 req/h    │  ~10 requests     │  ~1440/day   │
│  (no token)      │              │                   │              │
├──────────────────┼──────────────┼───────────────────┼──────────────┤
│  GitHub API      │  5000 req/h  │  ~10 requests     │  ~120k/day   │
│  (with token)    │              │                   │              │
├──────────────────┼──────────────┼───────────────────┼──────────────┤
│  Gemini 2.5      │  1500 req/d  │  1 request        │  1500/day    │
│  Flash           │  1M tok/min  │  ~4k-8k tokens    │              │
├──────────────────┼──────────────┼───────────────────┼──────────────┤
│  Groq LLaMA 3    │  14400 req/d │  1 request        │  14400/day   │
│  8B              │  30k tok/min │  ~1k-2k tokens    │              │
└──────────────────┴──────────────┴───────────────────┴──────────────┘

Bottleneck: Gemini (1500/day) → ~1500 analyses/day max
With MAX_SOURCE_FILES=8, can analyse larger repos within same quota
```

---

**This architecture demonstrates production-grade async Python, proper use of Pydantic for type safety, error handling with retries, and clean separation of concerns.**
