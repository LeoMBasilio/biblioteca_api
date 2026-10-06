"""
Modelos (tabelas do banco de dados) da biblioteca.

Cada classe que herda de `models.Model` vira uma tabela, e cada atributo
vira uma coluna. Relacionamentos:

    Author 1 --- N Book 1 --- N Loan N --- 1 User
"""
from django.conf import settings
from django.db import models
from django.db.models import Q


class Author(models.Model):
    """Autor de livros."""

    name = models.CharField("nome", max_length=255)
    # null=True  -> o banco aceita NULL.
    # blank=True -> formulários/serializers aceitam o campo vazio.
    birth_date = models.DateField("data de nascimento", null=True, blank=True)
    bio = models.TextField("biografia", blank=True)

    class Meta:
        ordering = ["name"]  # ordenação padrão das consultas
        verbose_name = "autor"
        verbose_name_plural = "autores"

    def __str__(self):
        return self.name


class Book(models.Model):
    """Livro do catálogo."""

    title = models.CharField("título", max_length=255)
    # unique=True: o banco impede dois livros com o mesmo ISBN.
    isbn = models.CharField("ISBN", max_length=13, unique=True)
    # on_delete=PROTECT: não deixa apagar um autor que ainda tem livros.
    # related_name="books": permite usar `autor.books.all()`.
    author = models.ForeignKey(
        Author, on_delete=models.PROTECT, related_name="books", verbose_name="autor"
    )
    published_year = models.PositiveIntegerField("ano de publicação")
    # Indica se o livro está na estante. Quem altera esse campo é o serviço de
    # empréstimo/devolução (library/services.py), nunca o cliente diretamente.
    available = models.BooleanField("disponível", default=True)
    # auto_now_add=True: preenchido automaticamente na criação.
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "livro"
        verbose_name_plural = "livros"

    def __str__(self):
        return self.title


class Loan(models.Model):
    """Empréstimo de um livro a um usuário."""

    book = models.ForeignKey(
        Book, on_delete=models.PROTECT, related_name="loans", verbose_name="livro"
    )
    # settings.AUTH_USER_MODEL aponta para o modelo de usuário do projeto.
    # É a forma recomendada de referenciar o User.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loans",
        verbose_name="usuário",
    )
    loaned_at = models.DateTimeField("emprestado em", auto_now_add=True)
    due_date = models.DateField("devolver até")
    # Enquanto for NULL, o empréstimo está ATIVO (o livro ainda não voltou).
    returned_at = models.DateTimeField("devolvido em", null=True, blank=True)

    class Meta:
        ordering = ["-loaned_at"]  # mais recentes primeiro
        verbose_name = "empréstimo"
        verbose_name_plural = "empréstimos"
        constraints = [
            # Garante, no próprio banco, que um livro tenha NO MÁXIMO um
            # empréstimo ativo. É uma segunda linha de defesa contra duas
            # pessoas pegando o mesmo livro ao mesmo tempo.
            models.UniqueConstraint(
                fields=["book"],
                condition=Q(returned_at__isnull=True),
                name="unique_active_loan_per_book",
            )
        ]

    def __str__(self):
        return f"{self.book} -> {self.user}"

    @property
    def is_active(self):
        """True enquanto o livro não foi devolvido."""
        return self.returned_at is None
