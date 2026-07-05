from pydantic import BaseModel
from typing import List, Optional


class Job(BaseModel):
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    salary: Optional[str] = ""
    tags: List[str] = []
    source: str
    published_at: Optional[str] = ""
    match_score: Optional[int] = None
    match_summary: Optional[str] = None
    matched_skills: Optional[List[str]] = None
    missing_skills: Optional[List[str]] = None


class SearchRequest(BaseModel):
    query: str = "data engineer"
    limit: int = 20


class CoverLetterRequest(BaseModel):
    job_id: str
    job_title: str
    company: str
    description: str
