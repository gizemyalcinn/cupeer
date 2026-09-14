from src.scraping.apify_client import run_actor
from src.preprocessing.schema import Job

REMOTEOK_ACTOR_ID = "c5BsPGHJ2q085g0eq"


def scrape_remoteok_jobs(keywords: str, max_items: int = 10) -> list[Job]:
    run_input = {
        "keywordFilter": keywords,
        "maxResults": max_items,
    }
    raw_items = run_actor(REMOTEOK_ACTOR_ID, run_input)
    return [_to_job(item) for item in raw_items]


def _to_job(item: dict) -> Job:
    salary = None
    if item.get("salary_min") or item.get("salary_max"):
        parts = [str(item.get("salary_min") or ""), str(item.get("salary_max") or "")]
        salary = "-".join(p for p in parts if p)
        if item.get("currency"):
            salary = f"{item['currency']} {salary}"

    return Job(
        id=f"remoteok:{item.get('id', '')}",
        source="remoteok",
        title=item.get("title") or "",
        company=item.get("company_name"),
        location=item.get("location") or "Remote",
        description=item.get("description") or "",
        url=item.get("apply_url") or item.get("source_url") or "",
        remote=True,
        employment_type=item.get("type"),
        salary=salary,
        posted_date=item.get("posted_at"),
    )
