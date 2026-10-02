import pytest
from fastapi.testclient import TestClient

from src.api import hardening
from src.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_limiter():
    hardening.limiter._hits.clear()


def test_security_headers_present():
    response = client.get("/")
    assert response.status_code == 200
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "referrer-policy" in response.headers


def test_hsts_only_over_https():
    assert "strict-transport-security" not in client.get("/").headers
    secure = client.get("/", headers={"X-Forwarded-Proto": "https"})
    assert "max-age" in secure.headers["strict-transport-security"]


def test_unknown_path_serves_custom_404_with_404_status():
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert "Sayfa bulunamadı" in response.text


def test_api_docs_are_not_exposed():
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_cross_origin_post_is_rejected():
    blocked = client.post("/auth/logout", headers={"Origin": "https://evil.example"})
    assert blocked.status_code == 403
    allowed = client.post("/auth/logout", headers={"Origin": "http://testserver"})
    assert allowed.status_code == 200


def test_upload_must_be_a_pdf():
    response = client.post("/extract-text", files={"file": ("cv.pdf", b"not a pdf", "application/pdf")})
    assert response.status_code == 415


def test_upload_size_limit():
    too_big = b"%PDF-" + b"0" * (hardening.MAX_PDF_BYTES + 1)
    response = client.post("/extract-text", files={"file": ("cv.pdf", too_big, "application/pdf")})
    assert response.status_code == 413


def test_oversized_request_body_is_rejected_early():
    huge = b"0" * (hardening.MAX_BODY_BYTES + 1)
    response = client.post("/extract-text", files={"file": ("cv.pdf", huge, "application/pdf")})
    assert response.status_code == 413


def test_request_validation_bounds():
    response = client.post("/recommend", json={"profile_text": "python", "top_n": 5000})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_refresh_requires_login():
    response = client.post("/refresh", json={"keywords": "python"})
    assert response.status_code == 401


def test_refresh_cannot_request_unbounded_items():
    response = client.post("/refresh", json={"keywords": "python", "max_items_per_source": 100000})
    assert response.status_code == 422


def test_password_longer_than_bcrypt_limit_is_rejected():
    response = client.post(
        "/auth/register",
        json={"email": "someone@example.com", "password": "a" * 100},
    )
    assert response.status_code == 400


def test_sliding_window_limiter(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(hardening.time, "monotonic", lambda: now[0])
    limiter = hardening.SlidingWindowLimiter()

    assert limiter.hit("k", limit=2, window=60) == 0
    assert limiter.hit("k", limit=2, window=60) == 0
    assert limiter.hit("k", limit=2, window=60) > 0
    assert limiter.hit("other", limit=2, window=60) == 0

    now[0] += 61
    assert limiter.hit("k", limit=2, window=60) == 0


def test_rate_limit_returns_429_with_retry_after():
    for _ in range(8):
        client.post("/cv-review", files={"file": ("cv.pdf", b"nope", "application/pdf")})
    response = client.post("/cv-review", files={"file": ("cv.pdf", b"nope", "application/pdf")})
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


def test_delete_account_requires_login():
    response = client.post("/auth/delete-account", json={"confirm_email": "a@b.co"})
    assert response.status_code == 401
