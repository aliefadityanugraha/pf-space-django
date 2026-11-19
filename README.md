# PF Space — Backend Galeri Digital & Arsip Karya Produksi Film

**PF Space** adalah platform pusat data dan arsip digital berbasis web untuk menyimpan karya film beserta dokumen produksi siswa (**Naskah, Storyboard, RAB, dan Poster**) di Jurusan Produksi Film **SMKN 1 Ngasem**. Sistem ini menerapkan alur validasi karya berjenjang (`pending` → `published` / `rejected`), manajemen hak akses berbasis *role* (`USER`, `CREATOR`, `ADMIN`), serta fitur apresiasi karya melalui **Voting** dan **Diskusi berjenjang (komentar & balasan)**.

Proyek ini disusun untuk memenuhi **Ujian Tengah Semester (UTS) Ganjil 2026/2027** mata kuliah **Pemrograman Sisi Server** (Kelompok `F11.C702RPL`, Dosen Pengampu: **Zudha Pratama, M.Kom.**).

---

## Navigasi Cepat Dokumen Proyek

| Dokumen | Lokasi / Tautan | Keterangan |
| :--- | :--- | :--- |
| **Analisis & Arsitektur Backend (Soal 1)** | [`SOAL1.md`](./SOAL1.md) atau `UTS_PSS_Analisis dan Arsitektur (Nomor 1).pdf` | Studi kasus, kebutuhan pengguna, tujuan backend, alur *client-server*, pola arsitektur, diagram, ERD, dan hak akses |
| **Dokumentasi REST API Tertulis** | [`API_DOKUMENTASI.md`](./API_DOKUMENTASI.md) | Daftar 19 endpoint, aturan validasi body, contoh request/respons nyata, dan format error |
| **Spesifikasi OpenAPI 3.1** | [`docs/openapi.json`](./docs/openapi.json) | Skema standar hasil ekspor otomatis Django Ninja (siap diimpor ke Postman / Insomnia) |
| **Dokumentasi API Interaktif (Swagger UI)** | `http://localhost:8000/api/docs` | Tersedia saat container berjalan; setiap endpoint dapat langsung diuji lewat *Try it out* |

---

## Tim Pengembang & Kontribusi

Setiap anggota bertanggung jawab atas pengerjaan implementasi, dokumentasi bagian terkait, serta presentasi penjelasan *source code* sesuai nomor soal masing-masing:

| No | Nama Lengkap | NIM | Cakupan Soal | Rincian Kontribusi & Presentasi |
| :---: | :--- | :--- | :---: | :--- |
| 1 | **Tedo Haris Candra** | `F11.2024.00165` | **Soal 01 – 02** | Analisis kebutuhan & arsitektur backend ([`SOAL1.md`](./SOAL1.md)), diagram arsitektur, alur *client-server*, ERD (`images/`), serta *containerization* Django & PostgreSQL (`Dockerfile`, `docker-compose.yaml`, `.env`), lengkap dengan presentasi Soal 01–02. |
| 2 | **Alief Aditya Nugraha** | `F11.2024.00166` | **Soal 03 – 04** | Perancangan & implementasi Django Models, migrasi, konfigurasi Django Admin, *seeding* data awal, dan operasi CRUD ORM (`core/models.py`, `core/admin.py`, `core/services.py`, `seed_data.py`, `crud_demo.py`); serta optimasi query ORM dan perbandingan jumlah query (`query_demo.py`), lengkap dengan presentasi Soal 03–04. |
| 3 | **Moch. Misbach Hafist Afrizal** | `F11.2024.00162` | **Soal 05 – 06** | Pengembangan 19 endpoint REST API menggunakan Django Ninja, validasi schema, penanganan error, dokumentasi API (`core/api.py`, `core/schemas.py`, `pfspace/urls.py`, `API_DOKUMENTASI.md`, `docs/openapi.json`, `core/tests.py`); serta autentikasi JWT dan otorisasi berbasis role (`core/auth.py`, `core/tests_auth.py`), lengkap dengan presentasi Soal 05–06. |

---

## 1. Arsitektur & Teknologi

Sistem dibangun menggunakan pola **Layered Architecture (Modular Monolith)** yang berjalan di atas dua container Docker (penjelasan lengkap analisis, alur *client-server*, diagram arsitektur, dan ERD dapat dibaca pada **[`SOAL1.md`](./SOAL1.md)**):
- **Backend Framework**: Python 3.11, Django 4.2, Django Ninja
- **Database**: PostgreSQL 15 (Alpine) dengan *persistent Docker Volume* (`postgres_data`)
- **Autentikasi & Otorisasi**: Custom User Model (`AUTH_USER_MODEL = 'core.User'`) dengan login berbasis `email`, password hashing bawaan Django, JWT Bearer Token (`PyJWT`, algoritma `HS256` dengan masa berlaku `access` 30 menit dan `refresh` 7 hari) pada `core/auth.py`, serta Role-Based Access Control (`USER`, `CREATOR`, `ADMIN`)
- **Service Layer**: Pemisahan logika bisnis dan optimasi ORM (`select_related`, `prefetch_related`, `annotate`, `transaction.atomic`) di dalam `core/services.py`
- **REST API & Dokumentasi**: 19 endpoint berbasis Django Ninja di `core/api.py`, validasi input/output Pydantic di `core/schemas.py`, serta spesifikasi OpenAPI 3.1 ([`docs/openapi.json`](./docs/openapi.json)) dan Swagger UI (`/api/docs`)

