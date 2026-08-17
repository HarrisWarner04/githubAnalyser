"""
Configuration — loaded from environment / .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── API keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY", "").strip("\"' \r\n\t")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "").strip("\"' \r\n\t")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip("\"' \r\n\t")
GITHUB_TOKEN       = os.getenv("GITHUB_TOKEN", "").strip("\"' \r\n\t")

# ── Model selection ───────────────────────────────────────────────────────────
GEMINI_MODEL     = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GROQ_MODEL       = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto")

# ── Fetch limits ──────────────────────────────────────────────────────────────
MAX_SOURCE_FILES = int(os.getenv("MAX_SOURCE_FILES", "12"))
MAX_FILE_SIZE_KB = int(os.getenv("MAX_FILE_SIZE_KB", "80"))
