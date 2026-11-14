from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = 'USER', 'User (Siswa/Umum)'
        CREATOR = 'CREATOR', 'Creator (Perwakilan Kelompok)'
        ADMIN = 'ADMIN', 'Admin (Guru)'

    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Menggunakan email sebagai kredensial login utama sesuai Skenario 1
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.email} - {self.role})"


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Film(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PUBLISHED = 'published', 'Published'
        REJECTED = 'rejected', 'Rejected'

    film_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_films',
        db_column='user_id',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='films',
        db_column='category_id',
    )
    judul = models.CharField(max_length=255)
    sinopsis = models.TextField()
    tahun_karya = models.PositiveSmallIntegerField()
    link_video_utama = models.URLField(max_length=500)

    # File & gambar produksi
    gambar_poster = models.FileField(upload_to='films/posters/')
    file_naskah = models.FileField(upload_to='films/scripts/', blank=True, null=True)
    file_storyboard = models.FileField(upload_to='films/storyboards/', blank=True, null=True)
    file_rab = models.FileField(upload_to='films/rab/', blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'films'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.judul} ({self.tahun_karya}) - {self.get_status_display()}"


class Vote(models.Model):
    vote_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='votes',
        db_column='user_id',
    )
    film = models.ForeignKey(
        Film,
        on_delete=models.CASCADE,
        related_name='votes',
        db_column='film_id',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'votes'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'film'],
                name='unique_user_film_vote',
            )
        ]

    def __str__(self):
        return f"Vote oleh {self.user.name} pada '{self.film.judul}'"


class Discussion(models.Model):
    diskusi_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discussions',
        db_column='user_id',
    )
    film = models.ForeignKey(
        Film,
        on_delete=models.CASCADE,
        related_name='discussions',
        db_column='film_id',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        db_column='parent_id',
    )
    isi_pesan = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'discussions'
        ordering = ['created_at']

    def __str__(self):
        prefix = f"Balasan ke #{self.parent_id}" if self.parent_id else "Komentar"
        return f"{prefix} oleh {self.user.name} di '{self.film.judul}'"
