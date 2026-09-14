from src.scraping.apify_client import run_actor
from src.preprocessing.schema import Job

KARIYER_ACTOR_ID = "VVtQkmj8ktjqzRQDh"


def scrape_kariyer_jobs(keywords: str, location: str = "", max_items: int = 10, max_age_days: int = 7) -> list[Job]:
    run_input = {
        "query": keywords,
        "location": location,
        "maxResults": max_items,
        "includeDetails": True,
        "maxAgeDays": max_age_days,
    }
    raw_items = run_actor(KARIYER_ACTOR_ID, run_input)
    return [_to_job(item) for item in raw_items]


def _to_job(item: dict) -> Job:
    is_active = item.get("isActive")
    is_expired = (is_active is False) if is_active is not None else None
    return Job(
        id=f"kariyer:{item.get('jobId', '')}",
        source="kariyer",
        title=item.get("title") or "",
        company=item.get("company"),
        location=item.get("location") or item.get("city"),
        description=item.get("descriptionText") or "",
        url=item.get("sourceUrl", ""),
        remote=item.get("isRemoteWork"),
        employment_type=item.get("employmentType"),
        posted_date=item.get("postedAt"),
        is_expired=is_expired,
    )