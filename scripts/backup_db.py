"""Veritabanını sıkıştırılmış bir JSON dosyasına yedekler ya da yedekten geri yükler.

Kullanım (proje kökünden, DATABASE_URL .env'de tanımlı olmalı):

    python scripts/backup_db.py backup                      # backups/ klasörüne yazar
    python scripts/backup_db.py restore backups/<dosya>.json.gz

Yedek, şifre özetleri dahil kullanıcı verisi içerir; `backups/` .gitignore'dadır,
dosyayı paylaşma. Geri yükleme mevcut kayıtların üstüne yazmaz (ON CONFLICT DO NOTHING).
"""
import argparse
import base64
import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.db.storage import _connect

BACKUP_DIR = Path(__file__).resolve().parent.parent / "backups"

# tablo -> (kolonlar, çakışma anahtarı, base64'e çevrilecek BYTEA kolonları)
TABLES = {
    "users": (["id", "email", "password_hash", "google_id", "name", "created_at"], "id", []),
    "favorites": (["user_id", "job_id", "created_at"], "user_id, job_id", []),
    "jobs": (
        [
            "id", "source", "title", "company", "location", "country", "description", "url",
            "remote", "employment_type", "salary", "posted_date", "scraped_at", "is_expired",
            "is_favorite", "title_embedding", "content_embedding",
        ],
        "id",
        ["title_embedding", "content_embedding"],
    ),
}


def backup() -> Path:
    conn = _connect()
    data = {"created_at": datetime.now(timezone.utc).isoformat(), "tables": {}}
    with conn.cursor() as cur:
        for table, (columns, _, binary) in TABLES.items():
            cur.execute(f"SELECT {', '.join(columns)} FROM {table}")  # noqa: S608 (sabit tablo/kolon adları)
            rows = []
            for row in cur.fetchall():
                record = dict(zip(columns, row))
                for col in binary:
                    if record[col] is not None:
                        record[col] = base64.b64encode(bytes(record[col])).decode("ascii")
                rows.append(record)
            data["tables"][table] = rows
    conn.close()

    BACKUP_DIR.mkdir(exist_ok=True)
    out = BACKUP_DIR / f"cupeer-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json.gz"
    with gzip.open(out, "wt", encoding="utf-8") as f:
        json.dump(data, f)
    counts = ", ".join(f"{t}={len(r)}" for t, r in data["tables"].items())
    print(f"Yedek yazıldı: {out} ({counts})")
    return out


def restore(path: Path) -> None:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)

    conn = _connect()
    with conn.cursor() as cur:
        # jobs önce: favorites onlara bağlı
        for table in ("users", "jobs", "favorites"):
            columns, conflict, binary = TABLES[table]
            placeholders = ", ".join(["%s"] * len(columns))
            sql = (
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "  # noqa: S608
                f"ON CONFLICT ({conflict}) DO NOTHING"
            )
            for record in data["tables"].get(table, []):
                for col in binary:
                    if record[col] is not None:
                        record[col] = base64.b64decode(record[col])
                cur.execute(sql, [record[c] for c in columns])
            print(f"{table}: {len(data['tables'].get(table, []))} kayıt işlendi")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("backup")
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("file", type=Path)
    args = parser.parse_args()

    if args.command == "backup":
        backup()
    else:
        restore(args.file)
