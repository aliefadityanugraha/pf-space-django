from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Category, Film, Vote, Discussion


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'name', 'email', 'username', 'role', 'is_active', 'is_staff', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'created_at')
    search_fields = ('name', 'email', 'username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informasi PF Space', {'fields': ('name', 'role', 'created_at')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informasi PF Space', {'fields': ('name', 'email', 'role')}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'name', 'slug')
    list_filter = ('name',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = (
        'film_id',
        'judul',
        'user',
        'category',
        'tahun_karya',
        'status',
        'created_at',
    )
    list_filter = ('status', 'category', 'tahun_karya', 'created_at')
    search_fields = ('judul', 'sinopsis', 'user__name', 'user__email', 'category__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('vote_id', 'user', 'film', 'created_at')
    list_filter = ('created_at', 'film__category')
    search_fields = ('user__name', 'user__email', 'film__judul')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ('diskusi_id', 'user', 'film', 'parent', 'created_at')
    list_filter = ('created_at', 'film__category')
    search_fields = ('isi_pesan', 'user__name', 'user__email', 'film__judul')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
