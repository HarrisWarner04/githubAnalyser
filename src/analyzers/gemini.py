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
        self.gemini_key = config.GEMINI_API_KEY
        self.groq_key = config.GROQ_API_KEY
        self.client = genai.Client(api_key=self.gemini_key) if self.gemini_key else None

    async def _fallback_groq(self, summary: str) -> dict:
        """Fallback to Groq if Gemini is geographically restricted."""
        from groq import Groq
        logger.info("Running qualitative analysis via Groq fallback...")
        groq_client = Groq(api_key=self.groq_key)
        
        def _call_groq():
            return groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile" if "70b" in config.GROQ_MODEL else config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": GEMINI_SYS},
                    {"role": "user", "content": gemini_prompt(summary)},
                ],
                temperature=0.2,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
        
        comp = await asyncio.to_thread(_call_groq)
        raw = comp.choices[0].message.content or ""
        return self._parse(raw)

    async def analyse(self, summary: str) -> dict:
        """Run analysis with Gemini, automatically falling back to Groq if location restricted."""
        if not self.client:
            return await self._fallback_groq(summary)

        try:
            return await self._call_gemini_with_retry(summary)
        except Exception as exc:
            err_msg = str(exc)
            if "location is not supported" in err_msg or "FAILED_PRECONDITION" in err_msg or "400" in err_msg:
                logger.warning("Gemini location restricted on this VM (%s). Switching to Groq fallback...", err_msg)
                return await self._fallback_groq(summary)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=5, max=30),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _call_gemini_with_retry(self, summary: str) -> dict:
        """Run Gemini analysis in a thread."""
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
            raise ValueError(f"No JSON object in AI response: {txt[:300]!r}")
        return json.loads(txt[s:e + 1])
