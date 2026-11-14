from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import User, Category, Film, Vote, Discussion


class Command(BaseCommand):
    help = 'Memasukkan data awal (dummy data) PF Space secara idempoten (get_or_create).'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Memulai proses seeding data PF Space...'))

        # 1. Buat 3 Kategori Utama
        categories_data = [
            'Fiksi Pendek',
            'Dokumenter',
            'Iklan Layanan Masyarakat',
        ]
        categories = {}
        for cat_name in categories_data:
            category, created = Category.objects.get_or_create(name=cat_name)
            categories[cat_name] = category
            status_text = 'Dibuat' if created else 'Sudah ada'
            self.stdout.write(f"  - Kategori '{category.name}' (slug: {category.slug}): {status_text}")

        # 2. Buat 3 Jenis User (Admin, Creator, User) dengan password default 'password123'
        default_password = 'password123'
        users_data = [
            {
                'email': 'admin@smkn1ngasem.sch.id',
                'username': 'admin_guru',
                'name': 'Budi Santoso, S.Sn. (Guru)',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'creator@smkn1ngasem.sch.id',
                'username': 'creator_kelompok1',
                'name': 'Raka Pratama (Kelompok Sineas Muda)',
                'role': User.Role.CREATOR,
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'email': 'siswa@smkn1ngasem.sch.id',
                'username': 'siswa_alief',
                'name': 'Alief Putra (Siswa)',
                'role': User.Role.USER,
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        users = {}
        for u_data in users_data:
            user, created = User.objects.get_or_create(
                email=u_data['email'],
                defaults={
                    'username': u_data['username'],
                    'name': u_data['name'],
                    'role': u_data['role'],
                    'is_staff': u_data['is_staff'],
                    'is_superuser': u_data['is_superuser'],
                },
            )
            if created:
                user.set_password(default_password)
                user.save()
            users[u_data['role']] = user
            status_text = 'Dibuat' if created else 'Sudah ada'
            self.stdout.write(f"  - User [{user.role}] {user.email}: {status_text}")

        creator_user = users[User.Role.CREATOR]
        regular_user = users[User.Role.USER]

        # 3. Buat 2 Data Film Dummy (1 Published, 1 Pending)
        film_published, created_pub = Film.objects.get_or_create(
            judul='Senja di Balik Layar',
            user=creator_user,
            defaults={
                'category': categories['Fiksi Pendek'],
                'sinopsis': (
                    'Kisah perjuangan sekelompok siswa SMK jurusan Produksi Film '
                    'dalam menyelesaikan proyek film pendek pertama mereka di tengah keterbatasan alat.'
                ),
                'tahun_karya': 2025,
                'link_video_utama': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'gambar_poster': 'films/posters/senja_poster_dummy.jpg',
                'file_naskah': 'films/scripts/naskah_senja_dummy.pdf',
                'file_storyboard': 'films/storyboards/storyboard_senja_dummy.pdf',
                'file_rab': 'films/rab/rab_senja_dummy.xlsx',
                'status': Film.Status.PUBLISHED,
            },
        )
        self.stdout.write(
            f"  - Film '{film_published.judul}' [{film_published.status}]: "
            f"{'Dibuat' if created_pub else 'Sudah ada'}"
        )

        film_pending, created_pend = Film.objects.get_or_create(
            judul='Jejak Tradisi Ngasem',
            user=creator_user,
            defaults={
                'category': categories['Dokumenter'],
                'sinopsis': (
                    'Film dokumenter yang mengangkat pelestarian kesenian tradisional '
                    'dan pengrajin lokal di sekitar wilayah Kecamatan Ngasem.'
                ),
                'tahun_karya': 2026,
                'link_video_utama': 'https://www.youtube.com/watch?v=9bZkp7q19f0',
                'gambar_poster': 'films/posters/jejak_tradisi_poster_dummy.jpg',
                'file_naskah': 'films/scripts/naskah_jejak_tradisi_dummy.pdf',
                'file_storyboard': 'films/storyboards/storyboard_jejak_tradisi_dummy.pdf',
                'file_rab': 'films/rab/rab_jejak_tradisi_dummy.xlsx',
                'status': Film.Status.PENDING,
            },
        )
        self.stdout.write(
            f"  - Film '{film_pending.judul}' [{film_pending.status}]: "
            f"{'Dibuat' if created_pend else 'Sudah ada'}"
        )

        # 4. Buat 1 Data Vote & 1 Data Discussion pada Film yang 'published'
        vote, vote_created = Vote.objects.get_or_create(
            user=regular_user,
            film=film_published,
        )
        self.stdout.write(
            f"  - Vote oleh {vote.user.email} pada '{vote.film.judul}': "
            f"{'Dibuat' if vote_created else 'Sudah ada'}"
        )

        discussion, disc_created = Discussion.objects.get_or_create(
            user=regular_user,
            film=film_published,
            parent=None,
            defaults={
                'isi_pesan': 'Sinematografi dan penataan cahayanya keren banget! Sangat menginspirasi untuk angkatan kami.',
            },
        )
        self.stdout.write(
            f"  - Discussion oleh {discussion.user.email} pada '{discussion.film.judul}': "
            f"{'Dibuat' if disc_created else 'Sudah ada'}"
        )

        self.stdout.write(self.style.SUCCESS('\nSeeding data PF Space selesai dengan sukses!'))
        self.stdout.write(
            self.style.WARNING(
                f"Info Login Default -> Password semua akun: '{default_password}'\n"
                f"  1. Admin   : admin@smkn1ngasem.sch.id\n"
                f"  2. Creator : creator@smkn1ngasem.sch.id\n"
                f"  3. User    : siswa@smkn1ngasem.sch.id"
            )
        )
