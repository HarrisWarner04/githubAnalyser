#!/usr/bin/env python3
"""
Evaluation Harness for GitHub Analyzer MCP Server
==================================================

Runs comprehensive tests covering:
- Environment setup
- Dependency validation  
- MCP protocol compliance
- End-to-end analysis
- Error handling
- Performance benchmarks

Usage:
    python eval_harness.py                 # Full test suite
    python eval_harness.py --benchmark     # Performance tests only
    python eval_harness.py --quick         # Skip slow integration tests
"""

import asyncio
import sys
import time
import json
from pathlib import Path
from typing import Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []

    def pass_test(self, name: str):
        self.passed += 1
        print(f"{GREEN}✅ {name}{RESET}")

    def fail_test(self, name: str, error: str):
        self.failed += 1
        self.errors.append((name, error))
        print(f"{RED}❌ {name}{RESET}")
        print(f"   {YELLOW}└─ {error}{RESET}")

    def skip_test(self, name: str, reason: str):
        self.skipped += 1
        print(f"{BLUE}⊘  {name} (skipped: {reason}){RESET}")

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*70}")
        print(f"{BOLD}Test Summary{RESET}")
        print(f"{'='*70}")
        print(f"  Total:   {total}")
        print(f"  {GREEN}Passed:  {self.passed}{RESET}")
        print(f"  {RED}Failed:  {self.failed}{RESET}")
        print(f"  {BLUE}Skipped: {self.skipped}{RESET}")
        
        if self.failed > 0:
            print(f"\n{RED}{BOLD}Failed Tests:{RESET}")
            for name, error in self.errors:
                print(f"  • {name}")
                print(f"    {error}")
        
        print(f"{'='*70}\n")
        return self.failed == 0


results = TestResult()


# ============================================================================
# SECTION 1: Environment & Dependencies
# ============================================================================

def test_python_version():
    """Verify Python 3.10+"""
    major, minor = sys.version_info[:2]
    if major == 3 and minor >= 10:
        results.pass_test(f"Python version ({major}.{minor})")
    else:
        results.fail_test(
            f"Python version ({major}.{minor})",
            "Requires Python 3.10 or higher"
        )


def test_env_file():
    """Check .env exists and has required keys"""
    env_path = Path(".env")
    if not env_path.exists():
        results.fail_test(".env file exists", "File not found")
        return

    content = env_path.read_text()
    required = ["GEMINI_API_KEY", "GROQ_API_KEY", "GITHUB_TOKEN"]
    missing = [k for k in required if k not in content or f"{k}=" not in content]
    
    if missing:
        results.fail_test(".env has required keys", f"Missing: {', '.join(missing)}")
    else:
        results.pass_test(".env has required keys")


def test_dependencies():
    """Verify all Python packages are installed"""
    import importlib.util
    packages = {
        "mcp": "mcp",
        "httpx": "httpx",
        "google.genai": "google-genai",
        "groq": "groq",
        "pydantic": "pydantic",
        "asyncio": "asyncio (stdlib)",
    }
    
    failed = []
    for module, pkg in packages.items():
        if importlib.util.find_spec(module) is None:
            failed.append(pkg)
    
    if failed:
        results.fail_test(
            "Python dependencies installed",
            f"Missing: {', '.join(failed)}"
        )
    else:
        results.pass_test("Python dependencies installed")


def test_server_imports():
    """Verify server.py and src modules load"""
    try:
        import server
        results.pass_test("server.py imports")
    except Exception as e:
        results.fail_test("server.py imports", str(e))
        return

    modules = [
        "src.config",
        "src.models",
        "src.github.fetcher",
        "src.analyzers.gemini",
        "src.analyzers.groq",
        "src.report.generator",
    ]
    
    for mod in modules:
        try:
            __import__(mod)
        except Exception as e:
            results.fail_test(f"Import {mod}", str(e))
            return
    
    results.pass_test("All src modules import")


# ============================================================================
# SECTION 2: Configuration
# ============================================================================

