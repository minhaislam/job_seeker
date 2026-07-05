from backend.models import Job
from backend.services.llm import chat, parse_json_response


def _relevant_description(description: str, max_chars: int = 1500) -> str:
    lower = description.lower()
    for keyword in ("requirement", "qualification", "what you'll need", "you have", "you bring", "must have"):
        idx = lower.find(keyword)
        if idx != -1:
            return description[max(0, idx - 50): idx + max_chars]
    return description[:max_chars]


async def score_job(job: Job, profile: str) -> dict:
    desc = _relevant_description(job.description)
    tags = ", ".join(job.tags) if job.tags else "none listed"

    prompt = f"""Score how well this job fits the candidate. Reply with ONLY a JSON object, no other text.

SCORING RULES:
- Cloud platforms are transferable: GCP=AWS=Azure (BigQuery≈Redshift, GCS≈S3, Datastream≈Glue)
- SQL expertise applies across all databases
- Data engineering experience transfers across industries and cloud providers
- Base score on ability to do the job, not exact keyword matches
- 80-100: Excellent — matches 80%+ requirements at correct seniority
- 60-79: Good — meets core requirements, minor gaps
- 40-59: Partial — solid fundamentals but notable gaps
- 20-39: Poor — major skill or seniority mismatch
- 0-19: Not a fit

CANDIDATE:
{profile}

JOB:
Title: {job.title}
Tags: {tags}
{desc}

Return ONLY this JSON:
{{"score": <integer 0-100>, "summary": "<one concise sentence>", "matched_skills": ["skill1", "skill2"], "missing_skills": ["skill1", "skill2"]}}"""

    try:
        text = await chat(prompt, json_mode=True)
        return parse_json_response(text)
    except Exception as e:
        print(f"[Matcher] error: {type(e).__name__}: {e}")
        return {
            "score": 50,
            "summary": "Could not score this job.",
            "matched_skills": [],
            "missing_skills": [],
        }
