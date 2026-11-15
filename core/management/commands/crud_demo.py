from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Category, Film, User

JUDUL_DEMO = "[DEMO] Film Uji CRUD"


class Command(BaseCommand):
    help = "Demo operasi CRUD (tambah, baca, ubah, hapus) pada entitas utama Film memakai Django ORM."

    @transaction.atomic
    def handle(self, *args, **options):
        # Data pendukung dari seed_data: Film butuh satu user (Creator) dan satu kategori
        creator = User.objects.filter(role=User.Role.CREATOR).first()
        kategori = Category.objects.first()
        if not creator or not kategori:
            raise CommandError("Data awal belum ada. Jalankan dulu: python manage.py seed_data")

        # Bersihkan sisa demo sebelumnya agar perintah ini aman dijalankan berulang
        Film.objects.filter(judul=JUDUL_DEMO).delete()

        # ---------------------------------------------------------------
        self.judul("1. CREATE - menambah film baru")
        film = Film(
            user=creator,
            category=kategori,
            judul=JUDUL_DEMO,
            sinopsis="Film percobaan untuk memperagakan operasi CRUD dengan ORM.",
            tahun_karya=2025,
            link_video_utama="https://www.youtube.com/watch?v=demo",
            gambar_poster="films/posters/demo.jpg",
        )
        film.full_clean()   # jalankan validasi dulu
        film.save()         # INSERT ke tabel films
        self.stdout.write(f"  Berhasil disimpan: film_id={film.film_id}, status={film.status}")

        # ---------------------------------------------------------------
        self.judul("2. READ - membaca data")
        satu = Film.objects.get(pk=film.pk)
        self.stdout.write(f"  get(pk)            : {satu.judul}")

        jumlah_pending = Film.objects.filter(status=Film.Status.PENDING).count()
        self.stdout.write(f"  filter(pending)    : {jumlah_pending} film berstatus pending")

        self.stdout.write("  semua film + relasi (select_related):")
        for f in Film.objects.select_related("user", "category").order_by("film_id"):
            self.stdout.write(f"    #{f.film_id} {f.judul} | {f.category.name} | oleh {f.user.name} | {f.status}")

        # ---------------------------------------------------------------
        self.judul("3. UPDATE - mengubah data")
        film.judul = "[DEMO] Film Uji CRUD (Revisi)"
        film.save(update_fields=["judul"])                       # UPDATE satu objek
        Film.objects.filter(pk=film.pk).update(status=Film.Status.PUBLISHED)  # UPDATE lewat queryset
        film.refresh_from_db()                                   # ambil ulang dari database
        self.stdout.write(f"  Setelah diubah: judul='{film.judul}', status={film.status}")

        # ---------------------------------------------------------------
        self.judul("4. DELETE - menghapus data")
        total_sebelum = Film.objects.count()
        film.delete()                                            # DELETE dari tabel films
        total_sesudah = Film.objects.count()
        masih_ada = Film.objects.filter(pk=film.pk).exists()
        self.stdout.write(f"  Total film: {total_sebelum} -> {total_sesudah}")
        self.stdout.write(f"  Film demo masih ada di database? {masih_ada}")

        self.stdout.write(self.style.SUCCESS("\nDemo CRUD selesai: tambah, baca, ubah, hapus berhasil."))

    def judul(self, teks):
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{teks}"))