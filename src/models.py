"""
Pydantic data models.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class RepoFile(BaseModel):
    path: str
    content: str
    size_bytes: int


class RepoData(BaseModel):
    owner: str
    name: str
    full_name: str
    description: str | None = None
    default_branch: str = "main"
    primary_language: str | None = None
    topics: list[str] = Field(default_factory=list)
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    license: str | None = None
    created_at: str = ""
    updated_at: str = ""

    readme: str | None = None
    file_tree: list[str] = Field(default_factory=list)
    source_files: list[RepoFile] = Field(default_factory=list)
    test_files: list[RepoFile] = Field(default_factory=list)
    doc_files: list[RepoFile] = Field(default_factory=list)
    config_files: list[RepoFile] = Field(default_factory=list)
    workflow_files: list[RepoFile] = Field(default_factory=list)


class CategoryScore(BaseModel):
    score: int = Field(ge=0, le=100)
    grade: str
    summary: str
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class PrioritizedRecommendation(BaseModel):
    priority: Literal["critical", "high", "medium", "low"]
    category: str
    title: str
    description: str
    effort: Literal["low", "medium", "high"]


class AnalysisResult(BaseModel):
    repo_full_name: str
    analyzed_at: str

    code_quality: CategoryScore
    documentation: CategoryScore
    testing: CategoryScore
    security: CategoryScore
    ci_cd: CategoryScore
    project_structure: CategoryScore
    dependencies: CategoryScore
    best_practices: CategoryScore

    overall_score: int = Field(ge=0, le=100)
    overall_grade: str
    executive_summary: str
    top_strengths: list[str] = Field(default_factory=list)
    top_issues: list[str] = Field(default_factory=list)
    prioritized_recommendations: list[PrioritizedRecommendation] = Field(default_factory=list)
    repo_metadata: dict = Field(default_factory=dict)
