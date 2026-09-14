import re
from bs4 import BeautifulSoup
from src.preprocessing.schema import Job

_WHITESPACE_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    if not text:
        return ""
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(separator=" ")
    return _WHITESPACE_RE.sub(" ", text).strip()


def clean_job(job: Job) -> Job:
    job.description = strip_html(job.description)
    job.title = _WHITESPACE_RE.sub(" ", job.title or "").strip()
    if job.company:
        job.company = _WHITESPACE_RE.sub(" ", job.company).strip()
    return job


def dedupe(jobs: list[Job]) -> list[Job]:
    seen: set[str] = set()
    result: list[Job] = []
    for job in jobs:
        key = job.url or job.id
        if key in seen:
            continue
        seen.add(key)
        result.append(job)
    return result