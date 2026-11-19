from typing import Any, Optional, Tuple
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Count, Prefetch, QuerySet
from django.shortcuts import get_object_or_404
from django.utils.text import slugify

from .models import Category, Discussion, Film, User, Vote


# SERVICE UNTUK TABEL USER (users)

@transaction.atomic
def register_user(
    *,
    name: str,
    email: str,
    username: str,
    password: str,
    role: str = User.Role.USER,
) -> User:
    """Mendaftarkan pengguna baru dengan password yang di-hash."""
    if User.objects.filter(email=email).exists():
        raise ValidationError("Email sudah terdaftar.")
    if User.objects.filter(username=username).exists():
        raise ValidationError("Username sudah digunakan.")

    user = User(
        name=name,
        email=email,
        username=username,
        role=role,
    )
    user.set_password(password)
    user.full_clean()
    user.save()
    return user


def get_all_users() -> QuerySet[User]:
    """Mengambil seluruh daftar pengguna."""
    return User.objects.all().order_by('-created_at')


@transaction.atomic
def update_user_role(*, admin_user: User, target_user_id: int, new_role: str) -> User:
    """Mengubah role pengguna (khusus Admin)."""
    if admin_user.role != User.Role.ADMIN and not admin_user.is_superuser:
        raise PermissionDenied("Hanya Admin yang dapat mengelola role pengguna.")

    if new_role not in User.Role.values:
        raise ValidationError(f"Role tidak valid. Pilihan: {', '.join(User.Role.values)}")

    target_user = get_object_or_404(User.objects.select_for_update(), pk=target_user_id)
    target_user.role = new_role
    target_user.save(update_fields=['role'])
    return target_user


@transaction.atomic
def delete_user(*, admin_user: User, target_user_id: int) -> None:
    """Menghapus akun pengguna (khusus Admin)."""
    if admin_user.role != User.Role.ADMIN and not admin_user.is_superuser:
        raise PermissionDenied("Hanya Admin yang dapat menghapus pengguna.")

    target_user = get_object_or_404(User, pk=target_user_id)
    target_user.delete()


# SERVICE UNTUK TABEL CATEGORY (categories)

@transaction.atomic
def create_category(*, admin_user: User, name: str) -> Category:
    """Membuat kategori film baru dengan slug otomatis (khusus Admin)."""
    if admin_user.role != User.Role.ADMIN and not admin_user.is_superuser:
        raise PermissionDenied("Hanya Admin yang dapat menambahkan kategori.")

    category = Category(name=name)
    category.full_clean()
    category.save()
    return category


def get_all_categories() -> QuerySet[Category]:
    """Mengambil semua kategori beserta jumlah film yang published di dalamnya."""
    return Category.objects.annotate(
        total_films=Count('films', distinct=True)
    ).order_by('name')


@transaction.atomic
def update_category(*, admin_user: User, category_id: int, name: str) -> Category:
    """Memperbarui nama dan slug kategori (khusus Admin)."""
    if admin_user.role != User.Role.ADMIN and not admin_user.is_superuser:
        raise PermissionDenied("Hanya Admin yang dapat mengubah kategori.")

    category = get_object_or_404(Category.objects.select_for_update(), pk=category_id)
    category.name = name
    category.slug = slugify(name)
    category.full_clean()
    category.save(update_fields=['name', 'slug'])
    return category


@transaction.atomic
def delete_category(*, admin_user: User, category_id: int) -> None:
    """Menghapus kategori film (khusus Admin)."""
    if admin_user.role != User.Role.ADMIN and not admin_user.is_superuser:
        raise PermissionDenied("Hanya Admin yang dapat menghapus kategori.")

    category = get_object_or_404(Category, pk=category_id)
    category.delete()


# SERVICE UNTUK TABEL FILM (films)

@transaction.atomic
def create_film(
    *,
    user: User,
    category: Category,
    judul: str,
    sinopsis: str,
    tahun_karya: int,
    link_video_utama: str,
    gambar_poster: Any,
    file_naskah: Optional[Any] = None,
    file_storyboard: Optional[Any] = None,
    file_rab: Optional[Any] = None,
) -> Film:
    """
    Menyimpan karya film baru ke database dan otomatis mengatur status ke 'pending'.
    Hanya user dengan role CREATOR atau ADMIN yang diizinkan mengunggah karya.
    """
    if user.role not in (User.Role.CREATOR, User.Role.ADMIN):
        raise PermissionDenied("Hanya Creator atau Admin yang dapat mengunggah karya film.")

    film = Film(
        user=user,
        category=category,
        judul=judul,
        sinopsis=sinopsis,
        tahun_karya=tahun_karya,
        link_video_utama=link_video_utama,
        gambar_poster=gambar_poster,
        file_naskah=file_naskah,
        file_storyboard=file_storyboard,
        file_rab=file_rab,
        status=Film.Status.PENDING,
        rejection_reason=None,
    )
    film.full_clean()
    film.save()
    return film


