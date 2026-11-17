"""
REST API PF Space (Django Ninja)
  - CRUD Film, pembacaan data berelasi, schema validasi, penanganan kesalahan, dokumentasi
  - login JWT dan pembatasan akses berdasarkan role (auth=JWTAuth(...))

Alur satu request:  URL -> auth (token + role) -> schema (validasi) -> services.py (ORM) -> JSON
Dokumentasi interaktif: http://localhost:8000/api/docs
"""
import re
from typing import List, Optional

from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from ninja import NinjaAPI
from ninja.errors import AuthenticationError
from ninja.errors import ValidationError as SchemaValidationError

from . import services
from .auth import JWTAuth, baca_token, buat_token
from .models import Category, Film
from .schemas import (
    CategoryIn, CategoryMiniOut, CategoryOut, DiscussionIn, DiscussionOut, ErrorOut, FilmDetailOut,
    FilmIn, FilmOut, FilmPatchIn, LoginIn, RefreshIn, RegisterIn, ReplyOut, RoleIn, TokenOut,
    UserOut, ValidateIn, ValidationErrorOut, VoteOut, VoteResultOut,
)

DESKRIPSI = """
REST API galeri digital dan arsip karya film siswa SMKN 1 Ngasem.

**Cara memakai endpoint yang terkunci:** `POST /login` -> salin `access` -> klik **Authorize** -> tempel token.

| Kode | Arti |
|---|---|
| 200 / 201 / 204 | Berhasil / berhasil dibuat / berhasil tanpa isi |
| 401 | Tanpa token, token tidak valid, atau token kedaluwarsa |
| 403 | Role tidak diizinkan, atau bukan pemilik data |
| 404 | Data tidak ditemukan |
| 422 | Data yang dikirim tidak valid |
"""

api = NinjaAPI(title="PF Space API", version="1.0.0", description=DESKRIPSI)

# Hak akses per endpoint (dipakai pada parameter auth=...)
login_wajib = JWTAuth()                        # semua role yang login
creator_atau_admin = JWTAuth("CREATOR", "ADMIN")
hanya_admin = JWTAuth("ADMIN")

ERR = {401: ErrorOut, 403: ErrorOut, 404: ErrorOut, 422: ValidationErrorOut}  # untuk dokumentasi


# PENANGANAN KESALAHAN: setiap jenis error menjadi JSON + kode status yang sesuai
def balas(request, status, detail, **tambahan):
    return api.create_response(request, {"detail": detail, **tambahan}, status=status)


@api.exception_handler(AuthenticationError)
def tangani_401(request, exc):
    """Tanpa token, token salah, atau kedaluwarsa."""
    if exc.message == "Unauthorized":  
        return balas(request, 401, "Token tidak ditemukan. Login lewat POST /api/login, "
                                   "lalu kirim header 'Authorization: Bearer <access token>'.")
    return balas(request, 401, exc.message)


@api.exception_handler(PermissionDenied)
def tangani_403(request, exc):
    return balas(request, 403, str(exc) or "Anda tidak memiliki izin untuk aksi ini.")


NAMA_DATA = {"Film": "Film", "User": "Pengguna", "Category": "Kategori"}


@api.exception_handler(Http404)
def tangani_404(request, exc):
    cocok = re.match(r"No (\w+) matches", str(exc)) 
    return balas(request, 404, f"{NAMA_DATA.get(cocok.group(1), 'Data') if cocok else 'Data'} tidak ditemukan.")


@api.exception_handler(SchemaValidationError)
def tangani_422_schema(request, exc):
    """Kiriman client tidak cocok dengan schema (field kosong, tipe salah, terlalu pendek, dll.)."""
    return balas(request, 422, "Data yang dikirim tidak valid.", errors=exc.errors)


@api.exception_handler(DjangoValidationError)
def tangani_422_model(request, exc):
    """Lolos schema tetapi ditolak validasi model/services (mis. email kembar, format URL salah)."""
    errors = exc.message_dict if hasattr(exc, "error_dict") else exc.messages
    return balas(request, 422, "Data tidak lolos validasi.", errors=errors)


# AUTENTIKASI (Soal 6): daftar, login, refresh, profil
@api.post("/register", response={201: UserOut, 422: ValidationErrorOut}, tags=["Autentikasi"],
          summary="Mendaftar akun baru (role USER)")
def register(request, data: RegisterIn):
    return 201, services.register_user(**data.model_dump())  # password di hash


@api.post("/login", response={200: TokenOut, 401: ErrorOut}, tags=["Autentikasi"],
          summary="Login: mendapat access token dan refresh token")
def login(request, data: LoginIn):
    user = authenticate(request, username=data.email, password=data.password)  # cek hash password Django
    if user is None:
        raise AuthenticationError(message="Email atau password salah.")
    return {"access": buat_token(user), "refresh": buat_token(user, "refresh")}


@api.post("/refresh", response={200: TokenOut, 401: ErrorOut}, tags=["Autentikasi"],
          summary="Meminta access token baru memakai refresh token")
def refresh(request, data: RefreshIn):
    user = baca_token(data.refresh, "refresh")
    return {"access": buat_token(user), "refresh": data.refresh}


@api.get("/me", response={200: UserOut, 401: ErrorOut}, auth=login_wajib, tags=["Autentikasi"],
         summary="Profil pengguna yang sedang login")
def profil(request):
    return request.auth


# KATEGORI
@api.get("/categories", response=List[CategoryOut], tags=["Kategori"], summary="Daftar kategori film")
def daftar_kategori(request):
    return services.get_all_categories()


@api.post("/categories", response={201: CategoryMiniOut, **ERR}, auth=hanya_admin, tags=["Kategori"],
          summary="Menambah kategori (Admin)")
