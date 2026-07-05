import asyncio
import io
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.models import Job, SearchRequest, CoverLetterRequest
from backend.sources import remotive, remoteok, jsearch
from backend.services import matcher, cover_letter

app = FastAPI(title="Job Seeker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_job_cache: dict[str, Job] = {}
_user_profile: str = ""

_STOPWORDS = {"in", "at", "for", "and", "or", "the", "a", "an", "job", "jobs", "remote", "us", "uk"}


def _is_relevant(job: Job, query: str) -> bool:
    words = [w for w in query.lower().split() if w not in _STOPWORDS and len(w) > 2]
    if not words:
        return True
    searchable = f"{job.title.lower()} {' '.join(job.tags).lower()}"
    return all(w in searchable for w in words)


@app.get("/")
async def index():
    return FileResponse("frontend/index.html")


@app.post("/api/cv")
async def upload_cv(file: UploadFile = File(...)):
    global _user_profile

    filename = file.filename or ""
    content = await file.read()

    if filename.lower().endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"PDF parse error: {e}")
    elif filename.lower().endswith(".txt"):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
    else:
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported.")

    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text could be extracted from the file.")

    _user_profile = text
    print(f"[CV] uploaded: {len(_user_profile)} chars from {filename}")
    return {"status": "ok", "chars": len(_user_profile)}


@app.get("/api/cv/status")
async def cv_status():
    return {"uploaded": bool(_user_profile), "chars": len(_user_profile)}


@app.post("/api/search")
async def search_jobs(req: SearchRequest):
    global _job_cache

    results = await asyncio.gather(
        remotive.fetch_jobs(req.query, req.limit),
        remoteok.fetch_jobs(req.query, req.limit),
        jsearch.fetch_jobs(req.query, req.limit),
    )

    all_jobs: list[Job] = []
    seen = set()
    for batch in results:
        for job in batch:
            if job.id not in seen and job.title and job.description:
                if _is_relevant(job, req.query):
                    seen.add(job.id)
                    all_jobs.append(job)

    for job in all_jobs:
        _job_cache[job.id] = job

    print(f"[Search] '{req.query}' → {len(all_jobs)} relevant jobs")
    return {"total": len(all_jobs), "jobs": [j.model_dump() for j in all_jobs]}


@app.get("/api/job/{job_id}")
async def get_job(job_id: str):
    if not _user_profile:
        raise HTTPException(status_code=400, detail="No CV uploaded. Please upload your CV first.")

    job = _job_cache.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.match_score is None:
        score_data = await matcher.score_job(job, _user_profile)
        job.match_score = score_data.get("score", 50)
        job.match_summary = score_data.get("summary", "")
        job.matched_skills = score_data.get("matched_skills", [])
        job.missing_skills = score_data.get("missing_skills", [])
        _job_cache[job_id] = job

    return job.model_dump()


@app.post("/api/cover-letter")
async def gen_cover_letter(req: CoverLetterRequest):
    if not _user_profile:
        raise HTTPException(status_code=400, detail="No CV uploaded. Please upload your CV first.")
    text = await cover_letter.generate(req, _user_profile)
    return {"cover_letter": text}


app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
