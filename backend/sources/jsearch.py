import httpx
from typing import List
from backend.models import Job
from backend.config import RAPIDAPI_KEY


async def fetch_jobs(query: str = "data engineer", limit: int = 20) -> List[Job]:
    if not RAPIDAPI_KEY:
        return []

    url = "https://jsearch.p.rapidapi.com/search-v2"
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "jsearch.p.rapidapi.com",
        "Content-Type": "application/json",
    }
    params = {
        "query": f"{query} remote",
        "num_pages": "2",
        "date_posted": "month",
        "country": "us",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[JSearch] error: {e}")
            return []

    items = data.get("data", {}).get("jobs", [])
    print(f"[JSearch] returned {len(items)} jobs")
    jobs = []
    for item in items[:limit]:
        salary = ""
        if item.get("job_min_salary") and item.get("job_max_salary"):
            cur = item.get("job_salary_currency", "USD")
            salary = f"{cur} {item['job_min_salary']:,}–{item['job_max_salary']:,}"

        jobs.append(Job(
            id=f"jsearch_{item.get('job_id', '')}",
            title=item.get("job_title", ""),
            company=item.get("employer_name", ""),
            location=item.get("job_city") or item.get("job_country") or "Remote",
            description=item.get("job_description", ""),
            url=item.get("job_apply_link", ""),
            salary=salary,
            tags=item.get("job_required_skills") or [],
            source=item.get("job_publisher", "JSearch"),
            published_at=item.get("job_posted_at_datetime_utc", ""),
        ))
    return jobs
