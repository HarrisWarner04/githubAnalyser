"""
GitHub REST API fetcher (async).
"""
from __future__ import annotations
import base64, re
import httpx
from src import config
from src.models import RepoData, RepoFile

API = "https://api.github.com"
MAX_BYTES = config.MAX_FILE_SIZE_KB * 1024

SRC_EXT = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h", ".swift", ".kt", ".scala"}
CFG_NAMES = {"dockerfile", "docker-compose.yml", "makefile", "pyproject.toml", "setup.py", "package.json", ".eslintrc", ".prettierrc", "requirements.txt"}
DOC_EXT = {".md", ".rst", ".txt"}
TEST_RE = re.compile(r"(^|/)tests?/|^test_|_test\.|\.test\.|__tests__", re.I)
WF_DIR = ".github/workflows"

def _hdr():
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if config.GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    return h

def _parse_url(url: str):
    url = url.rstrip("/").removesuffix(".git")
    m = re.search(r"github\.com[/:]([^/]+)/([^/]+)$", url)
    if not m:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return m.group(1), m.group(2)

async def _get(client, path):
    r = await client.get(f"{API}{path}", headers=_hdr())
    r.raise_for_status()
    return r.json()

async def _get_file(client, owner, repo, path):
    try:
        data = await _get(client, f"/repos/{owner}/{repo}/contents/{path}")
        if isinstance(data, list) or data.get("size", 0) > MAX_BYTES:
            return None
        enc, raw = data.get("encoding"), data.get("content", "")
        if enc == "base64":
            return base64.b64decode(raw).decode("utf-8", errors="replace")
        return raw or None
    except:
        return None

def _classify(path: str):
    lp = path.lower()
    name = lp.rsplit("/", 1)[-1]
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if lp.startswith(WF_DIR.lower()): return "workflow"
    if TEST_RE.search(lp): return "test"
    if name in CFG_NAMES: return "config"
    if ext in DOC_EXT: return "doc"
    if ext in SRC_EXT: return "source"
    return "other"

async def _tree(client, owner, repo, branch):
    try:
        data = await _get(client, f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
        return [i["path"] for i in data.get("tree", []) if i.get("type") == "blob"]
    except:
        return []

async def fetch_repo(repo_url: str) -> RepoData:
    owner, name = _parse_url(repo_url)
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        meta = await _get(c, f"/repos/{owner}/{name}")
        branch = meta.get("default_branch", "main")
        paths = await _tree(c, owner, name, branch)

        readme = None
        for cand in ("README.md", "README.rst", "README"):
            if any(p.upper() == cand.upper() for p in paths):
                readme = await _get_file(c, owner, name, cand)
                if readme: break

        groups = {"source": [], "test": [], "doc": [], "config": [], "workflow": []}
        for p in paths:
            cat = _classify(p)
            if cat in groups:
                groups[cat].append(p)

        async def fetch_group(ps, lim):
            fs = []
            for p in ps[:lim]:
                cont = await _get_file(c, owner, name, p)
                if cont:
                    fs.append(RepoFile(path=p, content=cont, size_bytes=len(cont.encode())))
            return fs

        lim = config.MAX_SOURCE_FILES
        return RepoData(
            owner=owner, name=name, full_name=f"{owner}/{name}",
            description=meta.get("description"), default_branch=branch,
            primary_language=meta.get("language"), topics=meta.get("topics", []),
            stars=meta.get("stargazers_count", 0), forks=meta.get("forks_count", 0),
            open_issues=meta.get("open_issues_count", 0),
            license=meta.get("license", {}).get("name") if meta.get("license") else None,
            created_at=meta.get("created_at", ""), updated_at=meta.get("updated_at", ""),
            readme=readme, file_tree=paths,
            source_files=await fetch_group(groups["source"], lim),
            test_files=await fetch_group(groups["test"], lim),
            doc_files=await fetch_group(groups["doc"], 6),
            config_files=await fetch_group(groups["config"], 20),
            workflow_files=await fetch_group(groups["workflow"], 10),
        )
