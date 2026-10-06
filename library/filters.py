"""
Filtros da listagem de livros (django-filter).

Cada campo declarado vira um parâmetro de URL:
    ?available=true
    ?published_year=2020
"""
import django_filters

from .models import Book


class BookFilter(django_filters.FilterSet):
    class Meta:
        model = Book
        # Filtros por igualdade exata nesses campos.
        fields = ["available", "published_year"]
