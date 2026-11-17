"""
JWT dan pembatasan akses berdasarkan role.
- buat_token()  : membuat token (access untuk tiap request, refresh untuk meminta access baru)
- baca_token()  : memeriksa token (tanda tangan, masa berlaku, jenis, dan penggunanya)
- JWTAuth       : dipasang pada endpoint dengan  auth=JWTAuth(...)
"""
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.core.exceptions import PermissionDenied
from ninja.errors import AuthenticationError
from ninja.security import HttpBearer

from .models import User

ALGORITMA = "HS256"
UMUR_ACCESS = timedelta(minutes=30)
UMUR_REFRESH = timedelta(days=7)


def buat_token(user, jenis="access"):
    """Membuat token JWT yang ditandatangani dengan SECRET_KEY."""
    sekarang = datetime.now(timezone.utc)
    umur = UMUR_ACCESS if jenis == "access" else UMUR_REFRESH
    payload = {
        "sub": str(user.pk),    # pemilik token
        "role": user.role,      # informasi role yang dipakai
        "type": jenis,
        "iat": sekarang,
        "exp": sekarang + umur,  # batas kedaluwarsa
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITMA)


def baca_token(token, jenis="access"):
    """Mengembalikan pengguna pemilik token, atau menolak dengan 401."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITMA])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(message="Token sudah kedaluwarsa. Silakan login ulang.")
    except jwt.PyJWTError:
        raise AuthenticationError(message="Token tidak valid.")

    if payload.get("type") != jenis:
        raise AuthenticationError(message="Jenis token tidak sesuai.")

    user = User.objects.filter(pk=payload.get("sub"), is_active=True).first()
    if user is None:
        raise AuthenticationError(message="Pengguna pemilik token tidak ditemukan atau nonaktif.")
    return user


class JWTAuth(HttpBearer):
    """
    auth=JWTAuth()                    -> semua pengguna yang sudah login
    auth=JWTAuth("CREATOR", "ADMIN")  -> hanya role tertentu (selain itu 403)
    Tanpa token / token salah / token kedaluwarsa -> 401.
    """

    def __init__(self, *roles):
        super().__init__()
        self.roles = roles

    def authenticate(self, request, token):
        user = baca_token(token)
        if self.roles and user.role not in self.roles and not user.is_superuser:
            raise PermissionDenied(f"Aksi ini hanya untuk role: {', '.join(self.roles)}.")
        return user  # tersedia di endpoint sebagai request.auth