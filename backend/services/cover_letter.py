from backend.models import CoverLetterRequest
from backend.services.llm import chat


async def generate(req: CoverLetterRequest, profile: str, override: dict | None = None) -> str:
    prompt = f"""Write a professional cover letter for the following job application.

CANDIDATE PROFILE:
{profile}

JOB DETAILS:
Title: {req.job_title}
Company: {req.company}

Job Description (first 1500 chars):
{req.description[:1500]}

Instructions:
- Write a concise, professional cover letter (3-4 paragraphs)
- Open with a strong hook connecting the candidate's most relevant experience to the role
- Highlight 2-3 specific achievements with measurable impact from the candidate's background
- Show genuine interest in the company and role
- Close with a clear call to action
- Tone: confident but not arrogant, professional, data-driven
- Do NOT use generic phrases like "I am writing to express my interest"
- Address it to "Hiring Team" since we don't know the hiring manager's name
- Keep it under 350 words

Return only the cover letter text, no subject line or meta-commentary."""

    return (await chat(prompt, json_mode=False, override=override)).strip()
