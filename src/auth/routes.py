import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from authlib.integrations.starlette_client import OAuth

from src.preprocessing.schema import User
from src.auth.security import (
    hash_password,
    verify_password,
    login_user,
    logout_user,
    get_current_user,
)
from src.db.storage import (
    create_user,
    get_user_by_email,
    get_user_by_google_id,
    get_user_by_id,
    link_google_id,
    record_failed_login,
    count_recent_failed_logins,
    clear_failed_logins,
)

router = APIRouter(prefix="/auth")

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_WINDOW_MINUTES = 15

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    client_kwargs={"scope": "openid email profile"},
)


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


def _user_public(user: User) -> dict:
    return {"logged_in": True, "id": user.id, "email": user.email, "name": user.name}


@router.post("/register")
def register(req: RegisterRequest, request: Request):
    email = req.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Geçerli bir e-posta adresi gir.")
    if len(req.password) < 8:
        raise HTTPException(400, "Şifre en az 8 karakter olmalı.")
    if get_user_by_email(email):
        raise HTTPException(400, "Bu e-posta ile zaten bir hesap var.")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        name=(req.name or "").strip() or None,
        password_hash=hash_password(req.password),
    )
    create_user(user)
    login_user(request, user)
    return _user_public(user)


@router.post("/login")
def login(req: LoginRequest, request: Request):
    email = req.email.strip().lower()

    if count_recent_failed_logins(email, LOGIN_LOCKOUT_WINDOW_MINUTES) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            429,
            f"Çok fazla başarısız deneme. Lütfen {LOGIN_LOCKOUT_WINDOW_MINUTES} dakika sonra tekrar dene.",
        )

    user = get_user_by_email(email)
    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        record_failed_login(email)
        raise HTTPException(401, "E-posta veya şifre hatalı.")

    clear_failed_logins(email)
    login_user(request, user)
    return _user_public(user)


@router.post("/logout")
def logout(request: Request):
    logout_user(request)
    return {"ok": True}


@router.get("/me")
def me(user: User | None = Depends(get_current_user)):
    if not user:
        return {"logged_in": False}
    return _user_public(user)


@router.get("/google/login")
async def google_login(request: Request):
    if not os.getenv("GOOGLE_CLIENT_ID"):
        raise HTTPException(503, "Google ile giriş henüz yapılandırılmadı.")
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri, prompt="select_account")


@router.get("/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.google.userinfo(token=token)

    google_id = userinfo["sub"]
    email = (userinfo.get("email") or "").lower() or None
    name = userinfo.get("name")

    user = get_user_by_google_id(google_id)
    if not user and email:
        existing = get_user_by_email(email)
        if existing:
            link_google_id(existing.id, google_id)
            user = get_user_by_id(existing.id)
    if not user:
        user = User(id=str(uuid.uuid4()), email=email, name=name, google_id=google_id)
        create_user(user)

    login_user(request, user)
    return RedirectResponse(url="/")