def get_published_films(category_slug: Optional[str] = None) -> QuerySet[Film]:
    """
    Mengambil daftar film yang berstatus 'published' secara efisien.
    Menggunakan select_related untuk User (kreator) dan Category,
    serta prefetch_related untuk Vote dan Discussion guna mencegah N+1 query problem.
    """
    queryset = (
        Film.objects.filter(status=Film.Status.PUBLISHED)
        .select_related('user', 'category')
        .prefetch_related('votes', 'discussions__user')
        .annotate(
            total_votes=Count('votes', distinct=True),
            total_discussions=Count('discussions', distinct=True),
        )
        .order_by('-created_at')
    )

    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)

    return queryset


def get_film_detail(*, film_id: int, requesting_user: Optional[User] = None) -> Film:
    """
    Mengambil detail satu film beserta relasinya secara efisien.
    Film yang belum 'published' hanya bisa dilihat oleh Kreator pemiliknya atau Admin.
    """
    film = get_object_or_404(
        Film.objects.select_related('user', 'category')
        .prefetch_related('votes__user', 'discussions__user', 'discussions__replies__user')
        .annotate(
            total_votes=Count('votes', distinct=True),
            total_discussions=Count('discussions', distinct=True),
        ),
        pk=film_id,
    )

    if film.status != Film.Status.PUBLISHED:
        is_allowed = requesting_user and (
            requesting_user.role == User.Role.ADMIN
            or requesting_user.is_superuser
            or film.user_id == requesting_user.id
        )
        if not is_allowed:
            raise PermissionDenied("Karya film ini belum dipublikasikan.")

    return film


@transaction.atomic
def update_film(
    *,
    requesting_user: User,
    film_id: int,
    category: Optional[Category] = None,
    judul: Optional[str] = None,
    sinopsis: Optional[str] = None,
    tahun_karya: Optional[int] = None,
    link_video_utama: Optional[str] = None,
    gambar_poster: Optional[Any] = None,
    file_naskah: Optional[Any] = None,
    file_storyboard: Optional[Any] = None,
    file_rab: Optional[Any] = None,
) -> Film:
    """
    Memperbarui data karya film.
    Creator hanya dapat mengedit film miliknya sendiri, sedangkan Admin dapat mengedit semua film.
    """
    film = get_object_or_404(Film.objects.select_for_update(), pk=film_id)

    is_admin = requesting_user.role == User.Role.ADMIN or requesting_user.is_superuser
    is_owner = film.user_id == requesting_user.id and requesting_user.role == User.Role.CREATOR

    if not (is_admin or is_owner):
        raise PermissionDenied("Anda tidak memiliki hak akses untuk mengubah karya film ini.")

    if category is not None:
        film.category = category
    if judul is not None:
        film.judul = judul
    if sinopsis is not None:
        film.sinopsis = sinopsis
    if tahun_karya is not None:
        film.tahun_karya = tahun_karya
    if link_video_utama is not None:
        film.link_video_utama = link_video_utama
    if gambar_poster is not None:
        film.gambar_poster = gambar_poster
    if file_naskah is not None:
        film.file_naskah = file_naskah
    if file_storyboard is not None:
        film.file_storyboard = file_storyboard
    if file_rab is not None:
        film.file_rab = file_rab

    film.full_clean()
    film.save()
    return film


@transaction.atomic
def update_film_status(
    *,
    admin_user: User,
    film_id: int,
    new_status: str,
    rejection_reason: Optional[str] = None,
) -> Film:
    """
    Mengubah status validasi film menjadi 'published' atau 'rejected' (khusus Admin).
    Jika status diubah menjadi 'rejected', alasan penolakan (rejection_reason) wajib diisi.
    """
    if admin_user.role != User.Role.ADMIN and not admin_user.is_superuser:
        raise PermissionDenied("Hanya Admin (Guru) yang berhak memvalidasi status karya film.")

    valid_target_statuses = (Film.Status.PUBLISHED, Film.Status.REJECTED)
    if new_status not in valid_target_statuses:
        raise ValidationError(
            f"Status tujuan tidak valid. Pilih salah satu dari: {', '.join(valid_target_statuses)}."
        )

    if new_status == Film.Status.REJECTED and not (rejection_reason and rejection_reason.strip()):
        raise ValidationError("Alasan penolakan (rejection_reason) wajib diisi saat menolak karya.")

    film = get_object_or_404(Film.objects.select_for_update(), pk=film_id)
    film.status = new_status
    film.rejection_reason = (
        rejection_reason.strip() if new_status == Film.Status.REJECTED and rejection_reason else None
    )
    film.save(update_fields=['status', 'rejection_reason'])
    return film


