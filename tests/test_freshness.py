from datetime import datetime, timedelta, timezone

from src.preprocessing.schema import Job
from src.model.freshness import is_job_stale


def _job(**overrides):
    defaults = dict(id="1", source="test", title="Job", url="https://a.com/1")
    defaults.update(overrides)
    return Job(**defaults)


def test_job_older_than_max_age_is_stale():
    old_date = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
    assert is_job_stale(_job(posted_date=old_date)) is True


def test_recent_job_is_not_stale():
    recent_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    assert is_job_stale(_job(posted_date=recent_date)) is False


def test_job_marked_expired_is_always_stale():
    recent_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    assert is_job_stale(_job(posted_date=recent_date, is_expired=True)) is True


def test_job_without_posted_date_is_not_stale():
    assert is_job_stale(_job(posted_date=None)) is False
