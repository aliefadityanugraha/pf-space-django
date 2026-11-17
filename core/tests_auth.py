"""
Pengujian otomatis (JWT dan pembatasan akses berdasarkan role).
run:  python manage.py test core.tests_auth -v 2

  A. Akun dan login        -> password di-hash, token dibuat, login gagal ditolak
  B. Token bermasalah      -> 401 (tanpa token, tidak valid, kedaluwarsa)
  C. Role tidak diizinkan  -> 403
  D. Aksi yang diizinkan   -> Admin dan semua role sesuai haknya
"""
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings

from .auth import buat_token
from .models import Category, Film, User
from .tests import ApiTestCase


# AKUN DAN LOGIN
class AkunDanLoginTest(ApiTestCase):
    DATA_DAFTAR = {"name": "Siswa Baru", "email": "baru@test.id", "username": "siswabaru", "password": "Rahasia123"}

    def test_daftar_201_password_disimpan_sebagai_hash(self):
        """POST /register -> 201, role USER, password di database berupa hash (bukan teks asli)."""
        r = self.panggil("post", "/api/register", self.DATA_DAFTAR)
        self.assertEqual((r.status_code, r.json()["role"]), (201, "USER"))
        self.assertNotIn("password", r.json())
        user = User.objects.get(email="baru@test.id")
        self.assertTrue(user.password.startswith("pbkdf2_"))
        self.assertNotEqual(user.password, "Rahasia123")
        self.assertTrue(user.check_password("Rahasia123"))

    def test_daftar_tidak_valid_422(self):
        """POST /register dengan email kembar atau password pendek -> 422."""
        kasus = {"email sudah terdaftar": {"email": "siswa@test.id"}, "password 4 karakter": {"password": "abcd"}}
        for nama, ubah in kasus.items():
            with self.subTest(nama):
                r = self.panggil("post", "/api/register", {**self.DATA_DAFTAR, **ubah})
                self.assertEqual(r.status_code, 422)

    def test_login_berhasil_200(self):
        """POST /login dengan email dan password benar -> 200 berisi access dan refresh token."""
        r = self.panggil("post", "/api/login", {"email": "siswa@test.id", "password": "Rahasia123"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()), {"access", "refresh", "token_type"})

    def test_login_gagal_401(self):
        """Login dengan password salah, email tidak terdaftar, atau akun nonaktif -> 401."""
        User.objects.filter(pk=self.creator_lain.pk).update(is_active=False)
        kasus = {"password salah": ("siswa@test.id", "salah"), "email tidak terdaftar": ("hantu@test.id", "Rahasia123"),
                 "akun nonaktif": ("creator2@test.id", "Rahasia123")}
        for nama, (email, password) in kasus.items():
            with self.subTest(nama):
                r = self.panggil("post", "/api/login", {"email": email, "password": password})
                self.assertEqual(r.status_code, 401)

    def test_token_dari_login_dapat_dipakai_di_me_200(self):
        """Token hasil login dipakai pada GET /me -> 200 dan menampilkan profil sendiri."""
        token = self.panggil("post", "/api/login", {"email": "siswa@test.id", "password": "Rahasia123"}).json()["access"]
        r = self.client.get("/api/me", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual((r.status_code, r.json()["email"]), (200, "siswa@test.id"))

    def test_refresh_token_menghasilkan_access_baru_200(self):
        """POST /refresh dengan refresh token valid -> 200 dan access token baru bisa dipakai."""
        refresh = buat_token(self.siswa, "refresh")
        r = self.panggil("post", "/api/refresh", {"refresh": refresh})
        self.assertEqual(r.status_code, 200)
        me = self.client.get("/api/me", HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
        self.assertEqual(me.status_code, 200)

    def test_jenis_token_tertukar_401(self):
        """Access token dipakai untuk /refresh, atau refresh token dipakai sebagai access -> 401."""
        r = self.panggil("post", "/api/refresh", {"refresh": buat_token(self.siswa, "access")})
        self.assertEqual(r.status_code, 401)
        me = self.client.get("/api/me", HTTP_AUTHORIZATION=f"Bearer {buat_token(self.siswa, 'refresh')}")
        self.assertEqual(me.status_code, 401)


# TOKEN BERMASALAH (401)
class TokenBermasalahTest(ApiTestCase):
    ENDPOINT_TERKUNCI = (("post", "/api/films"), ("patch", "/api/films/1"), ("delete", "/api/films/1"),
                         ("patch", "/api/films/1/validate"), ("post", "/api/films/1/vote"),
                         ("post", "/api/films/1/discussions"), ("post", "/api/categories"),
                         ("get", "/api/users"), ("get", "/api/me"))

    def token_dengan(self, kunci=None, **ubah):
        payload = {"sub": str(self.admin.pk), "type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
        payload.update(ubah)
        return jwt.encode(payload, kunci or settings.SECRET_KEY, algorithm="HS256")

    def test_tanpa_token_401(self):
        """Semua endpoint terkunci tanpa header Authorization -> 401."""
        for metode, url in self.ENDPOINT_TERKUNCI:
            with self.subTest(f"{metode.upper()} {url}"):
                r = self.panggil(metode, url, {} if metode != "get" else None)
                self.assertEqual(r.status_code, 401)
                self.assertIn("Token tidak ditemukan", r.json()["detail"])

    def test_token_tidak_valid_401(self):
        """Token asal-asalan, ditandatangani kunci lain, atau skema bukan Bearer -> 401."""
        kasus = {"token asal-asalan": "Bearer abc.def.ghi",
                 "ditandatangani kunci lain": f"Bearer {self.token_dengan(kunci='kunci-lain-yang-panjang-minimal-32-byte')}",
                 "skema bukan Bearer": f"Basic {self.token_dengan()}"}
        for nama, header in kasus.items():
            with self.subTest(nama):
                self.assertEqual(self.client.get("/api/me", HTTP_AUTHORIZATION=header).status_code, 401)

    def test_token_kedaluwarsa_401(self):
        """Token yang masa berlakunya sudah lewat -> 401 dengan pesan 'kedaluwarsa'."""
        token = self.token_dengan(exp=datetime.now(timezone.utc) - timedelta(minutes=1))
        r = self.client.get("/api/me", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(r.status_code, 401)
        self.assertIn("kedaluwarsa", r.json()["detail"])

    def test_token_pengguna_nonaktif_401(self):
        """Token milik akun yang sudah dinonaktifkan -> 401."""
        User.objects.filter(pk=self.siswa.pk).update(is_active=False)
        r = self.client.get("/api/me", HTTP_AUTHORIZATION=f"Bearer {buat_token(self.siswa)}")
        self.assertEqual(r.status_code, 401)


# ROLE TIDAK DIIZINKAN (403)
class RoleTidakDiizinkanTest(ApiTestCase):
    def test_role_user_tidak_boleh_mengunggah_403(self):
        """POST /films oleh role USER -> 403."""
        self.assertEqual(self.panggil("post", "/api/films", self.isi_film(), self.siswa).status_code, 403)

    def test_creator_tidak_boleh_memvalidasi_403(self):
        """PATCH /films/{id}/validate oleh Creator (pemilik film sekalipun) -> 403."""
        r = self.panggil("patch", self.url_film(self.film_pending) + "/validate", {"status": "published"}, self.creator)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Film.objects.get(pk=self.film_pending.pk).status, "pending")

    def test_bukan_admin_tidak_boleh_mengelola_data_403(self):
        """Daftar user, tambah kategori, dan ubah role oleh non-Admin -> 403."""
        kasus = (("get", "/api/users", None), ("post", "/api/categories", {"name": "Musikal"}),
                 ("patch", f"/api/users/{self.siswa.pk}/role", {"role": "ADMIN"}))
        for pengguna in (self.siswa, self.creator):
            for metode, url, data in kasus:
                with self.subTest(f"{pengguna.role} {metode.upper()} {url}"):
                    self.assertEqual(self.panggil(metode, url, data, pengguna).status_code, 403)
        self.assertEqual(User.objects.get(pk=self.siswa.pk).role, "USER")


# AKSI YANG DIIZINKAN
class AksiDiizinkanTest(ApiTestCase):
    def test_admin_memvalidasi_film_200(self):
        """Admin: pending -> published (200), lalu film tampil di daftar publik."""
        r = self.panggil("patch", self.url_film(self.film_pending) + "/validate", {"status": "published"}, self.admin)
        self.assertEqual((r.status_code, r.json()["status"]), (200, "published"))
        self.assertEqual(len(self.panggil("get", "/api/films").json()), 2)

    def test_admin_menolak_film_wajib_alasan(self):
        """Menolak tanpa alasan -> 422; dengan alasan -> 200 dan alasan tersimpan."""
        url = self.url_film(self.film_pending) + "/validate"
        self.assertEqual(self.panggil("patch", url, {"status": "rejected"}, self.admin).status_code, 422)
        r = self.panggil("patch", url, {"status": "rejected", "rejection_reason": "Audio kurang jelas"}, self.admin)
        self.assertEqual((r.status_code, r.json()["rejection_reason"]), (200, "Audio kurang jelas"))

    def test_status_validasi_tidak_dikenal_422(self):
        """Status selain published/rejected -> 422."""
        r = self.panggil("patch", self.url_film(self.film_pending) + "/validate", {"status": "approved"}, self.admin)
        self.assertEqual(r.status_code, 422)

    def test_admin_menambah_kategori_201(self):
        """Admin menambah kategori -> 201; nama kembar -> 422."""
        r = self.panggil("post", "/api/categories", {"name": "Musikal"}, self.admin)
        self.assertEqual((r.status_code, r.json()["slug"]), (201, "musikal"))
        self.assertEqual(self.panggil("post", "/api/categories", {"name": "Musikal"}, self.admin).status_code, 422)
        self.assertEqual(Category.objects.filter(name="Musikal").count(), 1)

    def test_admin_melihat_daftar_pengguna_200(self):
        """GET /users oleh Admin -> 200 berisi 4 akun."""
        r = self.panggil("get", "/api/users", None, self.admin)
        self.assertEqual((r.status_code, len(r.json())), (200, 4))

    def test_admin_mengubah_role_langsung_berlaku_200(self):
        """Siswa dinaikkan jadi CREATOR -> langsung boleh mengunggah film (token lama tetap dipakai)."""
        self.assertEqual(self.panggil("post", "/api/films", self.isi_film(), self.siswa).status_code, 403)
        r = self.panggil("patch", f"/api/users/{self.siswa.pk}/role", {"role": "CREATOR"}, self.admin)
        self.assertEqual((r.status_code, r.json()["role"]), (200, "CREATOR"))
        self.assertEqual(self.panggil("post", "/api/films", self.isi_film(), self.siswa).status_code, 201)

    def test_role_tidak_dikenal_422(self):
        """PATCH role dengan nilai 'SUPERHERO' -> 422."""
        r = self.panggil("patch", f"/api/users/{self.siswa.pk}/role", {"role": "SUPERHERO"}, self.admin)
        self.assertEqual(r.status_code, 422)

    def test_semua_role_boleh_vote_dan_komentar(self):
        """Creator dan Admin: vote (toggle), komentar, dan balasan -> berhasil; vote film pending -> 404."""
        for pengguna in (self.creator, self.admin):
            with self.subTest(pengguna.role):
                suka = self.panggil("post", self.url_film() + "/vote", None, pengguna)
                batal = self.panggil("post", self.url_film() + "/vote", None, pengguna)
                self.assertEqual((suka.json()["voted"], suka.json()["total_votes"]), (True, 2))
                self.assertEqual((batal.json()["voted"], batal.json()["total_votes"]), (False, 1))
                komentar = self.panggil("post", self.url_film() + "/discussions", {"isi_pesan": "Bagus"}, pengguna)
                balasan = self.panggil("post", self.url_film() + "/discussions",
                                       {"isi_pesan": "Setuju", "parent_id": komentar.json()["diskusi_id"]}, pengguna)
                self.assertEqual((komentar.status_code, balasan.status_code), (201, 201))
        pending = self.panggil("post", self.url_film(self.film_pending) + "/vote", None, self.creator)
        self.assertEqual(pending.status_code, 404)