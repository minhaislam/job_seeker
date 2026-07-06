import asyncio
import io
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Response
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

SESSION_COOKIE = "session_id"

_job_cache: dict[str, Job] = {}
# Per-browser state, keyed by session_id cookie. Each session gets its own CV
# and match scores so no two browsers/devices ever see each other's data.
_sessions: dict[str, dict] = {}

_STOPWORDS = {"in", "at", "for", "and", "or", "the", "a", "an", "job", "jobs", "remote", "us", "uk"}


def _get_session(request: Request, response: Response) -> dict:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id or session_id not in _sessions:
        session_id = uuid.uuid4().hex
        response.set_cookie(SESSION_COOKIE, session_id, httponly=True, samesite="lax")
        _sessions[session_id] = {"profile": "", "scores": {}, "suggestions": []}
    return _sessions[session_id]


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
async def upload_cv(request: Request, response: Response, file: UploadFile = File(...)):
    session = _get_session(request, response)

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

    session["profile"] = text
    session["scores"] = {}
    session["suggestions"] = await matcher.suggest_queries(text)
    print(f"[CV] uploaded: {len(text)} chars from {filename}")
    return {"status": "ok", "chars": len(text), "suggestions": session["suggestions"]}


@app.get("/api/cv/status")
async def cv_status(request: Request, response: Response):
    session = _get_session(request, response)
    profile = session["profile"]
    return {"uploaded": bool(profile), "chars": len(profile), "suggestions": session["suggestions"]}


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
async def get_job(job_id: str, request: Request, response: Response):
    session = _get_session(request, response)
    profile = session["profile"]
    if not profile:
        raise HTTPException(status_code=400, detail="No CV uploaded. Please upload your CV first.")

    job = _job_cache.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    score = session["scores"].get(job_id)
    if score is None:
        score_data = await matcher.score_job(job, profile)
        score = {
            "match_score": score_data.get("score", 50),
            "match_summary": score_data.get("summary", ""),
            "matched_skills": score_data.get("matched_skills", []),
            "missing_skills": score_data.get("missing_skills", []),
        }
        session["scores"][job_id] = score

    return {**job.model_dump(), **score}


@app.post("/api/cover-letter")
async def gen_cover_letter(req: CoverLetterRequest, request: Request, response: Response):
    session = _get_session(request, response)
    profile = session["profile"]
    if not profile:
        raise HTTPException(status_code=400, detail="No CV uploaded. Please upload your CV first.")
    text = await cover_letter.generate(req, profile)
    return {"cover_letter": text}


app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
