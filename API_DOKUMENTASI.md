# Dokumentasi API PF Space

Dokumen ini menjelaskan cara memakai REST API PF Space: daftar endpoint, hak akses, bentuk data, contoh
request dan respons, serta kode status. Dokumentasi ini memenuhi ketentuan UTS nomor 4 (*Dokumentasi API*)
dan Soal 5 (*dokumentasi API interaktif*).

## 1. Informasi umum

| Hal | Keterangan |
|---|---|
| Alamat dasar | `http://localhost:8000/api` |
| Format data | JSON (`Content-Type: application/json`) |
| Autentikasi | JWT Bearer: header `Authorization: Bearer <access token>` |
| Mendapat token | `POST /api/login` menghasilkan `access` (30 menit) dan `refresh` (7 hari) |
| Memperbarui token | `POST /api/refresh` dengan `refresh` |
| Akun uji | `admin@`, `creator@`, `siswa@smkn1ngasem.sch.id`, password `password123` |

### Kode status

| Kode | Arti |
|---|---|
| 200 | Berhasil |
| 201 | Berhasil dibuat |
| 204 | Berhasil, tanpa isi (hapus) |
| 401 | Tanpa token, token tidak valid, atau token kedaluwarsa |
| 403 | Sudah login tetapi role tidak berhak, atau bukan pemilik data |
| 404 | Data tidak ditemukan |
| 422 | Data yang dikirim tidak valid |

Semua error berbentuk `{"detail": "pesan"}`; kode 422 menambahkan `errors` berisi rincian field yang salah.

## 2. Daftar endpoint (19 endpoint)

`ADMIN`, `CREATOR` = role yang diizinkan. *Login (semua role)* = cukup membawa token yang valid.

### Autentikasi

| Metode | URL | Akses | Fungsi | Parameter | Kode respons |
|---|---|---|---|---|---|
| POST | `/api/register` | Publik | Mendaftar akun baru (role USER) | body JSON | 201, 422 |
| POST | `/api/login` | Publik | Login: mendapat access token dan refresh token | body JSON | 200, 401 |
| POST | `/api/refresh` | Publik | Meminta access token baru memakai refresh token | body JSON | 200, 401 |
| GET | `/api/me` | Login (semua role) | Profil pengguna yang sedang login | - | 200, 401 |

### Kategori

| Metode | URL | Akses | Fungsi | Parameter | Kode respons |
|---|---|---|---|---|---|
| GET | `/api/categories` | Publik | Daftar kategori film | - | 200 |
| POST | `/api/categories` | ADMIN | Menambah kategori (Admin) | body JSON | 201, 401, 403, 404, 422 |

### Film

| Metode | URL | Akses | Fungsi | Parameter | Kode respons |
|---|---|---|---|---|---|
| GET | `/api/films` | Publik | Daftar film yang sudah dipublikasikan | `category` (query) | 200 |
| POST | `/api/films` | CREATOR, ADMIN | Membuat film baru (status awal: pending) | body JSON | 201, 401, 403, 404, 422 |
| GET | `/api/films/{film_id}` | Publik (film published) | Detail film beserta pembuat, kategori, jumlah vote dan komentar | `film_id` (path) | 200, 403, 404 |
| PUT | `/api/films/{film_id}` | CREATOR (milik sendiri), ADMIN | Mengganti data film (PUT: field wajib harus lengkap) | `film_id` (path), body JSON | 200, 401, 403, 404, 422 |
| PATCH | `/api/films/{film_id}` | CREATOR (milik sendiri), ADMIN | Mengubah sebagian data film (PATCH: kirim field yang diubah saja) | `film_id` (path), body JSON | 200, 401, 403, 404, 422 |
| DELETE | `/api/films/{film_id}` | CREATOR (milik sendiri), ADMIN | Menghapus film | `film_id` (path) | 204, 401, 403, 404 |
| PATCH | `/api/films/{film_id}/validate` | ADMIN | Memvalidasi film: published atau rejected (Admin) | `film_id` (path), body JSON | 200, 401, 403, 404, 422 |

### Data Berelasi

| Metode | URL | Akses | Fungsi | Parameter | Kode respons |
|---|---|---|---|---|---|
| GET | `/api/films/{film_id}/votes` | Publik | Daftar vote pada sebuah film | `film_id` (path) | 200, 404 |
| GET | `/api/films/{film_id}/discussions` | Publik | Komentar utama pada sebuah film beserta balasannya | `film_id` (path) | 200, 404 |
| POST | `/api/films/{film_id}/discussions` | Login (semua role) | Menulis komentar atau balasan (semua role yang login) | `film_id` (path), body JSON | 201, 401, 403, 404, 422 |
| POST | `/api/films/{film_id}/vote` | Login (semua role) | Vote atau batalkan vote pada film published (semua role yang login) | `film_id` (path) | 200, 401, 403, 404, 422 |

