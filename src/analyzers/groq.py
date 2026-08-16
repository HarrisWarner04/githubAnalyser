"""
Groq analyzer — fast structured scoring and prioritised recommendations.
Uses groq-sdk with asyncio.to_thread since the SDK is synchronous.
"""
from __future__ import annotations
import asyncio
import json
import logging
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential
from src import config
from src.analyzers.prompts import GROQ_SYS, groq_prompt

logger = logging.getLogger(__name__)


class GroqAnalyzer:
    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=30), reraise=True)
    async def score(self, summary: str, gemini_out: str | dict) -> list[dict]:
        """Run Groq scoring in a thread (SDK is sync) and return parsed JSON list."""
        gemini_str = json.dumps(gemini_out) if isinstance(gemini_out, dict) else gemini_out

        def _call():
            return self.client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": GROQ_SYS},
                    {"role": "user",   "content": groq_prompt(summary, gemini_str)},
                ],
                temperature=0.1,
                max_tokens=2048,
            )

        comp = await asyncio.to_thread(_call)
        raw = comp.choices[0].message.content or ""
        logger.debug("Groq response: %d chars", len(raw))
        return self._parse(raw)

    @staticmethod
    def _parse(txt: str) -> list[dict]:
        txt = txt.strip()
        if txt.startswith("```"):
            txt = "\n".join(
                l for l in txt.splitlines() if not l.strip().startswith("```")
            ).strip()
        s, e = txt.find("["), txt.rfind("]")
        if s == -1 or e == -1:
            logger.warning("No JSON array in Groq response, returning []")
            return []
        return json.loads(txt[s:e + 1])
