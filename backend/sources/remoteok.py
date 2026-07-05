import httpx
from typing import List
from backend.models import Job


async def fetch_jobs(query: str = "data-engineer", limit: int = 20) -> List[Job]:
    tag = query.lower().replace(" ", "-")
    url = f"https://remoteok.com/api?tag={tag}"
    headers = {"User-Agent": "JobSeekerApp/1.0"}

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[RemoteOK] error: {e}")
            return []

    jobs = []
    for item in data:
        if not isinstance(item, dict) or "id" not in item:
            continue
        jobs.append(Job(
            id=f"remoteok_{item['id']}",
            title=item.get("position", ""),
            company=item.get("company", ""),
            location=item.get("location", "Remote"),
            description=_clean(item.get("description", "")),
            url=item.get("url", ""),
            salary=item.get("salary", ""),
            tags=item.get("tags", []),
            source="RemoteOK",
            published_at=item.get("date", ""),
        ))
        if len(jobs) >= limit:
            break
    return jobs


def _clean(html: str) -> str:
    import re
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()
