from src.scraping.collect_all import collect_all_jobs
from src.model.embeddings import embed_texts
from src.db.storage import save_new_jobs


def refresh_jobs(keywords: str, location: str = "Turkey", max_items_per_source: int = 10) -> int:
    jobs = collect_all_jobs(keywords, location, max_items_per_source)
    if not jobs:
        return 0

    titles = [job.title for job in jobs]
    contents = [
        "\n".join(p for p in [job.company or "", job.location or "", job.description] if p)
        for job in jobs
    ]

    title_vectors = embed_texts(titles)
    content_vectors = embed_texts(contents)
    inserted = save_new_jobs(jobs, title_vectors, content_vectors)
    return inserted