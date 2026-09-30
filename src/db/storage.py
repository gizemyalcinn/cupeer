import sqlite3
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.preprocessing.schema import Job, User

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
    is_favorite INTEGER DEFAULT 0,
    title_embedding BLOB,
    content_embedding BLOB
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    password_hash TEXT,
    google_id TEXT UNIQUE,
    name TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS favorites (
    user_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    created_at TEXT,
    PRIMARY KEY (user_id, job_id)
);

CREATE TABLE IF NOT EXISTS login_attempts (
    email TEXT NOT NULL,
    attempted_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    # jobs.db created before is_favorite existed won't have the column yet.
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    if "is_favorite" not in existing_columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN is_favorite INTEGER DEFAULT 0")
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
            "INSERT INTO jobs (id, source, title, company, location, country, description, url, "
            "remote, employment_type, salary, posted_date, scraped_at, is_expired, "
            "title_embedding, content_embedding) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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


def _row_to_job(row) -> Job:
    return Job(
        id=row[0], source=row[1], title=row[2], company=row[3], location=row[4],
        country=row[5],
        description=row[6], url=row[7],
        remote=bool(row[8]) if row[8] is not None else None,
        employment_type=row[9], salary=row[10], posted_date=row[11], scraped_at=row[12],
        is_expired=bool(row[13]) if row[13] is not None else None,
    )


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
        jobs.append(_row_to_job(row[:14]))
        title_vectors.append(np.frombuffer(row[14], dtype=np.float32))
        content_vectors.append(np.frombuffer(row[15], dtype=np.float32))

    title_embeddings = np.stack(title_vectors) if title_vectors else np.empty((0, 0), dtype=np.float32)
    content_embeddings = np.stack(content_vectors) if content_vectors else np.empty((0, 0), dtype=np.float32)
    return jobs, title_embeddings, content_embeddings


# --- Kullanıcılar ---

def _row_to_user(row) -> User:
    return User(
        id=row[0], email=row[1], password_hash=row[2], google_id=row[3],
        name=row[4], created_at=row[5],
    )


def create_user(user: User) -> User:
    conn = _connect()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, google_id, name, created_at) VALUES (?,?,?,?,?,?)",
        (user.id, user.email, user.password_hash, user.google_id, user.name, user.created_at),
    )
    conn.commit()
    conn.close()
    return user


def get_user_by_email(email: str) -> User | None:
    conn = _connect()
    row = conn.execute(
        "SELECT id, email, password_hash, google_id, name, created_at FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def get_user_by_google_id(google_id: str) -> User | None:
    conn = _connect()
    row = conn.execute(
        "SELECT id, email, password_hash, google_id, name, created_at FROM users WHERE google_id = ?",
        (google_id,),
    ).fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def get_user_by_id(user_id: str) -> User | None:
    conn = _connect()
    row = conn.execute(
        "SELECT id, email, password_hash, google_id, name, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def link_google_id(user_id: str, google_id: str) -> None:
    conn = _connect()
    conn.execute("UPDATE users SET google_id = ? WHERE id = ?", (google_id, user_id))
    conn.commit()
    conn.close()


# --- Favoriler (kullanıcıya özel) ---

def add_favorite(user_id: str, job_id: str) -> None:
    conn = _connect()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO favorites (user_id, job_id, created_at) VALUES (?,?,?)",
        (user_id, job_id, now),
    )
    conn.commit()
    conn.close()


def remove_favorite(user_id: str, job_id: str) -> None:
    conn = _connect()
    conn.execute("DELETE FROM favorites WHERE user_id = ? AND job_id = ?", (user_id, job_id))
    conn.commit()
    conn.close()


def get_favorite_ids(user_id: str) -> set[str]:
    conn = _connect()
    rows = conn.execute("SELECT job_id FROM favorites WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return {row[0] for row in rows}


def get_favorite_jobs(user_id: str) -> list[Job]:
    conn = _connect()
    rows = conn.execute(
        "SELECT j.id, j.source, j.title, j.company, j.location, j.country, j.description, j.url, "
        "j.remote, j.employment_type, j.salary, j.posted_date, j.scraped_at, j.is_expired "
        "FROM favorites f JOIN jobs j ON f.job_id = j.id "
        "WHERE f.user_id = ? ORDER BY f.created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    jobs = [_row_to_job(row) for row in rows]
    for job in jobs:
        job.is_favorite = True
    return jobs


# --- Giriş denemesi sınırlama (brute-force koruması) ---

def record_failed_login(email: str) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO login_attempts (email, attempted_at) VALUES (?, ?)",
        (email, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def count_recent_failed_logins(email: str, window_minutes: int) -> int:
    conn = _connect()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE email = ? AND attempted_at > ?",
        (email, cutoff),
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def clear_failed_logins(email: str) -> None:
    conn = _connect()
    conn.execute("DELETE FROM login_attempts WHERE email = ?", (email,))
    conn.commit()
    conn.close()
