"""Schema = bentuk data yang MASUK (input, divalidasi) dan KELUAR (output) pada API."""
from datetime import datetime
from typing import Any, List, Literal, Optional

from ninja import Field, Schema
from pydantic import ConfigDict

URL = r"^https?://\S+$" 

# Schemas Error 
class ErrorOut(Schema):
    detail: str


class ValidationErrorOut(Schema):
    detail: str
    errors: Any


# Pengguna dan autentikasi
class UserMiniOut(Schema):
    id: int
    name: str
    role: str


class UserOut(UserMiniOut):
    email: str
    is_active: bool


class RegisterIn(Schema):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8)


class LoginIn(Schema):
    email: str
    password: str


class RefreshIn(Schema):
    refresh: str


class TokenOut(Schema):
    access: str
    refresh: str
    token_type: str = "Bearer"


class RoleIn(Schema):
    role: Literal["USER", "CREATOR", "ADMIN"]


# Kategori Film
class CategoryIn(Schema):
    name: str = Field(min_length=2, max_length=50)


class CategoryMiniOut(Schema):
    category_id: int
    name: str
    slug: str


class CategoryOut(CategoryMiniOut):
    total_films: int


# input Film
# Poster dan dokumen dikirim sebagai LOKASI FILE (teks, maks. 100 karakter), mis. "films/posters/a.jpg".
# Tahun karya tidak dibatasi; 32767 hanyalah batas teknis kolom database.
class FilmIn(Schema):
    """Body POST /films dan PUT /films/{id}."""

    category_id: int
    judul: str = Field(min_length=3, max_length=255)
    sinopsis: str = Field(min_length=10)
    tahun_karya: int = Field(ge=1, le=32767)
    link_video_utama: str = Field(max_length=500, pattern=URL)
    gambar_poster: str = Field(min_length=1, max_length=100)
    file_naskah: Optional[str] = Field(None, max_length=100)
    file_storyboard: Optional[str] = Field(None, max_length=100)
    file_rab: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(json_schema_extra={"example": {
        "category_id": 2,
        "judul": "Langit Terakhir di Kampus",
        "sinopsis": "Dokumenter singkat tentang hari terakhir siswa di sekolah.",
        "tahun_karya": 2025,
        "link_video_utama": "https://www.youtube.com/watch?v=abc123",
        "gambar_poster": "films/posters/langit.jpg",
    }})


class FilmPatchIn(Schema):
    """Body PATCH /films/{id}: kirim hanya field yang diubah."""

    category_id: Optional[int] = None
    judul: Optional[str] = Field(None, min_length=3, max_length=255)
    sinopsis: Optional[str] = Field(None, min_length=10)
    tahun_karya: Optional[int] = Field(None, ge=1, le=32767)
    link_video_utama: Optional[str] = Field(None, max_length=500, pattern=URL)
    gambar_poster: Optional[str] = Field(None, min_length=1, max_length=100)
    file_naskah: Optional[str] = Field(None, max_length=100)
    file_storyboard: Optional[str] = Field(None, max_length=100)
    file_rab: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(json_schema_extra={"example": {"judul": "Judul Baru Film"}})


class ValidateIn(Schema):
    """Body PATCH /films/{id}/validate (khusus Admin)."""

    status: Literal["published", "rejected"]
    rejection_reason: Optional[str] = None


# Film: output
class FilmOut(Schema):
    """Satu baris pada daftar film."""

    film_id: int
    judul: str
    tahun_karya: int
    status: str
    gambar_poster: Optional[str] = None
    pembuat: str
    kategori: str
    total_votes: int
    total_discussions: int

    @staticmethod
    def resolve_pembuat(obj):
        return obj.user.name

    @staticmethod
    def resolve_kategori(obj):
        return obj.category.name


class FilmDetailOut(Schema):
    """Detail film beserta data berelasinya (pembuat, kategori, jumlah vote dan komentar)."""

    film_id: int
    judul: str
    sinopsis: str
    tahun_karya: int
    link_video_utama: str
    gambar_poster: Optional[str] = None
    file_naskah: Optional[str] = None
    file_storyboard: Optional[str] = None
    file_rab: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    created_at: datetime
    user: UserMiniOut
    category: CategoryMiniOut
    total_votes: int
    total_discussions: int


# Vote dan komentar 
class VoteOut(Schema):
    vote_id: int
    user: UserMiniOut
    created_at: datetime


class VoteResultOut(Schema):
    voted: bool  
    total_votes: int


class DiscussionIn(Schema):
    isi_pesan: str = Field(min_length=1, max_length=2000)
    parent_id: Optional[int] = None  # untuk membalas komentar lain


class ReplyOut(Schema):
    diskusi_id: int
    user: UserMiniOut
    isi_pesan: str
    created_at: datetime


class DiscussionOut(ReplyOut):
    replies: List[ReplyOut]