import httpx
from typing import List
from backend.models import Job


async def fetch_jobs(query: str = "data engineer", limit: int = 20) -> List[Job]:
    url = "https://remotive.com/api/remote-jobs"
    params = {"search": query, "limit": limit}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[Remotive] error: {e}")
            return []

    jobs = []
    for item in data.get("jobs", []):
        jobs.append(Job(
            id=f"remotive_{item['id']}",
            title=item.get("title", ""),
            company=item.get("company_name", ""),
            location=item.get("candidate_required_location", "Worldwide"),
            description=_clean(item.get("description", "")),
            url=item.get("url", ""),
            salary=item.get("salary", ""),
            tags=item.get("tags", []),
            source="Remotive",
            published_at=item.get("publication_date", ""),
        ))
    return jobs


def _clean(html: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()
