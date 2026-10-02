import os

import numpy as np
import psycopg2
from datetime import datetime, timedelta, timezone
from src.preprocessing.schema import Job, User

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
    title_embedding BYTEA,
    content_embedding BYTEA
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
ALTER TABLE favorites ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'saved';

CREATE TABLE IF NOT EXISTS login_attempts (
    email TEXT NOT NULL,
    attempted_at TEXT NOT NULL
);
"""


def _connect():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    with conn.cursor() as cur:
        cur.execute(_SCHEMA)
    conn.commit()
    return conn


def get_existing_ids() -> set[str]:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM jobs")
        rows = cur.fetchall()
    conn.close()
    return {row[0] for row in rows}


def save_new_jobs(jobs: list[Job], title_vectors: np.ndarray, content_vectors: np.ndarray) -> int:
    existing_ids = get_existing_ids()
    conn = _connect()
    inserted = 0
    with conn.cursor() as cur:
        for job, title_vec, content_vec in zip(jobs, title_vectors, content_vectors):
            if job.id in existing_ids:
                continue
            cur.execute(
                "INSERT INTO jobs (id, source, title, company, location, country, description, url, "
                "remote, employment_type, salary, posted_date, scraped_at, is_expired, "
                "title_embedding, content_embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
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
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, source, title, company, location, country, description, url, "
            "remote, employment_type, salary, posted_date, scraped_at, is_expired, "
            "title_embedding, content_embedding FROM jobs"
        )
        rows = cur.fetchall()
    conn.close()

    jobs = []
    title_vectors = []
    content_vectors = []
    for row in rows:
        jobs.append(_row_to_job(row[:14]))
        title_vectors.append(np.frombuffer(bytes(row[14]), dtype=np.float32))
        content_vectors.append(np.frombuffer(bytes(row[15]), dtype=np.float32))

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
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (id, email, password_hash, google_id, name, created_at) VALUES (%s,%s,%s,%s,%s,%s)",
            (user.id, user.email, user.password_hash, user.google_id, user.name, user.created_at),
        )
    conn.commit()
    conn.close()
    return user


def get_user_by_email(email: str) -> User | None:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, google_id, name, created_at FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def get_user_by_google_id(google_id: str) -> User | None:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, google_id, name, created_at FROM users WHERE google_id = %s",
            (google_id,),
        )
        row = cur.fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def get_user_by_id(user_id: str) -> User | None:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, google_id, name, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        row = cur.fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def link_google_id(user_id: str, google_id: str) -> None:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET google_id = %s WHERE id = %s", (google_id, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id: str) -> None:
    """Kullanıcıyı ve ona bağlı tüm kayıtları (favoriler, giriş denemeleri) tek işlemde siler."""
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.execute("DELETE FROM favorites WHERE user_id = %s", (user_id,))
        if row and row[0]:
            cur.execute("DELETE FROM login_attempts WHERE email = %s", (row[0],))
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()


# --- Favoriler (kullanıcıya özel) ---

def add_favorite(user_id: str, job_id: str) -> None:
    conn = _connect()
    now = datetime.now(timezone.utc).isoformat()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO favorites (user_id, job_id, created_at) VALUES (%s,%s,%s) "
            "ON CONFLICT (user_id, job_id) DO NOTHING",
            (user_id, job_id, now),
        )
    conn.commit()
    conn.close()


def remove_favorite(user_id: str, job_id: str) -> None:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM favorites WHERE user_id = %s AND job_id = %s", (user_id, job_id))
    conn.commit()
    conn.close()


def set_favorite_status(user_id: str, job_id: str, status: str) -> bool:
    """Favorinin başvuru durumunu günceller; kullanıcının böyle bir favorisi yoksa False döner."""
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE favorites SET status = %s WHERE user_id = %s AND job_id = %s",
            (status, user_id, job_id),
        )
        updated = cur.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_favorite_ids(user_id: str) -> set[str]:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("SELECT job_id FROM favorites WHERE user_id = %s", (user_id,))
        rows = cur.fetchall()
    conn.close()
    return {row[0] for row in rows}


def get_favorite_jobs(user_id: str) -> list[Job]:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT j.id, j.source, j.title, j.company, j.location, j.country, j.description, j.url, "
            "j.remote, j.employment_type, j.salary, j.posted_date, j.scraped_at, j.is_expired, f.status "
            "FROM favorites f JOIN jobs j ON f.job_id = j.id "
            "WHERE f.user_id = %s ORDER BY f.created_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()
    conn.close()
    jobs = []
    for row in rows:
        job = _row_to_job(row[:14])
        job.is_favorite = True
        job.favorite_status = row[14]
        jobs.append(job)
    return jobs


# --- Giriş denemesi sınırlama (brute-force koruması) ---

def record_failed_login(email: str) -> None:
    conn = _connect()
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        # Gereksiz veri tutma: kilitleme penceresinden (15 dk) çok eski denemeler silinir.
        cur.execute(
            "DELETE FROM login_attempts WHERE attempted_at < %s",
            ((now - timedelta(days=1)).isoformat(),),
        )
        cur.execute(
            "INSERT INTO login_attempts (email, attempted_at) VALUES (%s, %s)",
            (email, now.isoformat()),
        )
    conn.commit()
    conn.close()


def count_recent_failed_logins(email: str, window_minutes: int) -> int:
    conn = _connect()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM login_attempts WHERE email = %s AND attempted_at > %s",
            (email, cutoff),
        )
        row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def clear_failed_logins(email: str) -> None:
    conn = _connect()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM login_attempts WHERE email = %s", (email,))
    conn.commit()
    conn.close()
