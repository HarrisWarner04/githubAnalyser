"""
Standalone test script — bypasses MCP protocol to test the core pipeline directly.
Use this to verify your API keys and logic work before testing the MCP server.

Run:
    python test_standalone.py
"""
import asyncio
import json
from src.github.fetcher import fetch_repo
from src.analyzers.summarizer import build_summary
from src.analyzers.gemini import GeminiAnalyzer
from src.analyzers.groq import GroqAnalyzer
from src.report.generator import generate


async def main():
    # Test with a small, well-known repo
    test_url = "https://github.com/tiangolo/fastapi"

    print(f"🔍 Fetching {test_url}...")
    repo = await fetch_repo(test_url)
    print(f"✅ Fetched {repo.full_name}: {len(repo.source_files)} source files")

    print("\n📝 Building summary...")
    summary = build_summary(repo)
    print(f"✅ Summary: {len(summary)} chars")

    print("\n🤖 Running Gemini analysis...")
    gemini = GeminiAnalyzer()
    gemini_dict = await gemini.analyse(summary)
    print(f"✅ Gemini: overall score estimate ~ {gemini_dict.get('code_quality', {}).get('score', '?')}")

    print("\n⚡ Running Groq scoring...")
    groq = GroqAnalyzer()
    groq_recs = await groq.score(summary, json.dumps(gemini_dict))
    print(f"✅ Groq: {len(groq_recs)} recommendations")

    print("\n📊 Generating final report...")
    result = generate(repo, gemini_dict, groq_recs)
    print(f"✅ Final score: {result.overall_score} ({result.overall_grade})")

    print("\n" + "="*70)
    print("FULL REPORT (first 1000 chars):")
    print("="*70)
    print(result.model_dump_json(indent=2)[:1000])
    print("\n✅ All systems working! MCP server is ready to run.")


if __name__ == "__main__":
    asyncio.run(main())
