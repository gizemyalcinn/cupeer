"""Mevcut yerel jobs.db (SQLite) içindeki jobs tablosunu yeni Postgres veritabanına taşır.

Tek seferlik kullanım içindir: users/favorites/login_attempts tabloları boş
başlar (Postgres'e geçişle birlikte temiz bir hesap/favori durumu kabul edildi),
sadece scrape edilmiş + embed edilmiş iş ilanları taşınır.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.db.storage import _connect

OLD_SQLITE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "jobs.db"


def main():
    sqlite_conn = sqlite3.connect(OLD_SQLITE_PATH)
    rows = sqlite_conn.execute(
        "SELECT id, source, title, company, location, country, description, url, "
        "remote, employment_type, salary, posted_date, scraped_at, is_expired, "
        "title_embedding, content_embedding FROM jobs"
    ).fetchall()
    sqlite_conn.close()

    print(f"{len(rows)} ilan SQLite'tan okundu.")
    if not rows:
        return

    pg_conn = _connect()
    with pg_conn.cursor() as cur:
        for row in rows:
            cur.execute(
                "INSERT INTO jobs (id, source, title, company, location, country, description, url, "
                "remote, employment_type, salary, posted_date, scraped_at, is_expired, "
                "title_embedding, content_embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (id) DO NOTHING",
                row,
            )
    pg_conn.commit()
    pg_conn.close()
    print("Postgres'e aktarıldı.")


if __name__ == "__main__":
    main()
