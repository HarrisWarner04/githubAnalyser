"""
AI Qualitative Analyzer — supports OpenRouter, Gemini, and Groq with automatic fallback.
"""
from __future__ import annotations
import asyncio
import json
import logging
import httpx
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
        self.openrouter_key = config.OPENROUTER_API_KEY
        self.client = genai.Client(api_key=self.gemini_key) if self.gemini_key else None

    async def _call_openrouter(self, summary: str) -> dict:
        """Run qualitative analysis via OpenRouter (globally accessible without cloud region blocks)."""
        candidate_models = [
            config.OPENROUTER_MODEL,
            "google/gemini-2.0-flash-lite-preview-02-05:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "mistralai/mistral-small-24b-instruct-2501:free",
            "deepseek/deepseek-r1:free"
        ]
        # Deduplicate while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "HTTP-Referer": "https://githubanalyser.bugbiceps.in",
            "X-Title": "GitHub Repo Analyzer",
            "Content-Type": "application/json"
        }

        last_error = None
        for model in candidate_models:
            logger.info("Attempting OpenRouter model: %s...", model)
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": GEMINI_SYS},
                    {"role": "user", "content": gemini_prompt(summary)},
                ],
                "temperature": 0.2,
            }
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                    if r.status_code == 200:
                        data = r.json()
                        raw = data["choices"][0]["message"]["content"] or ""
                        return self._parse(raw)
                    else:
                        err_text = r.text
                        logger.warning("OpenRouter model %s returned status %d: %s", model, r.status_code, err_text[:200])
                        last_error = f"HTTP {r.status_code}: {err_text[:200]}"
            except Exception as e:
                logger.warning("OpenRouter model %s exception: %s", model, e)
                last_error = str(e)

        raise RuntimeError(f"All OpenRouter models failed. Last error: {last_error}")

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
        """Run analysis: Prioritize OpenRouter if set (fixes region blocks), then Gemini, then Groq."""
        # 1. OpenRouter (Zero region restrictions)
        if self.openrouter_key:
            try:
                return await self._call_openrouter(summary)
            except Exception as exc:
                logger.warning("OpenRouter analysis failed (%s), trying alternate providers...", exc)

        # 2. Gemini (Direct)
        if self.client and self.gemini_key:
            try:
                return await self._call_gemini_with_retry(summary)
            except Exception as exc:
                err_msg = str(exc)
                logger.warning("Gemini failed (%s), trying fallback...", err_msg)

        # 3. Groq
        if self.groq_key:
            try:
                return await self._fallback_groq(summary)
            except Exception as exc:
                logger.warning("Groq failed (%s)...", exc)

        raise RuntimeError("No AI provider succeeded. Please check your OPENROUTER_API_KEY or GEMINI_API_KEY.")

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
