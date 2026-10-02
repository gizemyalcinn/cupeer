from pydantic import BaseModel, Field
from datetime import datetime


class Job(BaseModel):
    id: str  # örn: "linkedin:abc123" - kaynak + benzersiz kimlik
    source: str  # "linkedin" | "indeed" | "upwork" | "kariyer" | "eleman"
    title: str
    company: str | None = None
    location: str | None = None
    country: str | None = None  # "tr", "us" gibi ülke kodu — çekilirken belirlenir; global platformlarda (upwork, remoteok) None
    description: str = ""
    url: str
    remote: bool | None = None
    is_expired: bool | None = None
    employment_type: str | None = None
    salary: str | None = None
    posted_date: str | None = None
    scraped_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    is_favorite: bool = False  # kalıcı değil, kullanıcıya göre her istekte hesaplanır
    favorite_status: str | None = None  # başvuru durumu; yalnızca favori listesinde dolu


class User(BaseModel):
    id: str
    email: str | None = None
    name: str | None = None
    password_hash: str | None = None  # Google ile kayıt olduysa None
    google_id: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())