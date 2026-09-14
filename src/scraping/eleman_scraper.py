from src.scraping.apify_client import run_actor
from src.preprocessing.schema import Job

ELEMAN_ACTOR_ID = "ykfUO6njHPhhp1hoG"


def scrape_eleman_jobs(keywords: str, max_items: int = 10) -> list[Job]:
    run_input = {
        "searchTerms": [keywords],
        "pagesToFetch": 1,
        "maxItems": max_items,
    }
    raw_items = run_actor(ELEMAN_ACTOR_ID, run_input)
    return [_to_job(item) for item in raw_items]


def _to_job(item: dict) -> Job:
    return Job(
        id=f"eleman:{item.get('jobId', '')}",
        source="eleman",
        title=item.get("title") or "",
        company=item.get("company"),
        location=item.get("location"),
        description=item.get("summary") or "",
        url=item.get("jobUrl") or "",
    )