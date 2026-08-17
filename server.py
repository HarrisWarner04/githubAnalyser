"""
GitHub Repo Analyzer — MCP Server & Web Dashboard

Supports both transports and dual interfaces:
  - stdio  (default): for local MCP hosts (Claude Desktop, Kiro, Cursor)
  - streamable-http : for remote deployment on Azure VM / cloud
      → /mcp         : MCP Protocol endpoint (Streamable HTTP / SSE)
      → /            : Interactive Web Dashboard
      → /api/analyze : REST API endpoint (with CORS)
      → /api/health  : Healthcheck endpoint

Usage:
    python server.py                     # stdio mode (local MCP host)
    python server.py --http              # HTTP mode on port 8000 (Web + MCP)
    python server.py --http --port 9000  # HTTP on custom port

Testing:
    npx @modelcontextprotocol/inspector python server.py   # MCP Inspector
"""
from __future__ import annotations
import argparse
import json
import logging
import sys
from pathlib import Path

# ── MCP SDK import (works with both v1 and v2) ────────────────────────────────
try:
    from mcp.server import MCPServer          # v2 SDK
    _SDK_V2 = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer   # v1 FastMCP fallback
        _SDK_V2 = False
    except ImportError:
        print("ERROR: mcp package not installed. Run: pip install mcp[cli]", file=sys.stderr)
        sys.exit(1)

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, FileResponse, Response

from src.github.fetcher import fetch_repo
from src.analyzers.summarizer import build_summary
from src.analyzers.gemini import GeminiAnalyzer
from src.analyzers.groq import GroqAnalyzer
from src.report.generator import generate
from src.models import AnalysisResult

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("MCP SDK v%s import: %s", "2" if _SDK_V2 else "1", "MCPServer" if _SDK_V2 else "FastMCP")

# ── Paths & CORS ──────────────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
}

# ── Server ─────────────────────────────────────────────────────────────────────
mcp = MCPServer("github-analyzer")

# Analyzer instances — created once and reused across all tool calls & web requests
_gemini = GeminiAnalyzer()
_groq   = GroqAnalyzer()


# ── Shared Core Pipeline ───────────────────────────────────────────────────────

async def _execute_analysis(repo_url: str) -> AnalysisResult:
    """Core analysis logic shared between MCP tool and REST API."""
    logger.info("Step 1/4 — Fetching repo data for %s...", repo_url)
    try:
        repo = await fetch_repo(repo_url)
        logger.info("Fetched %s: %d source files, %d total files",
                    repo.full_name, len(repo.source_files), len(repo.file_tree))
    except Exception as exc:
        raise RuntimeError(f"GitHub fetch failed for {repo_url}: {exc}") from exc

    logger.info("Step 2/4 — Building token-safe summary...")
    summary = build_summary(repo)
    logger.info("Summary: %d chars", len(summary))

    logger.info("Step 3/4 — Running qualitative audit...")
    try:
        gemini_dict = await _gemini.analyse(summary)
        gemini_raw  = json.dumps(gemini_dict, indent=2)
        logger.info("Qualitative analysis complete")
    except Exception as exc:
        raise RuntimeError(f"AI Qualitative Analysis failed: {exc}") from exc

    logger.info("Step 4/4 — Running prioritized scoring...")
    try:
        groq_recs = await _groq.score(summary, gemini_raw)
        logger.info("Prioritized scoring complete: %d recommendations", len(groq_recs))
    except Exception as exc:
        logger.warning("Scoring step failed (%s), falling back to baseline recommendations...", exc)
        groq_recs = []

    result = generate(repo, gemini_dict, groq_recs)
    logger.info("Analysis complete for %s: score=%d grade=%s",
                repo.full_name, result.overall_score, result.overall_grade)
    return result


# ── MCP Tool definition ───────────────────────────────────────────────────────