def test_config_loads():
    """Verify config.py loads environment variables"""
    try:
        from src.config import (
            GEMINI_API_KEY,
            GROQ_API_KEY,
            GITHUB_TOKEN,
            GEMINI_MODEL,
            GROQ_MODEL,
        )
        
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your-gemini-key-here":
            results.fail_test("GEMINI_API_KEY loaded", "Using placeholder value")
        elif not GROQ_API_KEY or GROQ_API_KEY == "your-groq-key-here":
            results.fail_test("GROQ_API_KEY loaded", "Using placeholder value")
        else:
            results.pass_test("Config loads API keys")
            
        # Models
        if GEMINI_MODEL and GROQ_MODEL:
            results.pass_test(f"Models configured ({GEMINI_MODEL}, {GROQ_MODEL})")
        else:
            results.fail_test("Models configured", "Missing model names")
            
    except Exception as e:
        results.fail_test("Config loads", str(e))


# ============================================================================
# SECTION 3: Unit Tests (Components)
# ============================================================================

async def test_github_fetcher():
    """Test GitHub API fetcher with small repo"""
    try:
        from src.github.fetcher import fetch_repo
        
        # Use a small, stable repo
        repo = await fetch_repo("https://github.com/pallets/click")
        
        if not repo.full_name:
            results.fail_test("GitHub fetcher", "No repo name returned")
        elif len(repo.source_files) == 0:
            results.fail_test("GitHub fetcher", "No source files fetched")
        else:
            results.pass_test(f"GitHub fetcher ({len(repo.source_files)} files)")
            
    except Exception as e:
        results.fail_test("GitHub fetcher", str(e))


async def test_gemini_analyzer():
    """Test Gemini API with minimal input"""
    try:
        from src.analyzers.gemini import GeminiAnalyzer
        
        analyzer = GeminiAnalyzer()
        
        # Minimal test input
        test_summary = """
        Repository: test/repo
        Files: main.py (50 lines)
        Description: Simple Python CLI tool
        """
        
        result = await analyzer.analyse(test_summary)
        
        required_keys = ["code_quality", "documentation", "testing", "security"]
        missing = [k for k in required_keys if k not in result]
        
        if missing:
            results.fail_test("Gemini analyzer", f"Missing keys: {missing}")
        else:
            # Check score format
            score = result.get("code_quality", {}).get("score")
            if isinstance(score, (int, float)) and 0 <= score <= 100:
                results.pass_test("Gemini analyzer")
            else:
                results.fail_test("Gemini analyzer", f"Invalid score: {score}")
                
    except Exception as e:
        results.fail_test("Gemini analyzer", str(e))


async def test_groq_scorer():
    """Test Groq recommendation scorer"""
    try:
        from src.analyzers.groq import GroqAnalyzer
        
        scorer = GroqAnalyzer()
        
        test_summary = "Repository: test/repo\nFiles: main.py"
        test_gemini = {"code_quality": {"score": 85, "issues": ["Missing docstrings"]}}
        
        recommendations = await scorer.score(test_summary, test_gemini)
        
        if not isinstance(recommendations, list):
            results.fail_test("Groq scorer", "Didn't return list")
        elif len(recommendations) == 0:
            results.skip_test("Groq scorer", "Returned empty list (acceptable)")
        else:
            # Check structure
            first = recommendations[0]
            if "priority" in first and ("title" in first or "recommendation" in first):
                results.pass_test(f"Groq scorer ({len(recommendations)} recs)")
            else:
                results.fail_test("Groq scorer", f"Invalid recommendation format: {list(first.keys())}")
                
    except Exception as e:
        results.fail_test("Groq scorer", str(e))


# ============================================================================
# SECTION 4: Integration Tests (Full Pipeline)
# ============================================================================

