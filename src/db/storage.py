import sqlite3
import json
import numpy as np
from pathlib import Path
from src.preprocessing.schema import Job

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "jobs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    country TEXT,
    description TEXT,
    url TEXT,
    remote INTEGER,
    employment_type TEXT,
    salary TEXT,
    posted_date TEXT,
    scraped_at TEXT,
    is_expired INTEGER,
    title_embedding BLOB,
    content_embedding BLOB
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def get_existing_ids() -> set[str]:
    conn = _connect()
    rows = conn.execute("SELECT id FROM jobs").fetchall()
    conn.close()
    return {row[0] for row in rows}


def save_new_jobs(jobs: list[Job], title_vectors: np.ndarray, content_vectors: np.ndarray) -> int:
    existing_ids = get_existing_ids()
    conn = _connect()
    inserted = 0
    for job, title_vec, content_vec in zip(jobs, title_vectors, content_vectors):
        if job.id in existing_ids:
            continue
        conn.execute(
            "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                job.id, job.source, job.title, job.company, job.location, job.country,
                job.description, job.url,
                int(job.remote) if job.remote is not None else None,
                job.employment_type, job.salary, job.posted_date, job.scraped_at,
                int(job.is_expired) if job.is_expired is not None else None,
                title_vec.astype(np.float32).tobytes(),
                content_vec.astype(np.float32).tobytes(),
            ),
        )
        inserted += 1
    conn.commit()
    conn.close()
    return inserted


def load_all_jobs() -> tuple[list[Job], np.ndarray, np.ndarray]:
    conn = _connect()
    rows = conn.execute(
        "SELECT id, source, title, company, location, country, description, url, "
        "remote, employment_type, salary, posted_date, scraped_at, is_expired, "
        "title_embedding, content_embedding FROM jobs"
    ).fetchall()
    conn.close()

    jobs = []
    title_vectors = []
    content_vectors = []
    for row in rows:
        jobs.append(Job(
            id=row[0], source=row[1], title=row[2], company=row[3], location=row[4],
            country=row[5],
            description=row[6], url=row[7],
            remote=bool(row[8]) if row[8] is not None else None,
            employment_type=row[9], salary=row[10], posted_date=row[11], scraped_at=row[12],
            is_expired=bool(row[13]) if row[13] is not None else None,
        ))
        title_vectors.append(np.frombuffer(row[14], dtype=np.float32))
        content_vectors.append(np.frombuffer(row[15], dtype=np.float32))

    title_embeddings = np.stack(title_vectors) if title_vectors else np.empty((0, 0), dtype=np.float32)
    content_embeddings = np.stack(content_vectors) if content_vectors else np.empty((0, 0), dtype=np.float32)
    return jobs, title_embeddings, content_embeddings
