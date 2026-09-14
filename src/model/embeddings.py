from sentence_transformers import SentenceTransformer
from src.preprocessing.schema import Job
import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return np.asarray(embeddings, dtype=np.float32)



def job_to_text(job: Job) -> str:
    parts = [job.title, job.company or "", job.location or "", job.description]
    return "\n".join(p for p in parts if p)