### Struktur Direktori Proyek
```text
pf-space-django/
├── core/                           # Aplikasi utama PF Space
│   ├── management/
│   │   └── commands/
│   │       ├── seed_data.py        # Custom command untuk pengisian data awal (seeding)
│   │       ├── crud_demo.py        # Demo operasi CRUD ORM pada entitas utama Film (Soal 3)
│   │       └── query_demo.py       # Demo perbandingan jumlah query sebelum & sesudah optimasi (Soal 4)
│   ├── migrations/                 # File migrasi skema database
│   ├── admin.py                    # Konfigurasi tampilan Django Admin Panel
│   ├── api.py                      # 19 endpoint REST API Django Ninja & exception handler (Soal 5)
│   ├── apps.py                     # Konfigurasi aplikasi core
│   ├── auth.py                     # Implementasi JWT (access/refresh) & role-based access (Soal 6)
│   ├── models.py                   # 5 Entitas ORM: User, Category, Film, Vote, Discussion
│   ├── schemas.py                  # Schema Pydantic/Ninja untuk validasi input & output JSON
│   ├── services.py                 # Service layer logika bisnis, CRUD, & optimasi ORM
│   ├── tests.py                    # Pengujian otomatis REST API (input valid, 422, 403, 404)
│   ├── tests_auth.py               # Pengujian otomatis autentikasi JWT & otorisasi role
│   └── views.py                    # Endpoint halaman utama (/) dan health check (/health/)
├── docs/
│   └── openapi.json                # Spesifikasi OpenAPI 3.1 hasil ekspor otomatis Django Ninja
├── images/                         # Aset diagram pendukung Soal 1
│   ├── diagram-arsitektur.png      # Diagram arsitektur sistem (Layered & Docker)
│   ├── diagram-client-server.png   # Diagram alur komunikasi client-server
│   └── diagram-erd.png             # Diagram relasi entitas (ERD)
├── pfspace/                        # Konfigurasi utama proyek Django
│   ├── asgi.py
│   ├── settings.py                 # Konfigurasi database, media, INSTALLED_APPS (core, ninja), dan AUTH_USER_MODEL
│   ├── urls.py                     # Routing utama (/), health (/health/), admin (/admin/), API (/api/), & media
│   └── wsgi.py
├── .env                            # Variabel environment untuk Django & PostgreSQL
├── API_DOKUMENTASI.md              # Dokumentasi tertulis lengkap REST API PF Space
├── Dockerfile                      # Definisi image container web (Django)
├── docker-compose.yaml             # Orkestrasi container web dan db (PostgreSQL)
├── manage.py                       # Utilitas CLI manajemen Django
├── README.md                       # Dokumentasi proyek
├── requirements.txt                # Daftar dependensi paket Python
└── SOAL1.md                        # Dokumen analisis kasus, arsitektur, ERD, dan hak akses (Soal 1)
```

---

## 2. Rancangan Entitas & Hak Akses

Rincian lengkap analisis entitas, atribut, relasi (ERD), dan alasan pemilihan arsitektur tersedia di **[`SOAL1.md`](./SOAL1.md)** serta diagram di [`images/diagram-erd.png`](./images/diagram-erd.png).

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
Jalankan perintah berikut dari terminal pada direktori utama `pf-space-django/` untuk membangun image `web` dan menyalakan service `db` (PostgreSQL) serta `web` (Django) di *background*:

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
# 1. Buat file migrasi untuk aplikasi core (jika ada perubahan model)
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
- **Health Check (Status Aplikasi & Koneksi DB)**: http://localhost:8000/health/
- **Django Admin Panel**: http://localhost:8000/admin/
  - Login menggunakan **Email**: `admin@smkn1ngasem.sch.id` dan **Password**: `password123` (atau menggunakan akun superuser yang baru Anda buat pada Tahap 5).
  - Di dalam Admin Panel, Guru/Admin dapat memfilter karya film berdasarkan **status** (`pending`, `published`, `rejected`) dan **category**, mencari data berdasarkan judul/kreator, serta mengelola seluruh entitas (`Users`, `Categories`, `Films`, `Votes`, `Discussions`).
- **Swagger UI (Dokumentasi API Interaktif)**: http://localhost:8000/api/docs
- **OpenAPI JSON (Live)**: http://localhost:8000/api/openapi.json

---

## 4. REST API, Autentikasi JWT & Dokumentasi

