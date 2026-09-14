from datetime import datetime, timedelta, timezone

from src.scraping.apify_client import run_actor
from src.scraping.country_utils import resolve_location
from src.preprocessing.schema import Job

GLASSDOOR_ACTOR_ID = "5OaooRg0FxlRF0L1B"


def scrape_glassdoor_jobs(keywords: str, location: str, max_items: int = 10, days_old: int = 7) -> list[Job]:
    _, resolved_location, _ = resolve_location(location)
    run_input = {
        "keywords": keywords,
        "location": resolved_location or "Turkey",
        "limit": max_items,
        "daysOld": days_old,
    }
    raw_items = run_actor(GLASSDOOR_ACTOR_ID, run_input)
    return [_to_job(item) for item in raw_items]


def _to_job(item: dict) -> Job:
    employer = item.get("employer") or {}
    location = item.get("location") or {}
    pay = item.get("pay") or {}

    salary = None
    if pay.get("min") or pay.get("max"):
        parts = [str(pay.get("min") or ""), str(pay.get("max") or "")]
        salary = "-".join(p for p in parts if p)
        if pay.get("period"):
            salary += f" / {pay['period']}"
        if pay.get("currency"):
            salary = f"{pay['currency']} {salary}"

    posted_date = None
    age_in_days = item.get("ageInDays")
    if age_in_days is not None:
        posted_date = (datetime.now(timezone.utc) - timedelta(days=age_in_days)).isoformat()

    return Job(
        id=f"glassdoor:{item.get('id', '')}",
        source="glassdoor",
        title=item.get("title") or "",
        company=employer.get("name"),
        location=location.get("name"),
        description=item.get("description") or "",
        url=item.get("url") or "",
        salary=salary,
        posted_date=posted_date,
    )
