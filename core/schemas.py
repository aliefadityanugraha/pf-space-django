"""
Schema : bentuk data yang boleh MASUK ke API (input) dan KELUAR dari API (output).

- Schema input  : memeriksa kiriman client. Jika tidak cocok, API langsung menjawab 422.
- Schema output : menentukan field apa saja yang dikirim balik ke client.
"""
from datetime import datetime
from typing import Any, List, Optional

from ninja import Field, Schema
from pydantic import ConfigDict


# SCHEMA ERROR
class ErrorOut(Schema):
    detail: str


class ValidationErrorOut(Schema):
    detail: str
    errors: Any


# SCHEMA OUTPUT RINGKAS
class UserMiniOut(Schema):
    """Data pengguna yang aman ditampilkan (tanpa email dan password)."""

    id: int
    name: str
    role: str


class CategoryMiniOut(Schema):
    category_id: int
    name: str
    slug: str


class CategoryOut(Schema):
    category_id: int
    name: str
    slug: str
    total_films: int


# SCHEMA FILM - INPUT
# Catatan file: poster dan dokumen produksi dikirim sebagai LOKASI FILE (teks), contoh
# "films/posters/poster.jpg". Unggah file fisik dilakukan lewat Django Admin.

class FilmFields(Schema):
    """Field yang dipakai bersama oleh POST dan PUT."""

    category_id: int
    judul: str = Field(min_length=3, max_length=255)
    sinopsis: str = Field(min_length=10)
    tahun_karya: int = Field(ge=1, le=32767)
    link_video_utama: str = Field(max_length=500, pattern=r"^https?://\S+$")
    gambar_poster: str = Field(min_length=1, max_length=100)
    file_naskah: Optional[str] = Field(None, max_length=100)
    file_storyboard: Optional[str] = Field(None, max_length=100)
    file_rab: Optional[str] = Field(None, max_length=100)


class FilmIn(FilmFields):
    """Body untuk POST /films (membuat film baru)."""

    # pembuat film dikirim lewat user_id.
    user_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 2,
                "category_id": 2,
                "judul": "Langit Terakhir di Kampus",
                "sinopsis": "Dokumenter singkat tentang hari terakhir siswa di sekolah.",
                "tahun_karya": 2025,
                "link_video_utama": "https://www.youtube.com/watch?v=abc123",
                "gambar_poster": "films/posters/langit.jpg",
                "file_naskah": "films/scripts/langit.pdf",
            }
        }
    )


class FilmPutIn(FilmFields):
    """Body untuk PUT /films/{id} (mengganti data film; field wajib harus lengkap)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category_id": 2,
                "judul": "Langit Terakhir di Kampus (Revisi)",
                "sinopsis": "Dokumenter singkat tentang hari terakhir siswa di sekolah.",
                "tahun_karya": 2025,
                "link_video_utama": "https://www.youtube.com/watch?v=abc123",
                "gambar_poster": "films/posters/langit.jpg",
            }
        }
    )


class FilmPatchIn(Schema):
    """Body untuk PATCH /films/{id} (mengubah sebagian data; semua field boleh dikosongkan)."""

    category_id: Optional[int] = None
    judul: Optional[str] = Field(None, min_length=3, max_length=255)
    sinopsis: Optional[str] = Field(None, min_length=10)
    tahun_karya: Optional[int] = Field(None, ge=1, le=32767)
    link_video_utama: Optional[str] = Field(None, max_length=500, pattern=r"^https?://\S+$")
    gambar_poster: Optional[str] = Field(None, min_length=1, max_length=100)
    file_naskah: Optional[str] = Field(None, max_length=100)
    file_storyboard: Optional[str] = Field(None, max_length=100)
    file_rab: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(json_schema_extra={"example": {"judul": "Judul Baru Film"}})


# SCHEMA FILM - OUTPUT

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
    """Detail satu film beserta data berelasinya (pembuat, kategori, jumlah vote dan komentar)."""

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


# SCHEMA DATA BERELASI (vote dan komentar)

class VoteOut(Schema):
    vote_id: int
    user: UserMiniOut
    created_at: datetime


class ReplyOut(Schema):
    """Satu balasan komentar."""

    diskusi_id: int
    user: UserMiniOut
    isi_pesan: str
    created_at: datetime


class DiscussionOut(ReplyOut):
    """Komentar utama beserta daftar balasannya."""

    replies: List[ReplyOut]