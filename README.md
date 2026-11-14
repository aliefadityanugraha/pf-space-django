# PF Space — Backend Galeri Digital & Arsip Karya Produksi Film

**PF Space** adalah platform pusat data dan arsip digital berbasis web untuk menyimpan karya film beserta dokumen produksi siswa (**Naskah, Storyboard, RAB, dan Poster**) di Jurusan Produksi Film **SMKN 1 Ngasem**. Sistem ini menerapkan alur validasi karya berjenjang (`pending` → `published` / `rejected`), manajemen hak akses berbasis *role* (`USER`, `CREATOR`, `ADMIN`), serta fitur apresiasi karya melalui **Voting** dan **Diskusi berjenjang (komentar & balasan)**.

---

## 1. Arsitektur & Teknologi

Sistem dibangun menggunakan pola **Layered Architecture (Modular Monolith)** yang berjalan di atas dua container Docker:
- **Backend Framework**: Python 3.11, Django 4.2, Django Ninja
- **Database**: PostgreSQL 15 (Alpine) dengan *persistent Docker Volume* (`postgres_data`)
- **Autentikasi & Otorisasi**: Custom User Model (`AUTH_USER_MODEL = 'core.User'`) dengan login berbasis `email` dan Role-Based Access Control (`USER`, `CREATOR`, `ADMIN`)
- **Service Layer**: Pemisahan logika bisnis dan optimasi ORM (`select_related`, `prefetch_related`, `transaction.atomic`) di dalam `core/services.py`

### Struktur Direktori Proyek
```text
pfspace-django/
├── core/                           # Aplikasi utama PF Space
│   ├── management/
│   │   └── commands/
│   │       └── seed_data.py        # Custom command untuk pengisian data awal (seeding)
│   ├── migrations/                 # File migrasi skema database
│   ├── admin.py                    # Konfigurasi tampilan Django Admin Panel
│   ├── apps.py                     # Konfigurasi aplikasi core
│   ├── models.py                   # 5 Entitas ORM: User, Category, Film, Vote, Discussion
│   └── services.py                 # Service layer logika bisnis & operasi CRUD
├── pfspace/                        # Konfigurasi utama proyek Django
│   ├── asgi.py
│   ├── settings.py                 # Konfigurasi database, media, dan AUTH_USER_MODEL
│   ├── urls.py                     # Routing utama & serving file media
│   └── wsgi.py
├── .env                            # Variabel environment untuk Django & PostgreSQL
├── Dockerfile                      # Definisi image container web (Django)
├── docker-compose.yaml             # Orkestrasi container web dan db (PostgreSQL)
├── manage.py                       # Utilitas CLI manajemen Django
├── requirements.txt                # Daftar dependensi paket Python
└── README.md                       # Dokumentasi proyek
```

---

## 2. Rancangan Entitas & Hak Akses

### Lima Entitas Utama (`core/models.py`)
1. **`User` (`users`)**: Kustomisasi `AbstractUser` dengan login menggunakan `email` (unik), atribut `name`, dan `role` (`USER`, `CREATOR`, `ADMIN`).
2. **`Category` (`categories`)**: Menyimpan kategori karya (`name` unik) dan menghasilkan `slug` secara otomatis.
3. **`Film` (`films`)**: Menyimpan metadata film (`judul`, `sinopsis`, `tahun_karya`, `link_video_utama`), file produksi (`gambar_poster`, `file_naskah`, `file_storyboard`, `file_rab`), serta status validasi (`pending`, `published`, `rejected`) dan `rejection_reason`.
4. **`Vote` (`votes`)**: Mencatat apresiasi pengguna terhadap film dengan batasan **`UniqueConstraint(fields=['user', 'film'])`** sehingga **1 user hanya dapat memberi 1 vote untuk 1 film**.
5. **`Discussion` (`discussions`)**: Mencatat komentar pengguna pada film beserta fitur balasan komentar melalui relasi rekursif (`parent_id`).

### Matriks Hak Akses Pengguna
| Aksi | User (Siswa/Umum) | Creator (Kelompok) | Admin (Guru) |
| :--- | :---: | :---: | :---: |
| Melihat film berstatus `published` | ✓ | ✓ | ✓ |
| Memberi Vote & Komentar (`Discussion`) | ✓ | ✓ | ✓ |
| Mengunggah karya film baru (`pending`) | – | ✓ | ✓ |
| Mengubah / menghapus karya film | – | Milik sendiri | Semua karya |
| Memvalidasi karya (`published` / `rejected`) | – | – | ✓ |
| Mengelola kategori, user, dan role | – | – | ✓ |

---

## 3. Panduan Lengkap Setup Awal hingga Aplikasi Berjalan

Pastikan **Docker** dan **Docker Compose** sudah terinstal dan berjalan di komputer Anda.

### Tahap 1: Periksa File Konfigurasi `.env`
Pastikan file `.env` sudah tersedia di direktori utama proyek dengan isi konfigurasi berikut:

