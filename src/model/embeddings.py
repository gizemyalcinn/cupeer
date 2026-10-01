import os

from google import genai
from google.genai import types

from src.preprocessing.schema import Job
import numpy as np

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> np.ndarray:
    client = _get_client()
    # Gemini boş content'e izin vermiyor; boş/whitespace-only metinleri
    # nötr bir placeholder ile değiştiriyoruz.
    safe_texts = [t if t and t.strip() else " " for t in texts]
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=safe_texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIM,
        ),
    )
    vectors = np.asarray([e.values for e in response.embeddings], dtype=np.float32)
    # output_dimensionality 3072'den küçük istendiğinde Gemini vektörleri
    # normalize etmeden döndürüyor; cosine similarity dot-product ile
    # hesaplandığı için burada L2 normalize şart.
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def job_to_text(job: Job) -> str:
    parts = [job.title, job.company or "", job.location or "", job.description]
    return "\n".join(p for p in parts if p)
