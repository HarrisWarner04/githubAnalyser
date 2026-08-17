"""
Prioritized Recommendations & Scoring — supports OpenRouter and Groq.
"""
from __future__ import annotations
import asyncio
import json
import logging
import httpx
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential
from src import config
from src.analyzers.prompts import GROQ_SYS, groq_prompt

logger = logging.getLogger(__name__)


class GroqAnalyzer:
    def __init__(self):
        self.groq_key = config.GROQ_API_KEY
        self.openrouter_key = config.OPENROUTER_API_KEY
        self.client = Groq(api_key=self.groq_key) if self.groq_key else None

    async def _score_openrouter(self, summary: str, gemini_str: str) -> list[dict]:
        """Generate structured recommendations via OpenRouter."""
        candidate_models = [
            config.OPENROUTER_MODEL,
            "google/gemini-2.0-flash-lite-preview-02-05:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "mistralai/mistral-small-24b-instruct-2501:free",
        ]
        candidate_models = list(dict.fromkeys(candidate_models))

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "HTTP-Referer": "https://githubanalyser.bugbiceps.in",
            "X-Title": "GitHub Repo Analyzer",
            "Content-Type": "application/json"
        }

        for model in candidate_models:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": GROQ_SYS},
                    {"role": "user", "content": groq_prompt(summary, gemini_str)},
                ],
                "temperature": 0.1,
            }
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    r = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                    if r.status_code == 200:
                        data = r.json()
                        raw = data["choices"][0]["message"]["content"] or ""
                        return self._parse(raw)
            except Exception as exc:
                logger.warning("OpenRouter scoring with %s failed: %s", model, exc)

        return []

    async def score(self, summary: str, gemini_out: str | dict) -> list[dict]:
        """Run scoring: Prioritize OpenRouter if configured, then Groq."""
        gemini_str = json.dumps(gemini_out) if isinstance(gemini_out, dict) else gemini_out

        # 1. OpenRouter
        if self.openrouter_key:
            try:
                return await self._score_openrouter(summary, gemini_str)
            except Exception as exc:
                logger.warning("OpenRouter scoring failed (%s), trying Groq...", exc)

        # 2. Groq
        if self.client and self.groq_key:
            try:
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
                return self._parse(raw)
            except Exception as exc:
                logger.warning("Groq scoring failed: %s", exc)

        return []

    @staticmethod
    def _parse(txt: str) -> list[dict]:
        txt = txt.strip()
        if txt.startswith("```"):
            txt = "\n".join(
                l for l in txt.splitlines() if not l.strip().startswith("```")
            ).strip()
        s, e = txt.find("["), txt.rfind("]")
        if s == -1 or e == -1:
            logger.warning("No JSON array in AI scoring response, returning []")
            return []
        return json.loads(txt[s:e + 1])