```env
# Konfigurasi Database PostgreSQL
DB_NAME=pfspace_db
DB_USER=pfspace_user
DB_PASSWORD=pfspace_password
DB_HOST=db
DB_PORT=5432

# Konfigurasi Django
SECRET_KEY=your_secret_key_here
DEBUG=True
```

---

### Tahap 2: Build dan Jalankan Container Docker Compose
Jalankan perintah berikut dari terminal pada direktori utama `pfspace-django/` untuk membangun image `web` dan menyalakan service `db` (PostgreSQL) serta `web` (Django) di *background*:

```bash
docker compose up -d --build
```

Untuk memastikan kedua container (`web` dan `db`) sudah berstatus **Running / Up**, jalankan:
```bash
docker compose ps
```

---

### Tahap 3: Membuat & Menjalankan Migrasi Database
Setelah container menyala, buat file migrasi dari `core/models.py` lalu terapkan skema tabel ke database PostgreSQL:

```bash
# 1. Buat file migrasi untuk aplikasi core
docker compose exec web python manage.py makemigrations core

# 2. Terapkan seluruh migrasi ke database PostgreSQL
docker compose exec web python manage.py migrate
```

---

### Tahap 4: Menjalankan Seeding Data Awal (`seed_data`)
Proyek ini dilengkapi dengan custom management command `seed_data` yang menggunakan `get_or_create` (aman dijalankan berulang kali tanpa membuat data ganda). Jalankan perintah berikut:

```bash
docker compose exec web python manage.py seed_data
```

Perintah di atas otomatis mengisi database dengan:
1. **3 Kategori**: `Fiksi Pendek`, `Dokumenter`, dan `Iklan Layanan Masyarakat`.
2. **3 Akun Pengguna Dummy** (untuk masing-masing role):
   | Role | Email Login | Username | Password | Akses `/admin/` |
   | :--- | :--- | :--- | :--- | :--- |
   | **ADMIN (Guru)** | `admin@smkn1ngasem.sch.id` | `admin_guru` | `password123` | **Ya** (Superuser) |
   | **CREATOR** | `creator@smkn1ngasem.sch.id` | `creator_kelompok1` | `password123` | Tidak |
   | **USER (Siswa)** | `siswa@smkn1ngasem.sch.id` | `siswa_alief` | `password123` | Tidak |
3. **2 Karya Film Dummy**:
   - *Senja di Balik Layar* (Kategori: `Fiksi Pendek`, Status: **`published`**)
   - *Jejak Tradisi Ngasem* (Kategori: `Dokumenter`, Status: **`pending`**)
4. **1 Data Vote & 1 Data Discussion (Komentar)** oleh akun Siswa pada film *Senja di Balik Layar*.

---

### Tahap 5: Membuat Akun Superuser Baru (Opsional)
Selain menggunakan akun Admin hasil seeding di atas, Anda juga dapat membuat akun Superuser sendiri kapan saja dengan perintah:

```bash
docker compose exec web python manage.py createsuperuser
```
Ikuti prompt interaktif di terminal:
- **Email**: Masukkan alamat email login Anda (contoh: `guru@smkn1ngasem.sch.id`)
- **Username**: Masukkan username (contoh: `guru_pf`)
- **Name**: Masukkan nama lengkap Anda
- **Password**: Masukkan password (minimal 8 karakter)

---

### Tahap 6: Mengakses Aplikasi
Setelah semua tahapan di atas selesai, aplikasi sudah aktif dan dapat diakses melalui browser:

- **Server Aplikasi Utama**: http://localhost:8000/
- **Django Admin Panel**: http://localhost:8000/admin/
  - Login menggunakan **Email**: `admin@smkn1ngasem.sch.id` dan **Password**: `password123` (atau menggunakan akun superuser yang baru Anda buat pada Tahap 5).
  - Di dalam Admin Panel, Guru/Admin dapat memfilter karya film berdasarkan **status** (`pending`, `published`, `rejected`) dan **category**, mencari data berdasarkan judul/kreator, serta mengelola seluruh entitas (`Users`, `Categories`, `Films`, `Votes`, `Discussions`).

---

## 4. Daftar Perintah Operasional & Troubleshooting

| Kebutuhan | Perintah CLI |
| :--- | :--- |
| Melihat log server Django secara langsung | `docker compose logs -f web` |
| Masuk ke Django Interactive Shell (menguji `services.py`) | `docker compose exec web python manage.py shell` |
| Masuk ke konsol database PostgreSQL (`psql`) | `docker compose exec db psql -U pfspace_user -d pfspace_db` |
| Merestart server aplikasi setelah perubahan konfigurasi | `docker compose restart web` |
| Menghentikan container (data database tetap aman di volume) | `docker compose down` |
| Menghentikan container sekaligus menghapus volume database | `docker compose down -v` |
