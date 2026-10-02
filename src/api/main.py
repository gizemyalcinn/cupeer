import logging
import mimetypes
import os
from datetime import datetime
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

# Sistemin MIME tablosunda woff2 olmayabilir; yazı tipleri doğru türle servis edilsin.
mimetypes.add_type("font/woff2", ".woff2")

from fastapi import FastAPI, UploadFile, File, Request, Response, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from src.pipeline import refresh_jobs
from src.model.recommender import recommend_jobs
from src.model.cover_letter import generate_cover_letter, guess_file_name
from src.model.cv_review import review_cv, CVReview
from google.genai.errors import ServerError
from src.db.storage import add_favorite, remove_favorite, get_favorite_jobs, get_favorite_ids
from src.preprocessing.schema import User
from src.auth.security import get_current_user, can_refresh
from src.auth.routes import router as auth_router
from src.api.hardening import (
    IS_PROD,
    MAX_BODY_BYTES,
    SECURITY_HEADERS,
    client_ip,
    enforce_limit,
    is_https,
    log_event,
    origin_allowed,
    rate_limit,
    read_pdf_text,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("cupeer")

SESSION_SECRET = os.getenv("SESSION_SECRET_KEY")
if not SESSION_SECRET:
    if IS_PROD:
        raise RuntimeError("SESSION_SECRET_KEY production ortamında tanımlı olmalı.")
    SESSION_SECRET = "dev-insecure-secret-change-me"

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=60 * 60 * 24 * 30,
    same_site="lax",
    https_only=IS_PROD,
)
app.include_router(auth_router)


@app.middleware("http")
async def hardening_middleware(request: Request, call_next):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_BODY_BYTES:
        log_event("request.rejected", request, reason="body_too_large")
        return JSONResponse({"detail": "İstek çok büyük."}, status_code=413)

    if not origin_allowed(request):
        log_event("request.rejected", request, reason="cross_origin", path=request.url.path)
        return JSONResponse({"detail": "İstek reddedildi."}, status_code=403)

    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if is_https(request):
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": "Gönderilen veri geçersiz."}, status_code=422)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Beklenmeyen bir hata oluştu."}, status_code=500)


class RefreshRequest(BaseModel):
    keywords: str = Field(min_length=1, max_length=100)
    location: str = Field("Turkey", max_length=100)
    max_items_per_source: int = Field(10, ge=1, le=10)


class RecommendRequest(BaseModel):
    profile_text: str = Field(max_length=30_000)
    top_n: int = Field(10, ge=1, le=50)
    include_expired: bool = False
    location: str = Field("", max_length=60)


class CoverLetterRequest(BaseModel):
    profile_text: str = Field(max_length=30_000)
    job_title: str = Field(max_length=300)
    company: str | None = Field(None, max_length=300)
    job_description: str = Field("", max_length=30_000)


class CoverLetterPdfRequest(BaseModel):
    text: str = Field(max_length=10_000)
    job_title: str | None = Field(None, max_length=300)
    company: str | None = Field(None, max_length=300)
    file_name: str = Field("on_yazi", max_length=120)


class FavoriteRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=200)
    favorite: bool


# Apify kredisi harcayan işlem: yalnızca site sahibi (REFRESH_ALLOWED_EMAILS) + kullanıcı başına ve genel sınır.
@app.post("/refresh", dependencies=[Depends(rate_limit("refresh-ip", 6, 3600))])
def refresh(request: Request, req: RefreshRequest, user: User | None = Depends(get_current_user)):
    if not user:
        raise HTTPException(401, "Yeni ilan çekmek için giriş yapmalısın.")
    if not can_refresh(request, user):
        log_event("refresh.denied", request, user=user.id)
        raise HTTPException(403, "Yeni ilan çekme yalnızca site sahibine açık.")
    enforce_limit(request, f"refresh-user:{user.id}", 3, 3600, "refresh-user")
    enforce_limit(request, "refresh-global", 12, 3600, "refresh-global")
    log_event("refresh.run", request, user=user.id)
    inserted = refresh_jobs(req.keywords, req.location, req.max_items_per_source)
    return {"inserted": inserted}


@app.post("/recommend", dependencies=[Depends(rate_limit("recommend", 40, 60))])
def recommend(req: RecommendRequest, user: User | None = Depends(get_current_user)):
    results = recommend_jobs(req.profile_text, req.top_n, req.include_expired, req.location)
    favorite_ids = get_favorite_ids(user.id) if user else set()
    return [
        {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "url": job.url,
            "source": job.source,
            "score": score,
            "is_favorite": job.id in favorite_ids,
        }
        for job, score in results
    ]


@app.post("/favorite", dependencies=[Depends(rate_limit("favorite", 120, 60))])
def favorite(req: FavoriteRequest, user: User | None = Depends(get_current_user)):
    if not user:
        raise HTTPException(401, "Favorilemek için giriş yapmalısın.")
    if req.favorite:
        add_favorite(user.id, req.job_id)
    else:
        remove_favorite(user.id, req.job_id)
    return {"ok": True}


@app.get("/favorites")
def favorites(user: User | None = Depends(get_current_user)):
    if not user:
        return []
    jobs = get_favorite_jobs(user.id)
    return [
        {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "url": job.url,
            "source": job.source,
            "is_favorite": job.is_favorite,
        }
        for job in jobs
    ]


@app.post("/cover-letter", dependencies=[Depends(rate_limit("cover-letter", 12, 600))])
def cover_letter(req: CoverLetterRequest):
    try:
        text = generate_cover_letter(
            req.profile_text, req.job_title, req.company, req.job_description
        )
    except ServerError:
        raise HTTPException(503, "Ön yazı servisi şu an yoğun, lütfen biraz sonra tekrar dene.")
    file_name = guess_file_name(req.profile_text)
    return {"text": text, "file_name": file_name}


@app.post("/cover-letter-pdf", dependencies=[Depends(rate_limit("cover-letter-pdf", 30, 600))])
def cover_letter_pdf(req: CoverLetterPdfRequest):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.set_margins(25, 25, 25)
    pdf.add_font("Tinos", "", "fonts/Tinos-Regular.ttf")
    pdf.add_font("Tinos", "B", "fonts/Tinos-Bold.ttf")

    # Tarih, sağa yaslı
    pdf.set_font("Tinos", "", 12)
    today = datetime.now().strftime("%d.%m.%Y")
    pdf.cell(0, 8, today, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(10)

    # Gövde metni
    pdf.set_font("Tinos", "", 12)
    for paragraph in req.text.split("\n"):
        if paragraph.strip() == "":
            pdf.ln(5)
        else:
            pdf.multi_cell(0, 7, paragraph, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf_bytes = bytes(pdf.output())
    encoded_name = quote(f"{req.file_name}.pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


@app.post("/extract-text", dependencies=[Depends(rate_limit("extract-text", 30, 600))])
async def extract_text(request: Request, file: UploadFile = File(...)):
    return {"text": await read_pdf_text(file, request)}


@app.post(
    "/cv-review",
    response_model=CVReview,
    dependencies=[Depends(rate_limit("cv-review", 8, 600))],
)
async def cv_review(request: Request, file: UploadFile = File(...)):
    text = await read_pdf_text(file, request)
    try:
        return await run_in_threadpool(review_cv, text)
    except ServerError:
        raise HTTPException(503, "CV analiz servisi şu an yoğun, lütfen biraz sonra tekrar dene.")


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/", NoCacheStaticFiles(directory="frontend", html=True), name="frontend")
