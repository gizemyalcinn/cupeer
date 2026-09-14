from datetime import datetime, timezone
from src.preprocessing.schema import Job


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_job_stale(job: Job, max_age_days: int = 45) -> bool:
    if job.is_expired:
        return True
    posted = _parse_date(job.posted_date)
    if posted is None:
        return False
    age_days = (datetime.now(timezone.utc) - posted).days
    return age_days > max_age_days