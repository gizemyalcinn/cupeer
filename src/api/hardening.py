"""Güvenlik katmanı: hız sınırı, istek doğrulama, güvenlik başlıkları, denetim kaydı."""
import hashlib
import io
import logging
import os
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

import pdfplumber
from fastapi import HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

# Render her serviste RENDER=true tanımlar; yerelde tanımsızdır.
IS_PROD = bool(os.getenv("RENDER"))

MAX_BODY_BYTES = 6 * 1024 * 1024
MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 12
MAX_CV_CHARS = 30_000

audit = logging.getLogger("cupeer.audit")


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def redact(value: str) -> str:
    """Kişisel veriyi (e-posta) loglara düz yazmamak için kısa bir özetini al."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]


def log_event(event: str, request: Request | None = None, **fields) -> None:
    parts = [f"event={event}"]
    if request is not None:
        parts.append(f"ip={client_ip(request)}")
    parts.extend(f"{key}={value}" for key, value in fields.items())
    audit.info(" ".join(parts))


# --- Hız sınırı (tek worker için bellek içi kayan pencere) ---

_MAX_WINDOW = 3600  # kullandığımız en uzun pencere; temizlik bunu baz alır


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window: int) -> int:
        """İzin veriliyorsa 0, aşıldıysa tekrar denemeye kalan saniyeyi döndürür."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= window:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, int(window - (now - hits[0])) + 1)
            hits.append(now)
            if len(self._hits) > 10_000:
                self._sweep(now)
            return 0

    def _sweep(self, now: float) -> None:
        stale = [k for k, h in self._hits.items() if not h or now - h[-1] >= _MAX_WINDOW]
        for key in stale:
            del self._hits[key]


limiter = SlidingWindowLimiter()


def enforce_limit(request: Request, key: str, limit: int, window: int, bucket: str) -> None:
    retry_after = limiter.hit(key, limit, window)
    if retry_after:
        log_event("ratelimit.exceeded", request, bucket=bucket)
        raise HTTPException(
            429,
            "Çok fazla istek gönderdin, biraz bekleyip tekrar dene.",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit(bucket: str, limit: int, window: int):
    """Route dependency: istemci IP'si başına `window` saniyede en fazla `limit` istek."""

    def dependency(request: Request) -> None:
        enforce_limit(request, f"{bucket}:{client_ip(request)}", limit, window, bucket)

    return dependency


# --- Başlıklar ve istek kontrolleri ---

CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def is_https(request: Request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


def origin_allowed(request: Request) -> bool:
    """CSRF'e ikinci savunma hattı: durum değiştiren isteklerin Origin'i bizim host olmalı."""
    if request.method in SAFE_METHODS:
        return True
    origin = request.headers.get("origin")
    if origin is None:
        return request.headers.get("sec-fetch-site") in (None, "same-origin", "none")
    return urlparse(origin).netloc == request.headers.get("host", "")


# --- PDF yükleme doğrulaması ---

def _extract_pdf_text(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        if len(pdf.pages) > MAX_PDF_PAGES:
            raise HTTPException(400, f"PDF en fazla {MAX_PDF_PAGES} sayfa olabilir.")
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text[:MAX_CV_CHARS]


async def read_pdf_text(file: UploadFile, request: Request) -> str:
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        log_event("upload.rejected", request, reason="too_large")
        raise HTTPException(413, "Dosya çok büyük (en fazla 5 MB).")
    if not data.startswith(b"%PDF-"):
        log_event("upload.rejected", request, reason="not_pdf")
        raise HTTPException(415, "Yalnızca PDF dosyaları kabul edilir.")
    try:
        text = await run_in_threadpool(_extract_pdf_text, data)
    except HTTPException:
        log_event("upload.rejected", request, reason="too_many_pages")
        raise
    except Exception:
        log_event("upload.rejected", request, reason="unreadable")
        raise HTTPException(400, "PDF okunamadı, dosyayı kontrol et.")
    if not text.strip():
        raise HTTPException(400, "PDF okunamadı, dosyayı kontrol et.")
    return text
