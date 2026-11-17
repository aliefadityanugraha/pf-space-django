"""
Pengujian otomatis REST API
Run:  python manage.py test core -v 2

Kelompok pengujian:
  A. Input VALID            -> kode 200 / 201 / 204
  B. Input TIDAK VALID      -> kode 422 (dan 403 untuk aksi yang tidak diizinkan)
  C. Data TIDAK DITEMUKAN   -> kode 404
Setiap pengujian memakai database sementara, sehingga data aslimu tidak berubah.
"""

from django.test import TestCase
from .models import Category, Discussion, Film, User, Vote


class ApiTestCase(TestCase):
    """Menyiapkan data awal yang sama untuk semua pengujian."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin", email="admin@test.id", password="Rahasia123", name="Admin Guru", role=User.Role.ADMIN
        )
        cls.creator = User.objects.create_user(
            username="creator", email="creator@test.id", password="Rahasia123", name="Creator Satu", role=User.Role.CREATOR
        )
        cls.creator_lain = User.objects.create_user(
            username="creator2", email="creator2@test.id", password="Rahasia123", name="Creator Dua", role=User.Role.CREATOR
        )
        cls.siswa = User.objects.create_user(
            username="siswa", email="siswa@test.id", password="Rahasia123", name="Siswa Biasa", role=User.Role.USER
        )
        cls.kategori = Category.objects.create(name="Dokumenter")
        cls.kategori_lain = Category.objects.create(name="Animasi")

        data_film = dict(
            user=cls.creator,
            category=cls.kategori,
            sinopsis="Sinopsis film untuk pengujian API.",
            tahun_karya=2025,
            link_video_utama="https://www.youtube.com/watch?v=abc123",
            gambar_poster="films/posters/uji.jpg",
        )
        cls.film_published = Film.objects.create(judul="Film Published", status=Film.Status.PUBLISHED, **data_film)
        cls.film_pending = Film.objects.create(judul="Film Pending", status=Film.Status.PENDING, **data_film)

        Vote.objects.create(user=cls.siswa, film=cls.film_published)
        komentar = Discussion.objects.create(user=cls.siswa, film=cls.film_published, isi_pesan="Komentar utama")
        Discussion.objects.create(user=cls.creator, film=cls.film_published, parent=komentar, isi_pesan="Balasan komentar")

    def isi_film_valid(self, **ubah):
        """Body POST yang valid; field tertentu bisa diganti lewat argumen."""
        data = {
            "user_id": self.creator.id,
            "category_id": self.kategori.category_id,
            "judul": "Langit Terakhir di Kampus",
            "sinopsis": "Dokumenter singkat tentang hari terakhir siswa di sekolah.",
            "tahun_karya": 2025,
            "link_video_utama": "https://www.youtube.com/watch?v=xyz789",
            "gambar_poster": "films/posters/langit.jpg",
        }
        data.update(ubah)
        return data



# INPUT VALID

class InputValidTest(ApiTestCase):
    def test_daftar_kategori_200(self):
        """GET /categories -> 200 dan memuat kategori."""
        r = self.client.get("/api/categories")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 2)

    def test_daftar_film_hanya_yang_published_200(self):
        """GET /films -> 200, hanya film published (film pending tidak tampil)."""
        r = self.client.get("/api/films")
        self.assertEqual(r.status_code, 200)
        judul = [f["judul"] for f in r.json()]
        self.assertEqual(judul, ["Film Published"])

    def test_daftar_film_filter_kategori_200(self):
        """GET /films?category=animasi -> 200 dan kosong karena tidak ada film animasi."""
        r = self.client.get("/api/films", {"category": "animasi"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    def test_detail_film_memuat_data_berelasi_200(self):
        """GET /films/{id} -> 200 dengan pembuat, kategori, jumlah vote dan komentar."""
        r = self.client.get(f"/api/films/{self.film_published.film_id}")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["user"]["name"], "Creator Satu")
        self.assertEqual(data["category"]["name"], "Dokumenter")
        self.assertEqual(data["total_votes"], 1)
        self.assertEqual(data["total_discussions"], 2)

    def test_daftar_vote_film_200(self):
        """GET /films/{id}/votes -> 200 berisi data vote beserta penggunanya."""
        r = self.client.get(f"/api/films/{self.film_published.film_id}/votes")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()[0]["user"]["name"], "Siswa Biasa")

    def test_daftar_komentar_beserta_balasan_200(self):
        """GET /films/{id}/discussions -> 200, komentar utama memuat daftar balasan."""
        r = self.client.get(f"/api/films/{self.film_published.film_id}/discussions")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)
        self.assertEqual(r.json()[0]["replies"][0]["isi_pesan"], "Balasan komentar")

    def test_buat_film_201_status_pending(self):
        """POST /films dengan data lengkap -> 201, status awal pending, data tersimpan."""
        r = self.client.post("/api/films", self.isi_film_valid(), content_type="application/json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["status"], "pending")
        self.assertTrue(Film.objects.filter(judul="Langit Terakhir di Kampus").exists())

    def test_ganti_film_put_200(self):
        """PUT /films/{id} dengan data lengkap -> 200 dan data berubah."""
        data = self.isi_film_valid(judul="Judul Hasil PUT")
        data.pop("user_id")
        r = self.client.put(
            f"/api/films/{self.film_published.film_id}?user_id={self.creator.id}", data, content_type="application/json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["judul"], "Judul Hasil PUT")

    def test_ubah_sebagian_film_patch_200(self):
        """PATCH /films/{id} hanya judul -> 200, field lain tidak berubah."""
        r = self.client.patch(
            f"/api/films/{self.film_published.film_id}?user_id={self.creator.id}",
            {"judul": "Judul Hasil PATCH"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["judul"], "Judul Hasil PATCH")
        self.assertEqual(r.json()["tahun_karya"], 2025)

    def test_hapus_film_204(self):
        """DELETE /films/{id} oleh pemiliknya -> 204 dan data hilang dari database."""
        film_id = self.film_pending.film_id
        r = self.client.delete(f"/api/films/{film_id}?user_id={self.creator.id}")
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Film.objects.filter(pk=film_id).exists())

    def test_admin_boleh_mengubah_film_orang_lain_200(self):
        """PATCH oleh Admin pada film milik Creator -> 200."""
        r = self.client.patch(
            f"/api/films/{self.film_published.film_id}?user_id={self.admin.id}",
            {"judul": "Diubah Admin"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)


# =====================================================================
# B. INPUT TIDAK VALID
# =====================================================================

class InputTidakValidTest(ApiTestCase):
    def kirim_post(self, data):
        return self.client.post("/api/films", data, content_type="application/json")

    def test_field_wajib_tidak_dikirim_422(self):
        """POST tanpa field judul -> 422."""
        data = self.isi_film_valid()
        data.pop("judul")
        r = self.kirim_post(data)
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.json()["detail"], "Data yang dikirim tidak valid.")

    def test_tipe_data_salah_422(self):
        """POST dengan tahun_karya berupa teks -> 422."""
        self.assertEqual(self.kirim_post(self.isi_film_valid(tahun_karya="dua ribu")).status_code, 422)

    def test_judul_terlalu_pendek_422(self):
        """POST dengan judul 2 huruf -> 422."""
        self.assertEqual(self.kirim_post(self.isi_film_valid(judul="ab")).status_code, 422)

    def test_sinopsis_terlalu_pendek_422(self):
        """POST dengan sinopsis kurang dari 10 karakter -> 422."""
        self.assertEqual(self.kirim_post(self.isi_film_valid(sinopsis="pendek")).status_code, 422)

    def test_link_video_bukan_url_422(self):
        """POST dengan link_video_utama bukan URL -> 422 (ditolak schema)."""
        self.assertEqual(self.kirim_post(self.isi_film_valid(link_video_utama="bukan-url")).status_code, 422)

    def test_url_lolos_schema_tapi_ditolak_model_422(self):
        """Link 'http://abc' lolos schema tetapi ditolak validasi model -> 422 dengan rincian error."""
        r = self.kirim_post(self.isi_film_valid(link_video_utama="http://abc"))
        self.assertEqual(r.status_code, 422)
        self.assertIn("link_video_utama", r.json()["errors"])

    def test_id_di_url_bukan_angka_422(self):
        """GET /films/abc -> 422 karena film_id harus angka."""
        self.assertEqual(self.client.get("/api/films/abc").status_code, 422)

    def test_put_dengan_data_tidak_lengkap_422(self):
        """PUT hanya berisi judul -> 422 karena PUT mewajibkan field lengkap."""
        r = self.client.put(
            f"/api/films/{self.film_published.film_id}?user_id={self.creator.id}",
            {"judul": "Hanya judul"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 422)

    def test_patch_judul_terlalu_pendek_422(self):
        """PATCH dengan judul 2 huruf -> 422."""
        r = self.client.patch(
            f"/api/films/{self.film_published.film_id}?user_id={self.creator.id}",
            {"judul": "ab"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 422)

    def test_hapus_tanpa_user_id_422(self):
        """DELETE tanpa user_id -> 422."""
        self.assertEqual(self.client.delete(f"/api/films/{self.film_pending.film_id}").status_code, 422)

    def test_role_user_tidak_boleh_mengunggah_403(self):
        """POST oleh pengguna berrole USER -> 403."""
        self.assertEqual(self.kirim_post(self.isi_film_valid(user_id=self.siswa.id)).status_code, 403)

    def test_bukan_pemilik_tidak_boleh_mengubah_403(self):
        """PATCH oleh Creator lain (bukan pemilik) -> 403."""
        r = self.client.patch(
            f"/api/films/{self.film_published.film_id}?user_id={self.creator_lain.id}",
            {"judul": "Percobaan"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 403)

    def test_bukan_pemilik_tidak_boleh_menghapus_403(self):
        """DELETE oleh Creator lain -> 403 dan film tetap ada."""
        r = self.client.delete(f"/api/films/{self.film_published.film_id}?user_id={self.creator_lain.id}")
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Film.objects.filter(pk=self.film_published.film_id).exists())

    def test_film_belum_published_tidak_bisa_dilihat_publik_403(self):
        """GET film berstatus pending oleh publik -> 403."""
        self.assertEqual(self.client.get(f"/api/films/{self.film_pending.film_id}").status_code, 403)


# =====================================================================
# C. DATA TIDAK DITEMUKAN
# =====================================================================

class DataTidakDitemukanTest(ApiTestCase):
    ID_TIDAK_ADA = 99999

    def test_detail_film_tidak_ada_404(self):
        """GET /films/99999 -> 404 dengan pesan 'Film tidak ditemukan.'"""
        r = self.client.get(f"/api/films/{self.ID_TIDAK_ADA}")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["detail"], "Film tidak ditemukan.")

    def test_vote_film_tidak_ada_404(self):
        """GET /films/99999/votes -> 404."""
        self.assertEqual(self.client.get(f"/api/films/{self.ID_TIDAK_ADA}/votes").status_code, 404)

    def test_komentar_film_tidak_ada_404(self):
        """GET /films/99999/discussions -> 404."""
        self.assertEqual(self.client.get(f"/api/films/{self.ID_TIDAK_ADA}/discussions").status_code, 404)

    def test_buat_film_kategori_tidak_ada_404(self):
        """POST dengan category_id yang tidak ada -> 404 'Kategori tidak ditemukan.'"""
        r = self.client.post(
            "/api/films", self.isi_film_valid(category_id=self.ID_TIDAK_ADA), content_type="application/json"
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["detail"], "Kategori tidak ditemukan.")

    def test_buat_film_pengguna_tidak_ada_404(self):
        """POST dengan user_id yang tidak ada -> 404 'Pengguna tidak ditemukan.'"""
        r = self.client.post(
            "/api/films", self.isi_film_valid(user_id=self.ID_TIDAK_ADA), content_type="application/json"
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["detail"], "Pengguna tidak ditemukan.")

    def test_patch_film_tidak_ada_404(self):
        """PATCH /films/99999 -> 404."""
        r = self.client.patch(
            f"/api/films/{self.ID_TIDAK_ADA}?user_id={self.admin.id}", {"judul": "Judul Baru"}, content_type="application/json"
        )
        self.assertEqual(r.status_code, 404)

    def test_put_film_tidak_ada_404(self):
        """PUT /films/99999 dengan data lengkap -> 404."""
        data = self.isi_film_valid()
        data.pop("user_id")
        r = self.client.put(
            f"/api/films/{self.ID_TIDAK_ADA}?user_id={self.admin.id}", data, content_type="application/json"
        )
        self.assertEqual(r.status_code, 404)

    def test_hapus_film_tidak_ada_404(self):
        """DELETE /films/99999 -> 404."""
        r = self.client.delete(f"/api/films/{self.ID_TIDAK_ADA}?user_id={self.admin.id}")
        self.assertEqual(r.status_code, 404)