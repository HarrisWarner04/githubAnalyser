#!/usr/bin/env python3
"""
Diagnostic script to test all 3 APIs (GitHub, Gemini, Groq) directly from the VM.
Run on VM:
    docker compose exec mcp-server python test_keys_on_vm.py
or:
    python test_keys_on_vm.py
"""
import asyncio
import os
import sys

from src import config

print("=" * 60)
print("  API Key & Connectivity Diagnostic Test")
print("=" * 60)

print(f"1. GEMINI_API_KEY : {'[FOUND]' if config.GEMINI_API_KEY else '[MISSING]'} (Length: {len(config.GEMINI_API_KEY)})")
print(f"2. GROQ_API_KEY   : {'[FOUND]' if config.GROQ_API_KEY else '[MISSING]'} (Length: {len(config.GROQ_API_KEY)})")
print(f"3. GITHUB_TOKEN   : {'[FOUND]' if config.GITHUB_TOKEN else '[NOT SET - Optional]'}")
print("-" * 60)

# Test 1: GitHub API
print("\n[TEST 1/3] Testing GitHub API...")
try:
    import httpx
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "github-analyzer"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    r = httpx.get("https://api.github.com/repos/pallets/click", headers=headers, timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"  ✅ GitHub API OK! Fetched repo: {data.get('full_name')} (Stars: {data.get('stargazers_count')})")
    else:
        print(f"  ❌ GitHub API returned status {r.status_code}: {r.text[:200]}")
except Exception as exc:
    print(f"  ❌ GitHub API error: {exc}")

# Test 2: Gemini API
print("\n[TEST 2/3] Testing Gemini API...")
if not config.GEMINI_API_KEY:
    print("  ⚠️ GEMINI_API_KEY is empty in .env")
else:
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        resp = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents="Say 'OK'",
        )
        print(f"  ✅ Gemini API OK! Response: {resp.text.strip() if resp.text else 'empty'}")
    except Exception as exc:
        print(f"  ❌ Gemini API error: {exc}")

# Test 3: Groq API
print("\n[TEST 3/3] Testing Groq API...")
if not config.GROQ_API_KEY:
    print("  ⚠️ GROQ_API_KEY is empty in .env")
else:
    try:
        from groq import Groq
        groq_client = Groq(api_key=config.GROQ_API_KEY)
        res = groq_client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=10,
        )
        print(f"  ✅ Groq API OK! Model: {config.GROQ_MODEL}, Response: {res.choices[0].message.content.strip()}")
    except Exception as exc:
        print(f"  ❌ Groq API error: {exc}")

print("\n" + "=" * 60)
