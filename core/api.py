"""
REST API PF Space (Django Ninja)
Alur satu request:  URL -> fungsi endpoint -> schema (validasi) -> services.py (ORM) -> JSON

Dokumentasi interaktif: http://localhost:8000/api/docs
"""
import re
from typing import List, Optional

from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI
from ninja.errors import ValidationError as SchemaValidationError

from . import services
from .models import Category, Film, User
from .schemas import (
    CategoryOut,
    DiscussionOut,
    ErrorOut,
    FilmDetailOut,
    FilmIn,
    FilmOut,
    FilmPatchIn,
    FilmPutIn,
    ValidationErrorOut,
    VoteOut,
)

DESKRIPSI = """
REST API galeri digital dan arsip karya film siswa SMKN 1 Ngasem.

**Kode status yang dipakai**

| Kode | Arti | Contoh |
|---|---|---|
| 200 | Berhasil | Membaca atau mengubah data |
| 201 | Berhasil dibuat | `POST /films` |
| 204 | Berhasil, tanpa isi | `DELETE /films/{id}` |
| 403 | Tidak diizinkan | Role `USER` mengunggah film, atau film belum dipublikasikan |
| 404 | Data tidak ditemukan | Film, kategori, atau pengguna dengan ID tersebut tidak ada |
| 422 | Data tidak valid | Field kosong, tipe salah, judul terlalu pendek, link bukan URL |

**Catatan sementara (Soal 5):** pengguna yang melakukan aksi dikirim lewat `user_id`
(body pada POST, query pada PUT/PATCH/DELETE). Pada Soal 6 diganti dengan token JWT.
"""

api = NinjaAPI(
    title="PF Space API",
    version="1.0.0",
    description=DESKRIPSI,
)


# PENANGANAN KESALAHAN (ERROR HADLER)

@api.exception_handler(SchemaValidationError)
def tangani_schema_tidak_valid(request, exc):
    """Kiriman client tidak cocok dengan schema (field kosong, tipe salah, terlalu pendek, dll.)."""
    return api.create_response(
        request,
        {"detail": "Data yang dikirim tidak valid.", "errors": exc.errors},
        status=422,
    )


@api.exception_handler(DjangoValidationError)
def tangani_model_tidak_valid(request, exc):
    """Data lolos schema tetapi ditolak validasi model (mis. format URL tidak benar)."""
    errors = exc.message_dict if hasattr(exc, "error_dict") else exc.messages
    return api.create_response(
        request,
        {"detail": "Data tidak lolos validasi.", "errors": errors},
        status=422,
    )


@api.exception_handler(PermissionDenied)
def tangani_tidak_diizinkan(request, exc):
    return api.create_response(
        request,
        {"detail": str(exc) or "Anda tidak memiliki izin untuk aksi ini."},
        status=403,
    )


NAMA_DATA = {"Film": "Film", "User": "Pengguna", "Category": "Kategori"}


@api.exception_handler(Http404)
def tangani_tidak_ditemukan(request, exc):
    """Data dengan ID yang diminta tidak ada. Pesan Django 'No Film matches...' diubah ke Indonesia."""
    cocok = re.match(r"No (\w+) matches", str(exc))
    nama = NAMA_DATA.get(cocok.group(1), "Data") if cocok else "Data"
    return api.create_response(request, {"detail": f"{nama} tidak ditemukan."}, status=404)


# FUNGSI BANTU

def ambil_pengguna(user_id: int) -> User:
    """SEMENTARA (Soal 5): pengguna yang beraksi dicari dari user_id. Di Soal 6 diganti token JWT."""
    return get_object_or_404(User, pk=user_id)


# ENDPOINT KATEGORI

@api.get("/categories", response=List[CategoryOut], tags=["Kategori"], summary="Daftar kategori film")
def daftar_kategori(request):
    return services.get_all_categories()


# ENDPOINT FILM - MEMBACA (GET)

@api.get("/films", response=List[FilmOut], tags=["Film"], summary="Daftar film yang sudah dipublikasikan")
def daftar_film(request, category: Optional[str] = None):
    """Mengambil film berstatus `published`. Isi `category` dengan slug untuk menyaring, misalnya `dokumenter`."""
    return services.get_published_films(category_slug=category)


