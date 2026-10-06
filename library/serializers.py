"""
Serializers.

Um serializer faz duas coisas:
    1. Converte objetos do banco (models) em JSON para a resposta.
    2. Valida e converte o JSON recebido na requisição.

Funciona como um "formulário" para APIs.
"""
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Author, Book, Loan

User = get_user_model()


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
class RegisterSerializer(serializers.ModelSerializer):
    """Cadastro de novo usuário."""

    # write_only=True: a senha é aceita na entrada, mas NUNCA aparece na resposta.
    # validate_password aplica as regras de AUTH_PASSWORD_VALIDATORS.
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        # create_user faz o hash da senha. Nunca salve senha em texto puro
        # (ou seja, nunca use User.objects.create(password=...)).
        return User.objects.create_user(**validated_data)


class LogoutSerializer(serializers.Serializer):
    """Corpo esperado no logout: o refresh token a ser invalidado."""

    refresh = serializers.CharField()


class ErrorSerializer(serializers.Serializer):
    """Formato das mensagens de erro. Usado apenas na documentação Swagger."""

    detail = serializers.CharField()


# ---------------------------------------------------------------------------
# Autores e livros
# ---------------------------------------------------------------------------
class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name", "birth_date", "bio"]


class BookSerializer(serializers.ModelSerializer):
    # Campo extra, somente leitura, que mostra o nome do autor na resposta.
    # source="author.name" navega pelo relacionamento (livro -> autor -> nome).
    author_name = serializers.CharField(source="author.name", read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "isbn",
            "author",  # na escrita, recebe o ID do autor
            "author_name",
            "published_year",
            "available",
            "created_at",
        ]
        # `available` só muda via empréstimo/devolução, então o cliente não
        # pode enviá-lo ao criar ou editar um livro.
        read_only_fields = ["available", "created_at"]

    def validate_isbn(self, value):
        """Exige um ISBN com 10 ou 13 dígitos (somente números, sem hífens).

        Métodos `validate_<campo>` são chamados automaticamente pelo DRF,
        depois das validações automáticas do model (tamanho máximo, unicidade).
        """
        if not value.isdigit() or len(value) not in (10, 13):
            raise serializers.ValidationError("O ISBN deve ter 10 ou 13 dígitos numéricos.")
        return value

    def validate_published_year(self, value):
        """Impede anos absurdos (zero ou no futuro distante)."""
        if value < 1 or value > date.today().year + 1:
            raise serializers.ValidationError("Ano de publicação inválido.")
        return value


# ---------------------------------------------------------------------------
# Empréstimos
# ---------------------------------------------------------------------------
class LoanSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    # `is_active` é uma @property do model; aqui vira um campo booleano.
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            "id",
            "book",
            "book_title",
            "loaned_at",
            "due_date",
            "returned_at",
            "is_active",
        ]
        # Empréstimos são criados/alterados só pelas actions borrow e return.
        read_only_fields = fields
