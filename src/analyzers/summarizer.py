"""Converts RepoData → compact text summary."""
from src.models import RepoData

def build_summary(repo: RepoData) -> str:
    lines = [
        f"Repo: {repo.full_name}",
        f"Desc: {repo.description or 'N/A'}",
        f"Lang: {repo.primary_language or 'N/A'}",
        f"Topics: {', '.join(repo.topics) or 'N/A'}",
        f"Stars: {repo.stars}  Forks: {repo.forks}  Issues: {repo.open_issues}",
        f"License: {repo.license or 'None'}",
        "",
        "=== FILE TREE (first 100) ===",
        *repo.file_tree[:100],
        "",
    ]
    if repo.readme:
        lines += ["=== README ===", repo.readme[:1500], ""]
    for grp, lbl in [(repo.source_files, "SOURCE"), (repo.test_files, "TESTS"), (repo.config_files, "CONFIG"), (repo.workflow_files, "CI/CD")]:
        if grp:
            lines.append(f"=== {lbl} ===")
            for f in grp[:8]:
                lines.append(f"--- {f.path} ---")
                lines.append(f.content[:500])
    return "\n".join(lines)
