"""Mevcut jobs.db kayıtlarındaki embedding'leri yeni embedding modeliyle (Gemini) yeniden hesaplar."""
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

import httpx
from google.genai.errors import ClientError

import numpy as np

from src.model.embeddings import embed_texts
from src.db.storage import DB_PATH


def embed_with_retry(texts, task_type="RETRIEVAL_DOCUMENT", retries=6):
    for attempt in range(retries):
        try:
            return embed_texts(texts, task_type=task_type)
        except ClientError as e:
            if e.code == 429 and attempt < retries - 1:
                print(f"Rate limited, waiting 60s... (attempt {attempt + 1})")
                time.sleep(60)
            else:
                raise
        except httpx.TransportError as e:
            if attempt < retries - 1:
                print(f"Network error ({e}), retrying in 15s... (attempt {attempt + 1})")
                time.sleep(15)
            else:
                raise


def embed_in_batches(texts, task_type="RETRIEVAL_DOCUMENT", batch_size=33, pause=3):
    results = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        print(f"  batch {i // batch_size + 1}/{-(-len(texts) // batch_size)}...")
        results.append(embed_with_retry(chunk, task_type=task_type))
        if i + batch_size < len(texts):
            time.sleep(pause)
    return np.concatenate(results, axis=0)


def main():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, title, company, location, description FROM jobs"
    ).fetchall()
    if not rows:
        print("No jobs found.")
        return

    ids = [r[0] for r in rows]
    titles = [r[1] or "" for r in rows]
    contents = [
        "\n".join(p for p in [r[2] or "", r[3] or "", r[4] or ""] if p)
        for r in rows
    ]

    print(f"Re-embedding {len(ids)} jobs...")
    print("Titles:")
    title_vectors = embed_in_batches(titles)
    print("Contents:")
    content_vectors = embed_in_batches(contents)

    for job_id, title_vec, content_vec in zip(ids, title_vectors, content_vectors):
        conn.execute(
            "UPDATE jobs SET title_embedding = ?, content_embedding = ? WHERE id = ?",
            (
                title_vec.astype("float32").tobytes(),
                content_vec.astype("float32").tobytes(),
                job_id,
            ),
        )
    conn.commit()
    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