Dokumentasi lengkap yang mencakup aturan validasi tiap field, contoh *request* & *response* nyata, serta contoh error (`401`, `403`, `404`, `422`) tersedia pada **[`API_DOKUMENTASI.md`](./API_DOKUMENTASI.md)** dan spesifikasi OpenAPI 3.1 pada **[`docs/openapi.json`](./docs/openapi.json)**.

### Ringkasan 19 Endpoint REST API
| Kelompok Tag | Jumlah | Daftar Endpoint |
| :--- | :---: | :--- |
| **Autentikasi** | 4 | `POST /api/register`, `POST /api/login`, `POST /api/refresh`, `GET /api/me` |
| **Kategori** | 2 | `GET /api/categories`, `POST /api/categories` |
| **Film** | 7 | `GET /api/films`, `POST /api/films`, `GET /api/films/{film_id}`, `PUT /api/films/{film_id}`, `PATCH /api/films/{film_id}`, `DELETE /api/films/{film_id}`, `PATCH /api/films/{film_id}/validate` |
| **Data Berelasi** | 4 | `GET /api/films/{film_id}/votes`, `GET /api/films/{film_id}/discussions`, `POST /api/films/{film_id}/discussions`, `POST /api/films/{film_id}/vote` |
| **Admin** | 2 | `GET /api/users`, `PATCH /api/users/{user_id}/role` |

### Cara Menguji Endpoint Terkunci di Swagger UI (`/api/docs`)
1. Buka `http://localhost:8000/api/docs`.
2. Jalankan `POST /api/login` menggunakan salah satu akun uji dari Tahap 4 (misalnya `admin@smkn1ngasem.sch.id` / `password123`).
3. Salin nilai `access` dari respons `200 OK`.
4. Klik tombol **Authorize** di kanan atas halaman Swagger, tempel token tersebut, lalu klik **Authorize**.
5. Endpoint privat (seperti `GET /api/me`, `POST /api/films`, `PATCH /api/films/{film_id}/validate`, dll.) kini siap diuji langsung.

---

## 5. Demo Fitur & Pengujian Otomatis (Soal 3 – 6)

### 1. Demo CRUD ORM Entitas Utama (Soal 3)
Memperagakan operasi `CREATE`, `READ`, `UPDATE`, dan `DELETE` pada model `Film` menggunakan Django ORM (data demo otomatis dibersihkan kembali setelah selesai):
```bash
docker compose exec web python manage.py crud_demo
```

### 2. Demo Perbandingan Optimasi Query (Soal 4)
Membandingkan jumlah query dan waktu eksekusi pada proses pengambilan daftar film `published` beserta pembuat, kategori, jumlah vote, dan jumlah komentar antara versi **tanpa optimasi (N+1)**, **`select_related` + `prefetch_related`**, dan **`select_related` + `annotate`** (data uji sementara otomatis di-*rollback* sehingga database tetap bersih):
```bash
docker compose exec web python manage.py query_demo
```

### 3. Pengujian Otomatis REST API & JWT (Soal 5 & 6)
Menjalankan total **43 skenario pengujian otomatis** di [`core/tests.py`](./core/tests.py) (21 uji: input valid, input tidak valid `422`, akses terlarang `403`, data tidak ditemukan `404`) dan [`core/tests_auth.py`](./core/tests_auth.py) (22 uji: registrasi & hash password, login, refresh token, tanpa token `401`, token tidak valid/kedaluwarsa `401`, serta pembatasan role `403`):
```bash
docker compose exec web python manage.py test core -v 2
```

### 4. Ekspor Ulang Berkas OpenAPI (Jika Ada Perubahan API/Schema)
```bash
docker compose exec web python manage.py export_openapi_schema --api core.api.api --output docs/openapi.json --indent 2
```

---

## 6. Daftar Perintah Operasional & Troubleshooting

| Kebutuhan | Perintah CLI |
| :--- | :--- |
| Melihat log server Django secara langsung | `docker compose logs -f web` |
| Menjalankan demo CRUD ORM (Soal 3) | `docker compose exec web python manage.py crud_demo` |
| Menjalankan demo perbandingan optimasi query (Soal 4) | `docker compose exec web python manage.py query_demo` |
| Menjalankan seluruh unit test API & JWT (Soal 5 & 6) | `docker compose exec web python manage.py test core -v 2` |
| Mengekspor ulang skema OpenAPI ke `docs/openapi.json` | `docker compose exec web python manage.py export_openapi_schema --api core.api.api --output docs/openapi.json --indent 2` |
| Masuk ke Django Interactive Shell (menguji `services.py`) | `docker compose exec web python manage.py shell` |
| Masuk ke konsol database PostgreSQL (`psql`) | `docker compose exec db psql -U pfspace_user -d pfspace_db` |
| Merestart server aplikasi setelah perubahan konfigurasi | `docker compose restart web` |
| Menghentikan container (data database tetap aman di volume) | `docker compose down` |
| Menghentikan container sekaligus menghapus volume database | `docker compose down -v` |
