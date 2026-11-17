import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count
from django.test.utils import CaptureQueriesContext

from core.models import Category, Discussion, Film, User, Vote

JUMLAH_FILM_DEMO = 20


# ----------------------------------------------------------------------
# PROSES YANG DIUJI (sama untuk ketiga versi):
# "Menampilkan daftar film published beserta judul, nama pembuat,
#  nama kategori, jumlah vote, dan jumlah komentar."
# Hanya cara mengambil datanya yang berbeda.
# ----------------------------------------------------------------------

def versi_sebelum():
    """SEBELUM: tanpa optimasi. Setiap akses relasi memicu query baru (masalah N+1)."""
    hasil = []
    for film in Film.objects.filter(status=Film.Status.PUBLISHED).order_by("film_id"):
        hasil.append((
            film.judul,
            film.user.name,             
            film.category.name,         
            film.votes.count(),         
            film.discussions.count(),   
        ))
    return hasil


def versi_sesudah():
    """SESUDAH: select_related (JOIN) + prefetch_related (1 query tambahan per relasi)."""
    films = (
        Film.objects.filter(status=Film.Status.PUBLISHED)
        .select_related("user", "category")        # user & kategori ikut di query utama
        .prefetch_related("votes", "discussions")  # vote & komentar diambil sekaligus
        .order_by("film_id")
    )
    hasil = []
    for film in films:  # perulangan sama persis dengan versi sebelum
        hasil.append((
            film.judul,
            film.user.name,
            film.category.name,
            film.votes.count(),         # dibaca dari hasil prefetch, tanpa query baru
            film.discussions.count(),
        ))
    return hasil


def versi_annotate():
    """ALTERNATIF: select_related + annotate (menghitung jumlah langsung di database)."""
    films = (
        Film.objects.filter(status=Film.Status.PUBLISHED)
        .select_related("user", "category")
        .annotate(
            total_votes=Count("votes", distinct=True),
            total_discussions=Count("discussions", distinct=True),
        )
        .order_by("film_id")
    )
    return [
        (f.judul, f.user.name, f.category.name, f.total_votes, f.total_discussions)
        for f in films
    ]


def ukur(fungsi):
    """Menjalankan fungsi, lalu mengembalikan hasil, daftar query, dan durasinya."""
    with CaptureQueriesContext(connection) as konteks:
        mulai = time.perf_counter()
        hasil = fungsi()
        durasi_ms = (time.perf_counter() - mulai) * 1000
    return hasil, konteks.captured_queries, durasi_ms


class Command(BaseCommand):
    help = "Demo optimasi query (Soal 4): membandingkan jumlah query sebelum dan sesudah optimasi."

    @transaction.atomic
    def handle(self, *args, **options):
        users = list(User.objects.all()[:3])
        kategori = Category.objects.first()
        if not users or not kategori:
            raise CommandError("Data awal belum ada. Jalankan dulu: python manage.py seed_data")
        pembuat = users[0]

        # Catat dulu jumlah film published yang asli (dari seed_data)
        jumlah_asli = Film.objects.filter(status=Film.Status.PUBLISHED).count()

        # Tambah data uji sementara agar perbedaannya terlihat jelas.
        # Semua data ini DIBATALKAN (rollback) di akhir, jadi database tidak berubah.
        for i in range(1, JUMLAH_FILM_DEMO + 1):
            film = Film.objects.create(
                user=pembuat,
                category=kategori,
                judul=f"[DEMO Q] Film {i:02d}",
                sinopsis="Data uji sementara untuk demo optimasi query.",
                tahun_karya=2025,
                link_video_utama="https://www.youtube.com/watch?v=demo",
                gambar_poster="films/posters/demo.jpg",
                status=Film.Status.PUBLISHED,
            )
            for u in users:
                Vote.objects.create(user=u, film=film)
            for n in range(2):
                Discussion.objects.create(user=users[n % len(users)], film=film, isi_pesan=f"Komentar {n + 1}")

        jumlah_film = Film.objects.filter(status=Film.Status.PUBLISHED).count()
        self.stdout.write(self.style.MIGRATE_HEADING("\nDEMO OPTIMASI QUERY"))
        self.stdout.write("Proses : daftar film published + pembuat, kategori, jumlah vote, jumlah komentar")
        self.stdout.write(
            f"Data   : {jumlah_film} film published "
            f"({jumlah_asli} data asli + {JUMLAH_FILM_DEMO} data uji sementara)\n"
        )

        hasil_a, query_a, waktu_a = ukur(versi_sebelum)
        hasil_b, query_b, waktu_b = ukur(versi_sesudah)
        hasil_c, query_c, waktu_c = ukur(versi_annotate)

        self.stdout.write("Contoh query yang berulang pada versi SEBELUM:")
        for q in query_a[1:5]:
            self.stdout.write(f"  {q['sql'][:105]}...")

        self.stdout.write("\n" + "-" * 72)
        self.stdout.write(f"{'Versi':<44}{'Query':>8}{'Waktu':>12}")
        self.stdout.write("-" * 72)
        self.stdout.write(f"{'SEBELUM  (tanpa optimasi)':<44}{len(query_a):>8}{waktu_a:>9.1f} ms")
        self.stdout.write(f"{'SESUDAH  (select_related + prefetch_related)':<44}{len(query_b):>8}{waktu_b:>9.1f} ms")
        self.stdout.write(f"{'ALTERNATIF (select_related + annotate)':<44}{len(query_c):>8}{waktu_c:>9.1f} ms")
        self.stdout.write("-" * 72)

        sama = hasil_a == hasil_b == hasil_c
        self.stdout.write(f"Hasil data ketiga versi sama? {sama}")
        if len(query_a):
            hemat = (1 - len(query_b) / len(query_a)) * 100
            self.stdout.write(self.style.SUCCESS(
                f"Jumlah query turun dari {len(query_a)} menjadi {len(query_b)} (hemat {hemat:.0f}%)."
            ))

        # Batalkan semua data uji sementara
        transaction.set_rollback(True)