@transaction.atomic
def delete_film(*, requesting_user: User, film_id: int) -> None:
    """
    Menghapus karya film beserta dokumen produksi fisiknya dari media storage.
    Creator hanya dapat menghapus film miliknya sendiri, sedangkan Admin dapat menghapus semua film.
    """
    film = get_object_or_404(Film.objects.select_for_update(), pk=film_id)

    is_admin = requesting_user.role == User.Role.ADMIN or requesting_user.is_superuser
    is_owner = film.user_id == requesting_user.id and requesting_user.role == User.Role.CREATOR

    if not (is_admin or is_owner):
        raise PermissionDenied("Anda tidak memiliki hak akses untuk menghapus karya film ini.")

    file_fields = [
        film.gambar_poster,
        film.file_naskah,
        film.file_storyboard,
        film.file_rab,
    ]

    film.delete()

    def _cleanup_files() -> None:
        for file_field in file_fields:
            if file_field and file_field.name:
                file_field.storage.delete(file_field.name)

    transaction.on_commit(_cleanup_files)



# SERVICE UNTUK TABEL VOTE (votes)

@transaction.atomic
def toggle_vote(*, user: User, film_id: int) -> Tuple[bool, int]:
    """
    Memproses aksi toggle vote oleh user pada sebuah film yang telah 'published'.
    - Jika vote belum ada, buat record Vote baru (return True).
    - Jika vote sudah ada untuk pasangan (user, film), hapus Vote tersebut (return False).

    Returns:
        Tuple[bool, int]: (is_voted, total_votes_terkini)
    """
    film = get_object_or_404(Film, pk=film_id, status=Film.Status.PUBLISHED)

    existing_vote = Vote.objects.select_for_update().filter(user=user, film=film).first()
    if existing_vote:
        existing_vote.delete()
        is_voted = False
    else:
        Vote.objects.create(user=user, film=film)
        is_voted = True

    total_votes = Vote.objects.filter(film=film).count()
    return is_voted, total_votes


def get_film_votes(*, film_id: int) -> QuerySet[Vote]:
    """Mengambil seluruh daftar vote pada sebuah film beserta data user-nya."""
    return (
        Vote.objects.filter(film_id=film_id)
        .select_related('user', 'film')
        .order_by('-created_at')
    )


# SERVICE UNTUK TABEL DISCUSSION (discussions)

@transaction.atomic
def create_discussion(
    *,
    user: User,
    film_id: int,
    isi_pesan: str,
    parent_id: Optional[int] = None,
) -> Discussion:
    """
    Menambahkan komentar baru atau balasan komentar (relasi rekursif via parent_id)
    pada film yang berstatus 'published'.
    """
    film = get_object_or_404(Film, pk=film_id, status=Film.Status.PUBLISHED)

    parent_discussion = None
    if parent_id is not None:
        parent_discussion = get_object_or_404(Discussion, pk=parent_id, film=film)

    discussion = Discussion(
        user=user,
        film=film,
        parent=parent_discussion,
        isi_pesan=isi_pesan.strip(),
    )
    discussion.full_clean()
    discussion.save()
    return discussion


def get_film_discussions(*, film_id: int) -> QuerySet[Discussion]:
    """
    Mengambil daftar komentar utama (top-level, parent=None) pada sebuah film,
    lengkap dengan prefetch balasan (replies) dan user pembuatnya agar bebas N+1 query.
    """
    replies_queryset = Discussion.objects.select_related('user').order_by('created_at')
    return (
        Discussion.objects.filter(film_id=film_id, parent__isnull=True)
        .select_related('user', 'film')
        .prefetch_related(Prefetch('replies', queryset=replies_queryset))
        .order_by('created_at')
    )


@transaction.atomic
def update_discussion(*, requesting_user: User, diskusi_id: int, isi_pesan: str) -> Discussion:
    """Mengubah isi komentar (hanya pemilik komentar yang dapat mengedit)."""
    discussion = get_object_or_404(Discussion.objects.select_for_update(), pk=diskusi_id)

    if discussion.user_id != requesting_user.id:
        raise PermissionDenied("Anda hanya dapat mengubah komentar milik Anda sendiri.")

    discussion.isi_pesan = isi_pesan.strip()
    discussion.full_clean()
    discussion.save(update_fields=['isi_pesan'])
    return discussion


@transaction.atomic
def delete_discussion(*, requesting_user: User, diskusi_id: int) -> None:
    """Menghapus komentar beserta balasannya (pemilik komentar atau Admin)."""
    discussion = get_object_or_404(Discussion.objects.select_for_update(), pk=diskusi_id)

    is_admin = requesting_user.role == User.Role.ADMIN or requesting_user.is_superuser
    is_owner = discussion.user_id == requesting_user.id

    if not (is_admin or is_owner):
        raise PermissionDenied("Anda tidak memiliki hak akses untuk menghapus komentar ini.")

    discussion.delete()
