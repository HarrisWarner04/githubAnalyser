"""
Gemini analyzer — deep qualitative code analysis.
Uses google-genai SDK with asyncio.to_thread to avoid blocking the event loop,
since the google-genai client is synchronous.
"""
from __future__ import annotations
import asyncio
import json
import logging
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from src import config
from src.analyzers.prompts import GEMINI_SYS, gemini_prompt

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Retry on 503 (overloaded) and 429 (rate limit), not on 404 (bad model)."""
    msg = str(exc)
    return "503" in msg or "429" in msg or "UNAVAILABLE" in msg or "RESOURCE_EXHAUSTED" in msg


class GeminiAnalyzer:
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(min=10, max=60),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def analyse(self, summary: str) -> dict:
        """Run Gemini analysis in a thread (SDK is sync) and return parsed JSON."""
        def _call():
            return self.client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=gemini_prompt(summary),
                config=types.GenerateContentConfig(
                    system_instruction=GEMINI_SYS,
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
            )

        resp = await asyncio.to_thread(_call)
        raw = resp.text or ""
        if not raw:
            raise ValueError("Gemini returned empty response")
        logger.debug("Gemini response: %d chars", len(raw))
        return self._parse(raw)

    @staticmethod
    def _parse(txt: str) -> dict:
        txt = txt.strip()
        # Strip markdown fences if model wraps output
        if txt.startswith("```"):
            txt = "\n".join(
                l for l in txt.splitlines() if not l.strip().startswith("```")
            ).strip()
        s, e = txt.find("{"), txt.rfind("}")
        if s == -1 or e == -1:
            raise ValueError(f"No JSON object in Gemini response: {txt[:300]!r}")
        return json.loads(txt[s:e + 1])
