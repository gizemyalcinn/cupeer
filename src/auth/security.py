import os

import bcrypt
from fastapi import Request

from src.preprocessing.schema import User
from src.db.storage import get_user_by_id


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
