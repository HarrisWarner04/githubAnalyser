"""
GitHub Repo Analyzer — MCP Server

Supports both transports:
  - stdio  (default): for local MCP hosts (Claude Desktop, Kiro, Cursor)
  - streamable-http : for remote deployment on a VM

Usage:
    python server.py                     # stdio mode (local)
    python server.py --http              # HTTP mode on port 8000 (deployment)
    python server.py --http --port 9000  # HTTP on custom port

Testing:
    npx @modelcontextprotocol/inspector python server.py   # MCP Inspector
"""
from __future__ import annotations
import argparse
import json
import logging
import sys

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

from src.github.fetcher import fetch_repo
from src.analyzers.summarizer import build_summary
from src.analyzers.gemini import GeminiAnalyzer
from src.analyzers.groq import GroqAnalyzer
from src.report.generator import generate

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("MCP SDK v%s import: %s", "2" if _SDK_V2 else "1", "MCPServer" if _SDK_V2 else "FastMCP")

# ── Server ─────────────────────────────────────────────────────────────────────
mcp = MCPServer("github-analyzer")

# Analyzer instances — created once and reused across all tool calls
_gemini = GeminiAnalyzer()
_groq   = GroqAnalyzer()


# ── Tool definition ───────────────────────────────────────────────────────────

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
    logger.info("Tool called: analyze_repo(%s)", repo_url)

    try:
        # 1. Fetch repository data from GitHub
        logger.info("Step 1/4 — Fetching repo data...")
        repo = await fetch_repo(repo_url)
        logger.info("Fetched %s: %d source files, %d total files",
                    repo.full_name, len(repo.source_files), len(repo.file_tree))

        # 2. Build a token-safe summary for the LLMs
        logger.info("Step 2/4 — Building summary...")
        summary = build_summary(repo)
        logger.info("Summary: %d chars", len(summary))

        # 3. Gemini — deep qualitative analysis (8 categories)
        logger.info("Step 3/4 — Running Gemini analysis...")
        gemini_dict = await _gemini.analyse(summary)
        gemini_raw  = json.dumps(gemini_dict, indent=2)
        logger.info("Gemini done")

        # 4. Groq — fast prioritised recommendations
        logger.info("Step 4/4 — Running Groq scoring...")
        groq_recs = await _groq.score(summary, gemini_raw)
        logger.info("Groq done: %d recommendations", len(groq_recs))

        # 5. Merge into typed AnalysisResult and return as JSON
        result = generate(repo, gemini_dict, groq_recs)
        logger.info("Analysis complete: %s score=%d grade=%s",
                    repo.full_name, result.overall_score, result.overall_grade)
        return result.model_dump_json(indent=2)

    except Exception as exc:
        logger.exception("Analysis failed for %s: %s", repo_url, exc)
        return json.dumps({"error": str(exc), "repo_url": repo_url}, indent=2)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GitHub Analyzer MCP Server")
    parser.add_argument("--http",  action="store_true",
                        help="Use Streamable HTTP transport instead of stdio")
    parser.add_argument("--host",  default="0.0.0.0",
                        help="Host for HTTP transport (default: 0.0.0.0)")
    parser.add_argument("--port",  type=int, default=8000,
                        help="Port for HTTP transport (default: 8000)")
    args = parser.parse_args()

    if args.http:
        logger.info("Starting HTTP transport on %s:%d/mcp", args.host, args.port)
        logger.info("Clients connect to: http://%s:%d/mcp", args.host, args.port)
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