### Admin

| Metode | URL | Akses | Fungsi | Parameter | Kode respons |
|---|---|---|---|---|---|
| GET | `/api/users` | ADMIN | Daftar semua pengguna (Admin) | - | 200, 401, 403 |
| PATCH | `/api/users/{user_id}/role` | ADMIN | Mengubah role pengguna (Admin) | `user_id` (path), body JSON | 200, 401, 403, 404, 422 |

## 3. Bentuk data yang dikirim (body)

### `POST /register`

| Field | Tipe | Wajib | Aturan |
|---|---|:-:|---|
| `name` | string | ya | minimal 2 karakter; maksimal 100 karakter |
| `email` | string | ya | pola `^[^@\s]+@[^@\s]+\.[^@\s]+$` |
| `username` | string | ya | minimal 3 karakter; maksimal 150 karakter |
| `password` | string | ya | minimal 8 karakter |

### `POST /login`

| Field | Tipe | Wajib | Aturan |
|---|---|:-:|---|
| `email` | string | ya | - |
| `password` | string | ya | - |

### `POST /refresh`

| Field | Tipe | Wajib | Aturan |
|---|---|:-:|---|
| `refresh` | string | ya | - |

### `POST /films` dan `PUT /films/{film_id}`

| Field | Tipe | Wajib | Aturan |
|---|---|:-:|---|
| `category_id` | integer | ya | - |
| `judul` | string | ya | minimal 3 karakter; maksimal 255 karakter |
| `sinopsis` | string | ya | minimal 10 karakter |
| `tahun_karya` | integer | ya | minimal 1; maksimal 32767 |
| `link_video_utama` | string | ya | maksimal 500 karakter; pola `^https?://\S+$` |
| `gambar_poster` | string | ya | minimal 1 karakter; maksimal 100 karakter |
| `file_naskah` | string | tidak | maksimal 100 karakter |
| `file_storyboard` | string | tidak | maksimal 100 karakter |
| `file_rab` | string | tidak | maksimal 100 karakter |

### `PATCH /films/{film_id}` (kirim field yang diubah saja)

| Field | Tipe | Wajib | Aturan |
|---|---|:-:|---|
| `category_id` | integer | tidak | - |
| `judul` | string | tidak | minimal 3 karakter; maksimal 255 karakter |
| `sinopsis` | string | tidak | minimal 10 karakter |
| `tahun_karya` | integer | tidak | minimal 1; maksimal 32767 |
| `link_video_utama` | string | tidak | maksimal 500 karakter; pola `^https?://\S+$` |
| `gambar_poster` | string | tidak | minimal 1 karakter; maksimal 100 karakter |
| `file_naskah` | string | tidak | maksimal 100 karakter |
| `file_storyboard` | string | tidak | maksimal 100 karakter |
| `file_rab` | string | tidak | maksimal 100 karakter |

### `PATCH /films/{film_id}/validate`

| Field | Tipe | Wajib | Aturan |
|---|---|:-:|---|
| `status` | string | ya | salah satu: `published`, `rejected` |
| `rejection_reason` | string | tidak | - |

### `POST /films/{film_id}/discussions`

| Field | Tipe | Wajib | Aturan |
|---|---|:-:|---|
| `isi_pesan` | string | ya | minimal 1 karakter; maksimal 2000 karakter |
| `parent_id` | integer | tidak | - |

### `POST /categories`

| Field | Tipe | Wajib | Aturan |
|---|---|:-:|---|
| `name` | string | ya | minimal 2 karakter; maksimal 50 karakter |

### `PATCH /users/{user_id}/role`

| Field | Tipe | Wajib | Aturan |
|---|---|:-:|---|
| `role` | string | ya | salah satu: `USER`, `CREATOR`, `ADMIN` |

Catatan: poster dan dokumen produksi dikirim sebagai **lokasi file berupa teks** (maksimal 100 karakter),
misalnya `films/posters/poster.jpg`. Unggah file fisik dilakukan lewat Django Admin. Tahun karya tidak dibatasi
selain batas teknis kolom database (maksimal 32767).

## 4. Contoh penggunaan (hasil pemanggilan nyata)

Contoh berikut dijalankan pada data dari `python manage.py seed_data`.

#### Login

```http
POST /api/login
Content-Type: application/json

{
  "email": "admin@smkn1ngasem.sch.id",
  "password": "password123"
}
```

