"""Report generator — merges AI outputs into AnalysisResult."""
import logging
from datetime import datetime, timezone
from src.models import AnalysisResult, CategoryScore, PrioritizedRecommendation, RepoData

logger = logging.getLogger(__name__)

WEIGHTS = {
    "code_quality": 0.20, "documentation": 0.10, "testing": 0.15, "security": 0.20,
    "ci_cd": 0.10, "project_structure": 0.10, "dependencies": 0.10, "best_practices": 0.05,
}

def _grade(s: int):
    if s >= 90: return "A"
    if s >= 80: return "B"
    if s >= 65: return "C"
    if s >= 50: return "D"
    return "F"

def _cat(key, raw):
    sc = max(0, min(100, int(raw.get("score", 50))))
    return CategoryScore(
        score=sc, grade=_grade(sc),
        summary=raw.get("summary", raw.get("executive_summary", "")),
        issues=raw.get("issues", []),
        recommendations=raw.get("recommendations", []),
    )

def _recs(groq_recs):
    res = []
    vp, ve = {"critical", "high", "medium", "low"}, {"low", "medium", "high"}
    for it in groq_recs:
        try:
            pr, ef = it.get("priority", "medium"), it.get("effort", "medium")
            res.append(PrioritizedRecommendation(
                priority=pr if pr in vp else "medium",
                category=it.get("category", "General"),
                title=it.get("title", ""),
                description=it.get("description", ""),
                effort=ef if ef in ve else "medium",
            ))
        except:
            pass
    res.sort(key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(r.priority, 9))
    return res

def generate(repo: RepoData, gemini: dict, groq: list[dict]) -> AnalysisResult:
    cats = ["code_quality", "documentation", "testing", "security", "ci_cd", "project_structure", "dependencies", "best_practices"]
    cs = {c: _cat(c, gemini.get(c, {})) for c in cats}
    overall = round(sum(cs[c].score * WEIGHTS[c] for c in cats))
    return AnalysisResult(
        repo_full_name=repo.full_name,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        code_quality=cs["code_quality"], documentation=cs["documentation"], testing=cs["testing"],
        security=cs["security"], ci_cd=cs["ci_cd"], project_structure=cs["project_structure"],
        dependencies=cs["dependencies"], best_practices=cs["best_practices"],
        overall_score=overall, overall_grade=_grade(overall),
        executive_summary=gemini.get("executive_summary", ""),
        top_strengths=gemini.get("top_strengths", []),
        top_issues=gemini.get("top_issues", []),
        prioritized_recommendations=_recs(groq),
        repo_metadata={
            "full_name": repo.full_name, "description": repo.description,
            "primary_language": repo.primary_language, "stars": repo.stars,
            "forks": repo.forks, "license": repo.license,
        },
    )
