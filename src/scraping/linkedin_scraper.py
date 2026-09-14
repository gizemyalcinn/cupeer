from src.scraping.apify_client import run_actor
from src.scraping.country_utils import resolve_location
from src.preprocessing.schema import Job

LINKEDIN_ACTOR_ID = "hKByXkMQaC5Qt9UMN"


def scrape_linkedin_jobs(keywords: str, location: str, max_items: int = 5, date_posted: str = "pastWeek") -> list[Job]:
    _, resolved_location, _ = resolve_location(location)
    run_input = {
        "keywords": keywords,
        "location": resolved_location,
        "limitPerSource": max_items,
        "datePosted": date_posted,
    }
    raw_items = run_actor(LINKEDIN_ACTOR_ID, run_input)
    return [_to_job(item) for item in raw_items]


def _to_job(item: dict) -> Job:
    return Job(
        id=f"linkedin:{item.get('id', item.get('link', ''))}",
        source="linkedin",
        title=item.get("title") or "",
        company=item.get("companyName"),
        location=item.get("location"),
        description=item.get("descriptionText") or "",
        url=item.get("link") or "",
        salary=item.get("salary"),
        posted_date=item.get("postedAt"),
    )