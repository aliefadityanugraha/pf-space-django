"""
Pengujian otomatis (CRUD Film dan data berelasi).
Jalankan:  python manage.py test core -v 2

  A. Input VALID           -> 200 / 201 / 204
  B. Input TIDAK VALID     -> 422 (data salah) dan 403 (bukan pemilik)
  C. Data TIDAK DITEMUKAN  -> 404
"""
from django.test import TestCase

from .auth import buat_token
from .models import Category, Discussion, Film, User, Vote


class ApiTestCase(TestCase):
    """Data awal yang sama untuk semua pengujian (juga dipakai tests_auth.py)."""

    @classmethod
    def setUpTestData(cls):
        def akun(nama, role):
            return User.objects.create_user(username=nama, email=f"{nama}@test.id", password="Rahasia123",
                                            name=nama.title(), role=role)

        cls.admin = akun("admin", User.Role.ADMIN)
        cls.creator = akun("creator", User.Role.CREATOR)
        cls.creator_lain = akun("creator2", User.Role.CREATOR)
        cls.siswa = akun("siswa", User.Role.USER)
        cls.kategori = Category.objects.create(name="Dokumenter")
        Category.objects.create(name="Animasi")

        data = dict(user=cls.creator, category=cls.kategori, sinopsis="Sinopsis film untuk pengujian API.",
                    tahun_karya=2025, link_video_utama="https://www.youtube.com/watch?v=abc123",
                    gambar_poster="films/posters/uji.jpg")
        cls.film = Film.objects.create(judul="Film Published", status=Film.Status.PUBLISHED, **data)
        cls.film_pending = Film.objects.create(judul="Film Pending", status=Film.Status.PENDING, **data)
        Vote.objects.create(user=cls.siswa, film=cls.film)
        komentar = Discussion.objects.create(user=cls.siswa, film=cls.film, isi_pesan="Komentar utama")
        Discussion.objects.create(user=cls.creator, film=cls.film, parent=komentar, isi_pesan="Balasan komentar")

    def panggil(self, metode, url, data=None, user=None):
        """Memanggil API. Jika `user` diisi, token pengguna itu dikirim di header Authorization."""
        header = {"HTTP_AUTHORIZATION": f"Bearer {buat_token(user)}"} if user else {}
        kirim = getattr(self.client, metode)
        if metode == "get":
            return kirim(url, data, **header)
        return kirim(url, data, content_type="application/json", **header)

    def isi_film(self, **ubah):
        """Body film yang valid; nilai bisa diganti, atau None untuk menghapus field."""
        data = {"category_id": self.kategori.category_id, "judul": "Langit Terakhir di Kampus",
                "sinopsis": "Dokumenter singkat tentang hari terakhir siswa di sekolah.", "tahun_karya": 2025,
                "link_video_utama": "https://www.youtube.com/watch?v=xyz789", "gambar_poster": "films/posters/langit.jpg"}
        data.update(ubah)
        return {k: v for k, v in data.items() if v is not None}

    def url_film(self, film=None):
        return f"/api/films/{(film or self.film).film_id}"


# INPUT VALID
class InputValidTest(ApiTestCase):
    def test_daftar_kategori_200(self):
        """GET /categories -> 200 berisi 2 kategori."""
        r = self.panggil("get", "/api/categories")
        self.assertEqual((r.status_code, len(r.json())), (200, 2))

    def test_daftar_film_hanya_published_200(self):
        """GET /films -> 200; film pending tidak tampil."""
        r = self.panggil("get", "/api/films")
        self.assertEqual((r.status_code, [f["judul"] for f in r.json()]), (200, ["Film Published"]))

    def test_daftar_film_filter_kategori_200(self):
        """GET /films?category=animasi -> 200 dan kosong."""
        r = self.panggil("get", "/api/films", {"category": "animasi"})
        self.assertEqual((r.status_code, r.json()), (200, []))

    def test_detail_film_memuat_data_berelasi_200(self):
        """GET /films/{id} -> 200 dengan pembuat, kategori, jumlah vote dan komentar."""
        r = self.panggil("get", self.url_film())
        data = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual((data["user"]["name"], data["category"]["name"]), ("Creator", "Dokumenter"))
        self.assertEqual((data["total_votes"], data["total_discussions"]), (1, 2))

    def test_daftar_vote_200(self):
        """GET /films/{id}/votes -> 200 berisi vote beserta penggunanya."""
        r = self.panggil("get", self.url_film() + "/votes")
        self.assertEqual((r.status_code, r.json()[0]["user"]["name"]), (200, "Siswa"))

    def test_daftar_komentar_beserta_balasan_200(self):
        """GET /films/{id}/discussions -> 200, komentar utama memuat balasannya."""
        r = self.panggil("get", self.url_film() + "/discussions")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()[0]["replies"][0]["isi_pesan"], "Balasan komentar")

    def test_buat_film_201_status_pending(self):
        """POST /films dengan data lengkap -> 201, status awal pending, tersimpan di database."""
        r = self.panggil("post", "/api/films", self.isi_film(), self.creator)
        self.assertEqual((r.status_code, r.json()["status"]), (201, "pending"))
        self.assertTrue(Film.objects.filter(judul="Langit Terakhir di Kampus").exists())

    def test_ganti_film_put_200(self):
        """PUT /films/{id} dengan data lengkap -> 200."""
        r = self.panggil("put", self.url_film(), self.isi_film(judul="Judul Hasil PUT"), self.creator)
        self.assertEqual((r.status_code, r.json()["judul"]), (200, "Judul Hasil PUT"))

    def test_ubah_sebagian_patch_200(self):
        """PATCH /films/{id} hanya judul -> 200, field lain tidak berubah."""
        r = self.panggil("patch", self.url_film(), {"judul": "Judul Hasil PATCH"}, self.creator)
        self.assertEqual((r.status_code, r.json()["judul"], r.json()["tahun_karya"]), (200, "Judul Hasil PATCH", 2025))

    def test_hapus_film_204(self):
        """DELETE /films/{id} oleh pemiliknya -> 204 dan data hilang."""
        r = self.panggil("delete", self.url_film(self.film_pending), None, self.creator)
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Film.objects.filter(pk=self.film_pending.pk).exists())

    def test_admin_boleh_mengubah_film_orang_lain_200(self):
        """PATCH oleh Admin pada film milik Creator -> 200."""
        r = self.panggil("patch", self.url_film(), {"judul": "Diubah Admin"}, self.admin)
        self.assertEqual(r.status_code, 200)


