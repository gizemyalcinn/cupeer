import os
from datetime import datetime
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Response, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import pdfplumber
import io

from src.pipeline import refresh_jobs
from src.model.recommender import recommend_jobs
from src.model.cover_letter import generate_cover_letter, guess_file_name
from src.db.storage import add_favorite, remove_favorite, get_favorite_jobs, get_favorite_ids
from src.preprocessing.schema import User
from src.auth.security import get_current_user
from src.auth.routes import router as auth_router

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "dev-insecure-secret-change-me"),
    max_age=60 * 60 * 24 * 30,
    same_site="lax",
)
app.include_router(auth_router)


class RefreshRequest(BaseModel):
    keywords: str
    location: str = "Turkey"
    max_items_per_source: int = 10


class RecommendRequest(BaseModel):
    profile_text: str
    top_n: int = 10
    include_expired: bool = False
    location: str = ""


class CoverLetterRequest(BaseModel):
    profile_text: str
    job_title: str
    company: str | None = None
    job_description: str = ""


class CoverLetterPdfRequest(BaseModel):
    text: str
    job_title: str | None = None
    company: str | None = None
    file_name: str = "on_yazi"


class FavoriteRequest(BaseModel):
    job_id: str
    favorite: bool


@app.post("/refresh")
def refresh(req: RefreshRequest):
    inserted = refresh_jobs(req.keywords, req.location, req.max_items_per_source)
    return {"inserted": inserted}


@app.post("/recommend")
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


@app.post("/favorite")
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


@app.post("/cover-letter")
def cover_letter(req: CoverLetterRequest):
    text = generate_cover_letter(
        req.profile_text, req.job_title, req.company, req.job_description
    )
    file_name = guess_file_name(req.profile_text)
    return {"text": text, "file_name": file_name}


@app.post("/cover-letter-pdf")
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


@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    contents = await file.read()
    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return {"text": text}


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/", NoCacheStaticFiles(directory="frontend", html=True), name="frontend")