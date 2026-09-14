from datetime import datetime
from urllib.parse import quote

from fastapi import FastAPI, UploadFile, File, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import pdfplumber
import io

from src.pipeline import refresh_jobs
from src.model.recommender import recommend_jobs
from src.model.cover_letter import generate_cover_letter, guess_file_name

app = FastAPI()


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


@app.post("/refresh")
def refresh(req: RefreshRequest):
    inserted = refresh_jobs(req.keywords, req.location, req.max_items_per_source)
    return {"inserted": inserted}


@app.post("/recommend")
def recommend(req: RecommendRequest):
    results = recommend_jobs(req.profile_text, req.top_n, req.include_expired, req.location)
    return [
        {
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "description": job.description,
            "url": job.url,
            "source": job.source,
            "score": score,
        }
        for job, score in results
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


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")