@api.get(
    "/films/{film_id}",
    response={200: FilmDetailOut, 403: ErrorOut, 404: ErrorOut},
    tags=["Film"],
    summary="Detail satu film beserta pembuat, kategori, dan jumlah vote/komentar",
)
def detail_film(request, film_id: int):
    """Film yang belum `published` tidak dapat dilihat publik (403)."""
    return services.get_film_detail(film_id=film_id)


# ENDPOINT FILM - MEMBUAT, MENGUBAH, MENGHAPUS (POST, PUT, PATCH, DELETE)

@api.post(
    "/films",
    response={201: FilmDetailOut, 403: ErrorOut, 404: ErrorOut, 422: ValidationErrorOut},
    tags=["Film"],
    summary="Membuat film baru (status awal: pending)",
)
def buat_film(request, data: FilmIn):
    """Hanya pengguna berrole `CREATOR` atau `ADMIN` yang boleh mengunggah film."""
    pembuat = ambil_pengguna(data.user_id)
    kategori = get_object_or_404(Category, pk=data.category_id)

    film = services.create_film(
        user=pembuat,
        category=kategori,
        judul=data.judul,
        sinopsis=data.sinopsis,
        tahun_karya=data.tahun_karya,
        link_video_utama=data.link_video_utama,
        gambar_poster=data.gambar_poster,
        file_naskah=data.file_naskah,
        file_storyboard=data.file_storyboard,
        file_rab=data.file_rab,
    )
    return 201, services.get_film_detail(film_id=film.film_id, requesting_user=pembuat)


def ubah_film(film_id: int, user_id: int, isi: dict):
    """Dipakai bersama oleh PUT dan PATCH."""
    pengguna = ambil_pengguna(user_id)

    category_id = isi.pop("category_id", None)
    if category_id is not None:
        isi["category"] = get_object_or_404(Category, pk=category_id)

    services.update_film(requesting_user=pengguna, film_id=film_id, **isi)
    return services.get_film_detail(film_id=film_id, requesting_user=pengguna)


@api.put(
    "/films/{film_id}",
    response={200: FilmDetailOut, 403: ErrorOut, 404: ErrorOut, 422: ValidationErrorOut},
    tags=["Film"],
    summary="Mengganti data film (PUT: field wajib harus lengkap)",
)
def ganti_film(request, film_id: int, user_id: int, data: FilmPutIn):
    """Creator hanya dapat mengubah film miliknya sendiri; Admin dapat mengubah semua film."""
    return ubah_film(film_id, user_id, data.model_dump())


@api.patch(
    "/films/{film_id}",
    response={200: FilmDetailOut, 403: ErrorOut, 404: ErrorOut, 422: ValidationErrorOut},
    tags=["Film"],
    summary="Mengubah sebagian data film (PATCH: kirim field yang diubah saja)",
)
def ubah_sebagian_film(request, film_id: int, user_id: int, data: FilmPatchIn):
    return ubah_film(film_id, user_id, data.model_dump(exclude_unset=True))


@api.delete(
    "/films/{film_id}",
    response={204: None, 403: ErrorOut, 404: ErrorOut},
    tags=["Film"],
    summary="Menghapus film",
)
def hapus_film(request, film_id: int, user_id: int):
    pengguna = ambil_pengguna(user_id)
    services.delete_film(requesting_user=pengguna, film_id=film_id)
    return 204, None


# ENDPOINT DATA BERELASI (vote dan komentar milik sebuah film)

@api.get(
    "/films/{film_id}/votes",
    response={200: List[VoteOut], 404: ErrorOut},
    tags=["Data Berelasi"],
    summary="Daftar vote pada sebuah film",
)
def daftar_vote(request, film_id: int):
    get_object_or_404(Film, pk=film_id)
    return services.get_film_votes(film_id=film_id)


@api.get(
    "/films/{film_id}/discussions",
    response={200: List[DiscussionOut], 404: ErrorOut},
    tags=["Data Berelasi"],
    summary="Daftar komentar utama pada sebuah film beserta balasannya",
)
def daftar_komentar(request, film_id: int):
    get_object_or_404(Film, pk=film_id)
    return services.get_film_discussions(film_id=film_id)