async def test_standalone_pipeline():
    """Test complete analysis pipeline without MCP"""
    try:
        from src.github.fetcher import fetch_repo
        from src.analyzers.summarizer import build_summary
        from src.analyzers.gemini import GeminiAnalyzer
        from src.analyzers.groq import GroqAnalyzer
        from src.report.generator import generate
        
        print(f"\n{BLUE}→ Running full pipeline on pallets/click...{RESET}")
        
        # Step 1: Fetch
        start = time.time()
        repo = await fetch_repo("https://github.com/pallets/click")
        fetch_time = time.time() - start
        print(f"  Fetched {len(repo.source_files)} files in {fetch_time:.1f}s")
        
        # Step 2: Summarize
        summary = build_summary(repo)
        print(f"  Summary: {len(summary)} chars")
        
        # Step 3: Gemini
        start = time.time()
        gemini = GeminiAnalyzer()
        analysis = await gemini.analyse(summary)
        gemini_time = time.time() - start
        print(f"  Gemini analysis: {gemini_time:.1f}s")
        
        # Step 4: Groq
        start = time.time()
        groq = GroqAnalyzer()
        recs = await groq.score(summary, analysis)
        groq_time = time.time() - start
        print(f"  Groq scoring: {len(recs)} recommendations in {groq_time:.1f}s")
        
        # Step 5: Report
        report = generate(repo, analysis, recs)
        
        # Validate
        if not (0 <= report.overall_score <= 100):
            results.fail_test("Standalone pipeline", f"Invalid score: {report.overall_score}")
        elif report.overall_grade not in ["A", "B", "C", "D", "F"]:
            results.fail_test("Standalone pipeline", f"Invalid grade: {report.overall_grade}")
        else:
            total_time = fetch_time + gemini_time + groq_time
            results.pass_test(f"Standalone pipeline ({total_time:.1f}s total, score: {report.overall_score})")
            
    except Exception as e:
        results.fail_test("Standalone pipeline", str(e))


# ============================================================================
# SECTION 5: MCP Protocol Tests
# ============================================================================

async def test_mcp_protocol():
    """Test MCP handshake and tool invocation"""
    try:
        import json
        import asyncio
        from mcp.client.stdio import stdio_client, StdioServerParameters
        from mcp.client.session import ClientSession
        
        server_params = StdioServerParameters(
            command="python",
            args=["server.py"],
        )
        
        print(f"\n{BLUE}→ Testing MCP protocol...{RESET}")
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize
                await session.initialize()
                print(f"  Handshake complete")
                
                # List tools
                tools_result = await session.list_tools()
                tools = tools_result.tools
                
                if len(tools) == 0:
                    results.fail_test("MCP protocol", "No tools discovered")
                    return
                
                tool = tools[0]
                if tool.name != "analyze_repo":
                    results.fail_test("MCP protocol", f"Expected analyze_repo, got {tool.name}")
                    return
                
                print(f"  Tool discovered: {tool.name}")
                
                # Call tool (quick test repo)
                print(f"  Calling tool (this takes 30-60s)...")
                start = time.time()
                
                result = await session.call_tool(
                    "analyze_repo",
                    {"repo_url": "https://github.com/pallets/click"}
                )
                
                call_time = time.time() - start
                
                # Parse response
                if not result.content:
                    results.fail_test("MCP protocol", "Empty response")
                    return
                
                response_text = result.content[0].text
                data = json.loads(response_text)
                
                if "overall_score" not in data:
                    results.fail_test("MCP protocol", "Missing overall_score in response")
                elif not (0 <= data["overall_score"] <= 100):
                    results.fail_test("MCP protocol", f"Invalid score: {data['overall_score']}")
                else:
                    results.pass_test(f"MCP protocol ({call_time:.1f}s, score: {data['overall_score']})")
                    
    except Exception as e:
        results.fail_test("MCP protocol", str(e))


# ============================================================================
# SECTION 6: Error Handling
# ============================================================================

async def test_invalid_url():
    """Test handling of invalid GitHub URL"""
    try:
        from src.github.fetcher import fetch_repo
        
        try:
            await fetch_repo("https://invalid-not-github.com/repo")
            results.fail_test("Invalid URL handling", "Should have raised error")
        except ValueError as e:
            if "github" in str(e).lower():
                results.pass_test("Invalid URL handling")
            else:
                results.fail_test("Invalid URL handling", f"Wrong error: {e}")
                
    except Exception as e:
        results.fail_test("Invalid URL handling", str(e))


