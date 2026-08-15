"""
Minimal MCP client test — connects to server.py over stdio (subprocess),
performs the full MCP handshake, lists tools, and calls analyze_repo.

This replicates exactly what Claude Desktop / Kiro / MCP Inspector do.
No Node.js required.
"""
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    repo_url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/pallets/click"

    print(f"MCP Client Test")
    print(f"{'='*60}")
    print(f"Connecting to server.py via stdio...")
    print(f"Target repo: {repo_url}\n")

    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            # ── Step 1: Initialize ────────────────────────────────────────
            print("Step 1/3 — Sending initialize...")
            await session.initialize()
            print("✅ Handshake complete\n")

            # ── Step 2: List tools ────────────────────────────────────────
            print("Step 2/3 — Calling tools/list...")
            tools = await session.list_tools()
            print(f"✅ Tools available: {len(tools.tools)}")
            for t in tools.tools:
                print(f"   • {t.name}: {t.description[:80]}...")
            print()

            # ── Step 3: Call analyze_repo ─────────────────────────────────
            print(f"Step 3/3 — Calling analyze_repo({repo_url})...")
            print("(This takes 30-60 seconds — Gemini + Groq running)\n")

            result = await session.call_tool(
                "analyze_repo",
                arguments={"repo_url": repo_url},
            )

            # Parse and display the result
            raw = result.content[0].text
            data = json.loads(raw)

            if "error" in data:
                print(f"❌ Tool returned error: {data['error']}")
                return

            print("✅ Analysis complete!\n")
            print("=" * 60)
            print(f"  Repo          : {data['repo_full_name']}")
            print(f"  Overall Score : {data['overall_score']}/100")
            print(f"  Overall Grade : {data['overall_grade']}")
            print(f"  Analyzed At   : {data['analyzed_at']}")
            print()
            print("  Category Scores:")
            categories = [
                "code_quality", "documentation", "testing", "security",
                "ci_cd", "project_structure", "dependencies", "best_practices"
            ]
            for cat in categories:
                c = data[cat]
                bar = "█" * (c["score"] // 10) + "░" * (10 - c["score"] // 10)
                print(f"    {cat:<20} {bar} {c['score']:>3}/100  {c['grade']}")

            print()
            print("  Executive Summary:")
            summary = data.get("executive_summary", "N/A")
            # Word-wrap at 60 chars
            words = summary.split()
            line = "    "
            for word in words:
                if len(line) + len(word) > 64:
                    print(line)
                    line = "    " + word + " "
                else:
                    line += word + " "
            if line.strip():
                print(line)

            print()
            print("  Top Strengths:")
            for s in data.get("top_strengths", [])[:3]:
                print(f"    ✅ {s}")

            print()
            print("  Top Issues:")
            for i in data.get("top_issues", [])[:3]:
                print(f"    ⚠️  {i}")

            print()
            print("  Priority Recommendations:")
            for r in data.get("prioritized_recommendations", [])[:5]:
                icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(r["priority"], "•")
                print(f"    {icon} [{r['priority'].upper()}] {r['title']} (effort: {r['effort']})")
                print(f"       {r['description'][:80]}")

            print()
            print("=" * 60)
            print("✅ Full MCP round-trip test passed!")
            print(f"   The server correctly handled: initialize → tools/list → tools/call")


if __name__ == "__main__":
    asyncio.run(main())
