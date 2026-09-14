import numpy as np
from src.db.storage import load_all_jobs
from src.model.embeddings import embed_texts
from src.model.freshness import is_job_stale
from src.scraping.country_utils import resolve_location

TITLE_WEIGHT = 0.6
CONTENT_WEIGHT = 0.4


def recommend_jobs(profile_text: str, top_n: int = 10, include_expired: bool = False, location: str = ""):
    jobs, title_embeddings, content_embeddings = load_all_jobs()
    if not jobs:
        return []

    if not include_expired:
        keep_mask = np.array([not is_job_stale(j) for j in jobs])
        jobs = [j for j, keep in zip(jobs, keep_mask) if keep]
        title_embeddings = title_embeddings[keep_mask]
        content_embeddings = content_embeddings[keep_mask]

    if not jobs:
        return []

    if location.strip():
        country_code, _, _ = resolve_location(location)
        # job.country, ilan çekilirken hangi ülke için arandığını kesin olarak
        # tutar (metin tahmini değil). Bilinmiyorsa (upwork/remoteok gibi
        # global platformlar) dışlamak yerine göstermeyi tercih ediyoruz.
        keep_mask = np.array([
            j.country is None or j.country == country_code for j in jobs
        ])
        jobs = [j for j, keep in zip(jobs, keep_mask) if keep]
        title_embeddings = title_embeddings[keep_mask]
        content_embeddings = content_embeddings[keep_mask]

    if not jobs:
        return []

    query_vector = embed_texts([profile_text])[0]
    title_scores = title_embeddings @ query_vector
    content_scores = content_embeddings @ query_vector
    scores = TITLE_WEIGHT * title_scores + CONTENT_WEIGHT * content_scores

    ranked_indices = np.argsort(-scores)[:top_n]
    return [(jobs[i], float(scores[i])) for i in ranked_indices]