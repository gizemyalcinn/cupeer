from src.scraping.apify_client import run_actor
from src.scraping.country_utils import resolve_location
from src.preprocessing.schema import Job

INDEED_ACTOR_ID = "MXLpngmVpE8WTESQr"


def scrape_indeed_jobs(keywords: str, location: str, max_items: int = 5, from_days: str = "7") -> list[Job]:
    country, resolved_location, is_country_level = resolve_location(location)
    run_input = {
        "query": keywords,
        "location": "" if is_country_level else resolved_location,
        "country": country,
        "maxRows": max_items,
        "fromDays": from_days,
    }
    raw_items = run_actor(INDEED_ACTOR_ID, run_input)
    return [_to_job(item) for item in raw_items]


def _to_job(item: dict) -> Job:
    job_id = item.get("jobKey") or item.get("jobUrl", "")

    location = item.get("location")
    if isinstance(location, dict):
        location = location.get("formattedAddressLong") or location.get("city")

    salary = item.get("salary")
    if isinstance(salary, dict):
        salary = salary.get("salaryText")

    job_type = item.get("jobType")
    employment_type = ", ".join(job_type) if isinstance(job_type, list) else job_type

    return Job(
        id=f"indeed:{job_id}",
        source="indeed",
        title=item.get("title") or "",
        company=item.get("companyName"),
        location=location,
        description=item.get("descriptionText") or item.get("descriptionHtml") or "",
        url=item.get("jobUrl") or item.get("applyUrl") or "",
        remote=item.get("isRemote"),
        employment_type=employment_type,
        salary=salary,
        posted_date=item.get("datePublished"),
        is_expired=item.get("expired"),
    )