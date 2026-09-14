from src.preprocessing.schema import Job
from src.preprocessing.clean import clean_job, dedupe


def test_clean_job_strips_html_and_whitespace():
    job = Job(
        id="1",
        source="test",
        title="  Data   Scientist  ",
        description="<p>Great <b>role</b></p>",
        url="https://a.com/1",
    )
    cleaned = clean_job(job)
    assert cleaned.title == "Data Scientist"
    assert cleaned.description == "Great role"


def test_dedupe_removes_jobs_with_same_url():
    jobs = [
        Job(id="1", source="test", title="Data Scientist", url="https://a.com/1"),
        Job(id="2", source="test", title="Data Analyst", url="https://a.com/1"),
        Job(id="3", source="test", title="ML Engineer", url="https://a.com/3"),
    ]
    result = dedupe(jobs)
    assert len(result) == 2
    assert {j.id for j in result} == {"1", "3"}
