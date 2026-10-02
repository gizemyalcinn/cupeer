import os

import bcrypt
from fastapi import Request

from src.preprocessing.schema import User
from src.db.storage import get_user_by_id


# En sık kullanılan (ve Türkiye'de sık görülen) şifreler; kaba kuvvet listelerinin ilk satırları.
_COMMON_PASSWORDS = {
    "12345678", "123456789", "1234567890", "12345678910", "123123123", "11111111", "00000000",
    "87654321", "987654321", "password", "password1", "password123", "passw0rd", "qwerty123",
    "qwertyui", "qwertyuiop", "asdfghjk", "asdfghjkl", "zxcvbnm1", "1q2w3e4r", "1q2w3e4r5t",
    "q1w2e3r4", "abc12345", "abcd1234", "iloveyou", "welcome1", "admin123", "letmein1",
    "sifre123", "sifre1234", "parola123", "parola1234", "sifresifre", "benimsifrem", "merhaba123",
    "galatasaray", "fenerbahce", "besiktas1", "trabzonspor", "turkiye1", "istanbul34", "ankara06",
    "cupeer123", "cupeer1234",
}


def weak_password_reason(password: str, email: str = "") -> str | None:
    """Zayıf şifreyi tanıyıp kullanıcıya gösterilecek nedeni döndürür; sorun yoksa None."""
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        return "Bu şifre çok yaygın, tahmin edilmesi kolay. Başka bir şifre seç."
    if len(set(lowered)) <= 2:
        return "Şifre çok basit; farklı karakterler kullan."
    local = email.split("@")[0].lower()
    if len(local) >= 4 and local in lowered:
        return "Şifre e-posta adresini içermemeli."
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def login_user(request: Request, user: User) -> None:
    # Eski oturum verisini (ör. OAuth state) taşımamak için sıfırdan başlat.
    request.session.clear()
    request.session["user_id"] = user.id


def logout_user(request: Request) -> None:
    request.session.clear()


def can_refresh(request: Request, user: User | None) -> bool:
    """Ücretli Apify taraması yalnızca REFRESH_ALLOWED_EMAILS listesindeki hesaba açık.

    Şifreyle kayıtta e-posta doğrulanmadığı için, başkası sahibin adresiyle önceden hesap
    açmış olabilir; bu yüzden oturumun Google ile (doğrulanmış e-postayla) açılmış olması da
    şart. Liste boşsa kimseye izin verilmez.
    """
    if not user or not user.email or not request.session.get("via_google"):
        return False
    allowed = {e.strip().lower() for e in os.getenv("REFRESH_ALLOWED_EMAILS", "").split(",") if e.strip()}
    return user.email.lower() in allowed


def get_current_user(request: Request) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)
