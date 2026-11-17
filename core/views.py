from django.db import connection
from django.http import JsonResponse


def home(request):
    """Halaman utama: penanda bahwa aplikasi berjalan."""
    return JsonResponse(
        {
            "status": "ok",
            "aplikasi": "PF Space",
            "keterangan": "Backend galeri digital dan arsip karya film SMKN 1 Ngasem",
            "admin": "/admin/",
            "health": "/health/",
        },
        json_dumps_params={"ensure_ascii": False},
    )


def health(request):
    """Cek status aplikasi dan koneksi database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "connected"
    except Exception:
        database = "unavailable"
    return JsonResponse({"status": "ok", "database": database})