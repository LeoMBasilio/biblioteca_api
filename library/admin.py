"""
Registro dos modelos no painel administrativo (http://localhost:8000/admin/).

O admin é útil para cadastrar dados de teste sem escrever código.
"""
from django.contrib import admin

from .models import Author, Book, Loan


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "birth_date")  # colunas da listagem
    search_fields = ("name",)  # caixa de busca


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "published_year", "available")
    list_filter = ("available", "published_year")  # filtros laterais
    search_fields = ("title", "isbn", "author__name")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("book", "user", "loaned_at", "due_date", "returned_at")
    list_filter = ("returned_at",)