async def test_nonexistent_repo():
    """Test handling of 404 repo"""
    try:
        from src.github.fetcher import fetch_repo
        
        try:
            await fetch_repo("https://github.com/nonexistent-org-123456/nonexistent-repo-789")
            results.fail_test("404 repo handling", "Should have raised error")
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                results.pass_test("404 repo handling")
            else:
                results.fail_test("404 repo handling", f"Wrong error: {e}")
                
    except Exception as e:
        results.fail_test("404 repo handling", str(e))


# ============================================================================
# SECTION 7: Performance Benchmarks
# ============================================================================

async def benchmark_small_repo():
    """Benchmark analysis on small repo (<50 files)"""
    try:
        from src.github.fetcher import fetch_repo
        from src.analyzers.summarizer import build_summary
        from src.analyzers.gemini import GeminiAnalyzer
        from src.analyzers.groq import GroqAnalyzer
        from src.report.generator import generate
        
        start = time.time()
        
        repo = await fetch_repo("https://github.com/pallets/click")
        summary = build_summary(repo)
        
        gemini = GeminiAnalyzer()
        analysis = await gemini.analyse(summary)
        
        groq = GroqAnalyzer()
        recs = await groq.score(summary, analysis)
        
        report = generate(repo, analysis, recs)
        
        total_time = time.time() - start
        
        if total_time > 60:
            results.fail_test(
                f"Small repo benchmark ({total_time:.1f}s)",
                "Should complete in <60s"
            )
        else:
            results.pass_test(f"Small repo benchmark ({total_time:.1f}s)")
            
    except Exception as e:
        results.fail_test("Small repo benchmark", str(e))


# ============================================================================
# Main Test Runner
# ============================================================================

async def run_all_tests(quick: bool = False, benchmark: bool = False):
    """Run full test suite"""
    
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}GitHub Analyzer MCP Server — Evaluation Harness{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    if benchmark:
        print(f"{YELLOW}Running performance benchmarks only...{RESET}\n")
        await benchmark_small_repo()
        results.summary()
        return
    
    # Section 1: Environment
    print(f"{BOLD}[1/7] Environment & Dependencies{RESET}")
    print("─" * 70)
    test_python_version()
    test_env_file()
    test_dependencies()
    test_server_imports()
    
    # Section 2: Configuration
    print(f"\n{BOLD}[2/7] Configuration{RESET}")
    print("─" * 70)
    test_config_loads()
    
    # Section 3: Unit tests
    print(f"\n{BOLD}[3/7] Unit Tests (Components){RESET}")
    print("─" * 70)
    await test_github_fetcher()
    await test_gemini_analyzer()
    await test_groq_scorer()
    
    # Section 4: Integration
    if not quick:
        print(f"\n{BOLD}[4/7] Integration Tests (Full Pipeline){RESET}")
        print("─" * 70)
        await test_standalone_pipeline()
    else:
        print(f"\n{BOLD}[4/7] Integration Tests{RESET}")
        print("─" * 70)
        results.skip_test("Standalone pipeline", "--quick mode")
    
    # Section 5: MCP Protocol
    if not quick:
        print(f"\n{BOLD}[5/7] MCP Protocol Tests{RESET}")
        print("─" * 70)
        await test_mcp_protocol()
    else:
        print(f"\n{BOLD}[5/7] MCP Protocol Tests{RESET}")
        print("─" * 70)
        results.skip_test("MCP protocol", "--quick mode")
    
    # Section 6: Error Handling
    print(f"\n{BOLD}[6/7] Error Handling{RESET}")
    print("─" * 70)
    await test_invalid_url()
    await test_nonexistent_repo()
    
    # Section 7: Performance
    if not quick:
        print(f"\n{BOLD}[7/7] Performance Benchmarks{RESET}")
        print("─" * 70)
        await benchmark_small_repo()
    else:
        print(f"\n{BOLD}[7/7] Performance Benchmarks{RESET}")
        print("─" * 70)
        results.skip_test("Small repo benchmark", "--quick mode")
    
    # Summary
    success = results.summary()
    
    if success:
        print(f"{GREEN}{BOLD}✅ All tests passed! Server is ready for deployment.{RESET}\n")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}❌ Some tests failed. Review errors above.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    benchmark = "--benchmark" in sys.argv
    
    try:
        asyncio.run(run_all_tests(quick=quick, benchmark=benchmark))
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(130)