Respons **200**:

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5...",
  "token_type": "Bearer"
}
```

Salin nilai `access`, lalu kirim sebagai header `Authorization: Bearer <access>` pada endpoint yang terkunci.

#### Membaca detail film (data berelasi)

```http
GET /api/films/3
```

Respons **200**:

```json
{
  "film_id": 3,
  "judul": "Langit Terakhir di Kampus",
  "sinopsis": "Sinopsis dummy untuk film Langit Terakhir di Kampus.",
  "tahun_karya": 2025,
  "link_video_utama": "https://www.youtube.com/watch?v=dummy",
  "gambar_poster": "/media/films/posters/dummy.jpg",
  "file_naskah": null,
  "file_storyboard": null,
  "file_rab": null,
  "status": "published",
  "rejection_reason": null,
  "created_at": "2026-11-19T00:21:00.221Z",
  "user": {
    "id": 2,
    "name": "Raka Pratama (Kelompok Sineas Muda)",
    "role": "CREATOR"
  },
  "category": {
    "category_id": 2,
    "name": "Dokumenter",
    "slug": "dokumenter"
  },
  "total_votes": 3,
  "total_discussions": 3
}
```

#### Membuat film (Creator)

```http
POST /api/films
Content-Type: application/json

{
  "category_id": 2,
  "judul": "Film Uji Dokumentasi",
  "sinopsis": "Contoh film untuk dokumentasi API PF Space.",
  "tahun_karya": 2026,
  "link_video_utama": "https://www.youtube.com/watch?v=contoh",
  "gambar_poster": "films/posters/contoh.jpg"
}
Authorization: Bearer <access token>
```

Respons **201**:

```json
{
  "film_id": 10,
  "judul": "Film Uji Dokumentasi",
  "sinopsis": "Contoh film untuk dokumentasi API PF Space.",
  "tahun_karya": 2026,
  "link_video_utama": "https://www.youtube.com/watch?v=contoh",
  "gambar_poster": "/media/films/posters/contoh.jpg",
  "file_naskah": null,
  "file_storyboard": null,
  "file_rab": null,
  "status": "pending",
  "rejection_reason": null,
  "created_at": "2026-11-19T00:21:01.285Z",
  "user": {
    "id": 2,
    "name": "Raka Pratama (Kelompok Sineas Muda)",
    "role": "CREATOR"
  },
  "category": {
    "category_id": 2,
    "name": "Dokumenter",
    "slug": "dokumenter"
  },
  "total_votes": 0,
  "total_discussions": 0
}
```

Status awal film selalu `pending` sampai divalidasi Admin.

#### Memvalidasi film (Admin)

```http
PATCH /api/films/7/validate
Content-Type: application/json

{
  "status": "published"
}
Authorization: Bearer <access token>
```

Respons **200**:

```json
{
  "film_id": 7,
  "judul": "Menjelang Pentas Seni",
  "status": "published",
  "rejection_reason": null,
  "...": "(field lain dipersingkat)"
}
```

Untuk menolak: `{"status": "rejected", "rejection_reason": "alasan penolakan"}` (alasan wajib diisi).

### Contoh respons error

#### 401: tanpa token

```http
GET /api/me
```

Respons **401**:

```json
{
  "detail": "Token tidak ditemukan. Login lewat POST /api/login, lalu kirim header 'Authorization: Bearer <access token>'."
}
```

#### 401: token tidak valid

```http
GET /api/me
Authorization: Bearer <access token>
```

Respons **401**:

```json
{
  "detail": "Token tidak valid."
}
```

#### 403: role tidak diizinkan (token siswa)

```http
POST /api/films
Authorization: Bearer <access token>
```

Respons **403**:

```json
{
  "detail": "Aksi ini hanya untuk role: CREATOR, ADMIN."
}
```

#### 404: data tidak ditemukan

```http
GET /api/films/999
```

Respons **404**:

```json
{
  "detail": "Film tidak ditemukan."
}
```

#### 422: data tidak valid (judul 2 huruf)

```http
POST /api/films
Content-Type: application/json

{
  "...": "...",
  "judul": "ab"
}
Authorization: Bearer <access token>
```

Respons **422**:

```json
{
  "detail": "Data yang dikirim tidak valid.",
  "errors": [
    {
      "type": "string_too_short",
      "loc": [
        "body",
        "data",
        "judul"
      ],
      "msg": "String should have at least 3 characters",
      "ctx": {
        "min_length": 3
      }
    }
  ]
}
```

Daftar `errors` dipersingkat menjadi satu kesalahan. `loc` menunjukkan field yang salah.

## 5. Memperbarui dokumentasi

Setelah mengubah endpoint atau schema:

1. Muat ulang http://localhost:8000/api/docs (Swagger UI ikut berubah otomatis).
2. Ekspor ulang berkas OpenAPI dengan perintah di bagian 1 nomor 5.
3. Perbarui berkas ini bila ada endpoint baru (tabel pada bagian 3 mengikuti `docs/openapi.json`).