# INPUT TIDAK VALID
class InputTidakValidTest(ApiTestCase):
    def test_body_tidak_valid_422(self):
        """POST dengan data salah -> 422 (field hilang, tipe salah, terlalu pendek, link bukan URL)."""
        kasus = {
            "judul tidak dikirim": {"judul": None},
            "tahun_karya berupa teks": {"tahun_karya": "dua ribu"},
            "judul 2 huruf": {"judul": "ab"},
            "sinopsis terlalu pendek": {"sinopsis": "pendek"},
            "link bukan URL": {"link_video_utama": "bukan-url"},
            "poster kosong": {"gambar_poster": ""},
        }
        for nama, ubah in kasus.items():
            with self.subTest(nama):
                r = self.panggil("post", "/api/films", self.isi_film(**ubah), self.creator)
                self.assertEqual(r.status_code, 422)
                self.assertEqual(r.json()["detail"], "Data yang dikirim tidak valid.")

    def test_url_lolos_schema_ditolak_model_422(self):
        """Link 'http://abc' lolos schema tetapi ditolak validasi model -> 422 dengan rincian."""
        r = self.panggil("post", "/api/films", self.isi_film(link_video_utama="http://abc"), self.creator)
        self.assertEqual(r.status_code, 422)
        self.assertIn("link_video_utama", r.json()["errors"])

    def test_id_di_url_bukan_angka_422(self):
        """GET /films/abc -> 422."""
        self.assertEqual(self.panggil("get", "/api/films/abc").status_code, 422)

    def test_put_tidak_lengkap_422(self):
        """PUT hanya berisi judul -> 422 karena PUT mewajibkan field lengkap."""
        r = self.panggil("put", self.url_film(), {"judul": "Hanya judul"}, self.creator)
        self.assertEqual(r.status_code, 422)

    def test_patch_judul_pendek_422(self):
        """PATCH dengan judul 2 huruf -> 422."""
        self.assertEqual(self.panggil("patch", self.url_film(), {"judul": "ab"}, self.creator).status_code, 422)

    def test_bukan_pemilik_tidak_boleh_ubah_dan_hapus_403(self):
        """PATCH dan DELETE oleh Creator lain -> 403; film tetap ada."""
        for metode, data in (("patch", {"judul": "Percobaan"}), ("delete", None)):
            with self.subTest(metode):
                self.assertEqual(self.panggil(metode, self.url_film(), data, self.creator_lain).status_code, 403)
        self.assertEqual(Film.objects.get(pk=self.film.pk).judul, "Film Published")

    def test_film_belum_published_tidak_bisa_dilihat_publik_403(self):
        """GET film pending oleh publik -> 403."""
        self.assertEqual(self.panggil("get", self.url_film(self.film_pending)).status_code, 403)


# DATA TIDAK DITEMUKAN
class DataTidakDitemukanTest(ApiTestCase):
    TIDAK_ADA = "/api/films/99999"

    def test_film_tidak_ada_404(self):
        """Semua endpoint film dengan ID yang tidak ada -> 404."""
        kasus = (("get", ""), ("get", "/votes"), ("get", "/discussions"),
                 ("patch", ""), ("put", ""), ("delete", ""))
        for metode, akhiran in kasus:
            with self.subTest(f"{metode.upper()} {akhiran or '/{id}'}"):
                data = self.isi_film() if metode == "put" else ({"judul": "Judul Baru"} if metode == "patch" else None)
                r = self.panggil(metode, self.TIDAK_ADA + akhiran, data, None if metode == "get" else self.admin)
                self.assertEqual(r.status_code, 404)

    def test_pesan_film_tidak_ditemukan(self):
        """GET /films/99999 -> 404 dengan pesan 'Film tidak ditemukan.'"""
        self.assertEqual(self.panggil("get", self.TIDAK_ADA).json()["detail"], "Film tidak ditemukan.")

    def test_buat_film_kategori_tidak_ada_404(self):
        """POST dengan category_id yang tidak ada -> 404 'Kategori tidak ditemukan.'"""
        r = self.panggil("post", "/api/films", self.isi_film(category_id=99999), self.creator)
        self.assertEqual((r.status_code, r.json()["detail"]), (404, "Kategori tidak ditemukan."))