from src.scraping.apify_client import run_actor
from src.preprocessing.schema import Job

UPWORK_ACTOR_ID = "XYTgO05GT5qAoSlxy"


def scrape_upwork_jobs(keywords: str, max_items: int = 10) -> list[Job]:
    run_input = {
        "query": keywords,
        "pagesToScrape": 1,
        "perPage": max(max_items, 10),
    }
    raw_items = run_actor(UPWORK_ACTOR_ID, run_input)
    return [_to_job(item) for item in raw_items]


def _to_job(item: dict) -> Job:
    return Job(
        id=f"upwork:{item.get('id', '')}",
        source="upwork",
        title=item.get("title") or "",
        company=item.get("clientName"),
        location=item.get("clientLocation"),
        description=item.get("description") or "",
        url=item.get("url") or "",
        remote=True,
        salary=item.get("budget"),
        posted_date=item.get("absoluteDate"),
    )