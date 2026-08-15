"""AI prompt templates."""

GEMINI_SYS = """You are a senior software engineer and code quality expert.
Analyse GitHub repositories against industry best practices. Be specific, cite files when relevant."""

def gemini_prompt(summary: str):
    return f"""Analyse this repo and return ONLY a JSON object (no markdown):

{summary}

{{
  "code_quality": {{"score": 0-100, "issues": [...], "recommendations": [...]}},
  "documentation": {{"score": 0-100, "issues": [...], "recommendations": [...]}},
  "testing": {{"score": 0-100, "issues": [...], "recommendations": [...]}},
  "security": {{"score": 0-100, "issues": [...], "recommendations": [...]}},
  "ci_cd": {{"score": 0-100, "issues": [...], "recommendations": [...]}},
  "project_structure": {{"score": 0-100, "issues": [...], "recommendations": [...]}},
  "dependencies": {{"score": 0-100, "issues": [...], "recommendations": [...]}},
  "best_practices": {{"score": 0-100, "issues": [...], "recommendations": [...]}},
  "top_strengths": [...],
  "top_issues": [...],
  "executive_summary": "..."
}}

Scores: 90-100=A, 80-89=B, 65-79=C, 50-64=D, 0-49=F. Output ONLY JSON."""

GROQ_SYS = """Software architecture reviewer. Produce concise JSON only, no prose."""

def groq_prompt(summary: str, gemini_out: str):
    return f"""Given this repo and initial analysis, return prioritised recommendations as JSON array:

REPO:
{summary[:2000]}

ANALYSIS:
{gemini_out[:3000]}

[
  {{
    "priority": "critical|high|medium|low",
    "category": "...",
    "title": "...",
    "description": "...",
    "effort": "low|medium|high"
  }}
]

Max 12 recs, critical first. ONLY JSON array."""
