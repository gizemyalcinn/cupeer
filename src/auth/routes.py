import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from authlib.integrations.starlette_client import OAuth, OAuthError

from src.preprocessing.schema import User
from src.api.hardening import log_event, rate_limit, redact
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
    delete_user,
)

router = APIRouter(prefix="/auth")

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_WINDOW_MINUTES = 15
# bcrypt yalnızca ilk 72 baytı dikkate alır (ve daha uzununu reddeder).
MAX_PASSWORD_BYTES = 72

# Var olmayan e-postayla girişte de bcrypt çalıştırıp yanıt süresini eşitler;
# böylece süre farkından hesabın var olup olmadığı anlaşılamaz.
_DUMMY_HASH = hash_password("cupeer-timing-equalizer")

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    client_kwargs={"scope": "openid email profile"},
)


class RegisterRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)
    name: str | None = Field(None, max_length=100)


class LoginRequest(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


class DeleteAccountRequest(BaseModel):
    confirm_email: str = Field(max_length=254)


def _user_public(user: User) -> dict:
    return {"logged_in": True, "id": user.id, "email": user.email, "name": user.name}


@router.post("/register", dependencies=[Depends(rate_limit("register", 10, 3600))])
def register(req: RegisterRequest, request: Request):
    email = req.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Geçerli bir e-posta adresi gir.")
    if len(req.password) < 8:
        raise HTTPException(400, "Şifre en az 8 karakter olmalı.")
    if len(req.password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(400, "Şifre en fazla 72 karakter olabilir.")
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
    log_event("auth.register", request, user=user.id)
    return _user_public(user)


@router.post("/login", dependencies=[Depends(rate_limit("login", 30, 600))])
def login(req: LoginRequest, request: Request):
    email = req.email.strip().lower()

    if count_recent_failed_logins(email, LOGIN_LOCKOUT_WINDOW_MINUTES) >= MAX_LOGIN_ATTEMPTS:
        log_event("auth.login.locked", request, email=redact(email))
        raise HTTPException(
            429,
            f"Çok fazla başarısız deneme. Lütfen {LOGIN_LOCKOUT_WINDOW_MINUTES} dakika sonra tekrar dene.",
        )

    user = get_user_by_email(email)
    stored_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH
    password_ok = verify_password(req.password, stored_hash)
    if not (user and user.password_hash and password_ok):
        record_failed_login(email)
        log_event("auth.login.failure", request, email=redact(email))
        raise HTTPException(401, "E-posta veya şifre hatalı.")

    clear_failed_logins(email)
    login_user(request, user)
    log_event("auth.login.success", request, user=user.id)
    return _user_public(user)


@router.post("/logout")
def logout(request: Request):
    user_id = request.session.get("user_id")
    logout_user(request)
    log_event("auth.logout", request, user=user_id)
    return {"ok": True}


@router.post("/delete-account", dependencies=[Depends(rate_limit("delete-account", 5, 3600))])
def delete_account(
    req: DeleteAccountRequest,
    request: Request,
    user: User | None = Depends(get_current_user),
):
    if not user:
        raise HTTPException(401, "Bu işlem için giriş yapmalısın.")
    if not user.email or user.email.lower() != req.confirm_email.strip().lower():
        raise HTTPException(400, "Yazdığın e-posta hesabınla eşleşmiyor.")
    delete_user(user.id)
    logout_user(request)
    log_event("auth.account_deleted", request, user=user.id)
    return {"ok": True}


@router.get("/me")
def me(user: User | None = Depends(get_current_user)):
    if not user:
        return {"logged_in": False}
    return _user_public(user)


@router.get("/google/login", dependencies=[Depends(rate_limit("google-login", 20, 600))])
async def google_login(request: Request):
    if not os.getenv("GOOGLE_CLIENT_ID"):
        raise HTTPException(503, "Google ile giriş henüz yapılandırılmadı.")
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri, prompt="select_account")


@router.get("/google/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        log_event("auth.google.failure", request, reason="oauth_error")
        return RedirectResponse(url="/?login=failed")

    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.google.userinfo(token=token)

    # Doğrulanmamış bir e-postayla mevcut hesaba bağlanmak hesap ele geçirmeye yol açar.
    if not userinfo.get("email_verified"):
        log_event("auth.google.failure", request, reason="email_unverified")
        return RedirectResponse(url="/?login=failed")

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
    log_event("auth.google.success", request, user=user.id)
    return RedirectResponse(url="/")