def buat_kategori(request, data: CategoryIn):
    return 201, services.create_category(admin_user=request.auth, name=data.name)



# FILM: membaca (publik)
@api.get("/films", response=List[FilmOut], tags=["Film"], summary="Daftar film yang sudah dipublikasikan")
def daftar_film(request, category: Optional[str] = None):
    """Isi `category` dengan slug untuk menyaring, misalnya `dokumenter`."""
    return services.get_published_films(category_slug=category)


@api.get("/films/{film_id}", response={200: FilmDetailOut, 403: ErrorOut, 404: ErrorOut}, tags=["Film"],
         summary="Detail film beserta pembuat, kategori, jumlah vote dan komentar")
def detail_film(request, film_id: int):
    """Film yang belum `published` tidak dapat dilihat publik (403)."""
    return services.get_film_detail(film_id=film_id)


# FILM: membuat, mengubah, menghapus
@api.post("/films", response={201: FilmDetailOut, **ERR}, auth=creator_atau_admin, tags=["Film"],
          summary="Membuat film baru (status awal: pending)")
def buat_film(request, data: FilmIn):
    kategori = get_object_or_404(Category, pk=data.category_id)
    isi = data.model_dump(exclude={"category_id"})
    film = services.create_film(user=request.auth, category=kategori, **isi)
    return 201, services.get_film_detail(film_id=film.film_id, requesting_user=request.auth)


def ubah_film(pengguna, film_id, isi):
    """Dipakai bersama oleh PUT dan PATCH. Creator hanya boleh mengubah filmnya sendiri; Admin semua."""
    category_id = isi.pop("category_id", None)
    if category_id is not None:
        isi["category"] = get_object_or_404(Category, pk=category_id)
    services.update_film(requesting_user=pengguna, film_id=film_id, **isi)
    return services.get_film_detail(film_id=film_id, requesting_user=pengguna)


@api.put("/films/{film_id}", response={200: FilmDetailOut, **ERR}, auth=creator_atau_admin, tags=["Film"],
         summary="Mengganti data film (PUT: field wajib harus lengkap)")
def ganti_film(request, film_id: int, data: FilmIn):
    return ubah_film(request.auth, film_id, data.model_dump())


@api.patch("/films/{film_id}", response={200: FilmDetailOut, **ERR}, auth=creator_atau_admin, tags=["Film"],
           summary="Mengubah sebagian data film (PATCH: kirim field yang diubah saja)")
def ubah_sebagian_film(request, film_id: int, data: FilmPatchIn):
    return ubah_film(request.auth, film_id, data.model_dump(exclude_unset=True))


@api.delete("/films/{film_id}", response={204: None, 401: ErrorOut, 403: ErrorOut, 404: ErrorOut},
            auth=creator_atau_admin, tags=["Film"], summary="Menghapus film")
def hapus_film(request, film_id: int):
    services.delete_film(requesting_user=request.auth, film_id=film_id)
    return 204, None


@api.patch("/films/{film_id}/validate", response={200: FilmDetailOut, **ERR}, auth=hanya_admin, tags=["Film"],
           summary="Memvalidasi film: published atau rejected (Admin)")
def validasi_film(request, film_id: int, data: ValidateIn):
    services.update_film_status(admin_user=request.auth, film_id=film_id, new_status=data.status,
                                rejection_reason=data.rejection_reason)
    return services.get_film_detail(film_id=film_id, requesting_user=request.auth)


# DATA BERELASI: vote dan komentar milik sebuah film
@api.get("/films/{film_id}/votes", response={200: List[VoteOut], 404: ErrorOut}, tags=["Data Berelasi"],
         summary="Daftar vote pada sebuah film")
def daftar_vote(request, film_id: int):
    get_object_or_404(Film, pk=film_id)  # 404 jika film tidak ada
    return services.get_film_votes(film_id=film_id)


@api.get("/films/{film_id}/discussions", response={200: List[DiscussionOut], 404: ErrorOut},
         tags=["Data Berelasi"], summary="Komentar utama pada sebuah film beserta balasannya")
def daftar_komentar(request, film_id: int):
    get_object_or_404(Film, pk=film_id)
    return services.get_film_discussions(film_id=film_id)


@api.post("/films/{film_id}/vote", response={200: VoteResultOut, **ERR}, auth=login_wajib, tags=["Data Berelasi"],
          summary="Vote atau batalkan vote pada film published (semua role yang login)")
def vote_film(request, film_id: int):
    sudah_vote, total = services.toggle_vote(user=request.auth, film_id=film_id)
    return {"voted": sudah_vote, "total_votes": total}


@api.post("/films/{film_id}/discussions", response={201: ReplyOut, **ERR}, auth=login_wajib,
          tags=["Data Berelasi"], summary="Menulis komentar atau balasan (semua role yang login)")
def tulis_komentar(request, film_id: int, data: DiscussionIn):
    return 201, services.create_discussion(user=request.auth, film_id=film_id, isi_pesan=data.isi_pesan,
                                           parent_id=data.parent_id)


# KELOLA PENGGUNA (khusus Admin)
@api.get("/users", response={200: List[UserOut], 401: ErrorOut, 403: ErrorOut}, auth=hanya_admin,
         tags=["Admin"], summary="Daftar semua pengguna (Admin)")
def daftar_user(request):
    return services.get_all_users()


@api.patch("/users/{user_id}/role", response={200: UserOut, **ERR}, auth=hanya_admin, tags=["Admin"],
           summary="Mengubah role pengguna (Admin)")
def ubah_role(request, user_id: int, data: RoleIn):
    return services.update_user_role(admin_user=request.auth, target_user_id=user_id, new_role=data.role)