@mcp.tool()
async def analyze_repo(repo_url: str) -> str:
    """
    Analyse a GitHub repository against industry best practices.

    Fetches the repository from GitHub, analyses it using Gemini (deep code
    analysis) and Groq/LLaMA (fast structured scoring), and returns a
    comprehensive JSON report.

    The report includes:
    - Per-category scores (0-100) and grades (A-F) for: code quality,
      documentation, testing, security, CI/CD, project structure,
      dependencies, and best practices
    - Weighted overall score and letter grade
    - Executive summary
    - Top strengths and top issues
    - Prioritised recommendations (critical → high → medium → low)
    - Repository metadata snapshot

    Args:
        repo_url: Full GitHub URL, e.g. https://github.com/owner/repo

    Returns:
        JSON string. Parse with json.loads() to get a dict.

    Examples:
        analyze_repo("https://github.com/fastapi/fastapi")
        analyze_repo("https://github.com/pallets/flask")
    """
    logger.info("MCP Tool called: analyze_repo(%s)", repo_url)
    try:
        result = await _execute_analysis(repo_url)
        return result.model_dump_json(indent=2)
    except Exception as exc:
        logger.exception("Analysis failed for %s: %s", repo_url, exc)
        return json.dumps({"error": str(exc), "repo_url": repo_url}, indent=2)


# ── Custom HTTP Routes (Web Frontend & REST API) ──────────────────────────────

@mcp.custom_route("/", methods=["GET"])
async def serve_index(request: Request) -> Response:
    """Serve the Web Frontend Dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file, media_type="text/html")
    return HTMLResponse(
        "<h1>GitHub Analyzer MCP Server</h1><p>Web dashboard static files not found.</p>"
    )


@mcp.custom_route("/static/{file_path:path}", methods=["GET"])
async def serve_static(request: Request) -> Response:
    """Serve static CSS, JS, and asset files with path safety verification."""
    rel_path = request.path_params.get("file_path", "")
    target = (STATIC_DIR / rel_path).resolve()
    # Path traversal protection
    if str(target).startswith(str(STATIC_DIR.resolve())) and target.is_file():
        media_type = None
        if target.suffix == ".css":
            media_type = "text/css"
        elif target.suffix == ".js":
            media_type = "application/javascript"
        elif target.suffix == ".html":
            media_type = "text/html"
        return FileResponse(target, media_type=media_type)
    return Response("File not found", status_code=404)


@mcp.custom_route("/api/health", methods=["GET", "OPTIONS"])
async def api_health(request: Request) -> Response:
    """Health check endpoint for Azure / load balancer monitoring."""
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=CORS_HEADERS)
    return JSONResponse(
        {
            "status": "healthy",
            "service": "github-analyzer-mcp",
            "capabilities": ["mcp-stdio", "mcp-streamable-http", "web-dashboard", "rest-api"]
        },
        headers=CORS_HEADERS
    )


@mcp.custom_route("/api/analyze", methods=["POST", "OPTIONS"])
async def api_analyze(request: Request) -> Response:
    """REST API endpoint for web clients (supports CORS)."""
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=CORS_HEADERS)

    try:
        payload = await request.json()
        repo_url = payload.get("repo_url", "").strip()
        if not repo_url:
            return JSONResponse(
                {"error": "Missing or empty 'repo_url' field in JSON request"},
                status_code=400,
                headers=CORS_HEADERS
            )

        logger.info("REST API called: /api/analyze for %s", repo_url)
        result = await _execute_analysis(repo_url)
        return JSONResponse(result.model_dump(), headers=CORS_HEADERS)

    except Exception as exc:
        logger.exception("REST API analysis failed: %s", exc)
        return JSONResponse(
            {"error": str(exc)},
            status_code=500,
            headers=CORS_HEADERS
        )


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GitHub Analyzer MCP Server & Web Dashboard")
    parser.add_argument("--http",  action="store_true",
                        help="Use Streamable HTTP transport instead of stdio")
    parser.add_argument("--host",  default="0.0.0.0",
                        help="Host for HTTP transport (default: 0.0.0.0)")
    parser.add_argument("--port",  type=int, default=8000,
                        help="Port for HTTP transport (default: 8000)")
    args = parser.parse_args()

    if args.http:
        logger.info("==================================================================")
        logger.info("Starting Dual Server on http://%s:%d", args.host, args.port)
        logger.info("  → Web Dashboard  : http://%s:%d/", args.host, args.port)
        logger.info("  → REST API       : http://%s:%d/api/analyze", args.host, args.port)
        logger.info("  → Health Check   : http://%s:%d/api/health", args.host, args.port)
        logger.info("  → MCP Protocol   : http://%s:%d/mcp", args.host, args.port)
        logger.info("==================================================================")
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            streamable_http_path="/mcp",
        )
    else:
        logger.info("Starting stdio transport — waiting for MCP host...")
        logger.info("Test with: npx @modelcontextprotocol/inspector python server.py")
        mcp.run()   # stdio is the default — blocks until host disconnects


if __name__ == "__main__":
    main()
