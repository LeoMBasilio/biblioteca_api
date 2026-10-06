"""
Comando para popular o banco com dados de exemplo.

Uso:
    python manage.py seed_library

Cria 2 usuários (um admin e um comum), 5 autores e 11 livros, para que os
alunos tenham o que consultar e emprestar logo no primeiro uso.
É seguro rodar mais de uma vez: usa get_or_create e não duplica registros.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from library.models import Author, Book

# (nome, [(título, ISBN, ano), ...])
CATALOG = [
    ("Machado de Assis", [
        ("Dom Casmurro", "9788535910663", 1899),
        ("Memórias Póstumas de Brás Cubas", "9788535911664", 1881),
        ("Quincas Borba", "9788535912661", 1891),
    ]),
    ("Clarice Lispector", [
        ("A Hora da Estrela", "9788532508126", 1977),
        ("Laços de Família", "9788532508133", 1960),
    ]),
    ("Graciliano Ramos", [
        ("Vidas Secas", "9788501000118", 1938),
        ("São Bernardo", "9788501000125", 1934),
    ]),
    ("Jorge Amado", [
        ("Capitães da Areia", "9788535914849", 1937),
        ("Gabriela, Cravo e Canela", "9788535914856", 1958),
    ]),
    ("Carolina Maria de Jesus", [
        ("Quarto de Despejo", "9788508131075", 1960),
        ("Casa de Alvenaria", "9788508131082", 1961),
    ]),
]


class Command(BaseCommand):
    help = "Popula o banco com usuários, autores e livros de exemplo."

    def handle(self, *args, **options):
        User = get_user_model()

        # ATENÇÃO: senhas fixas servem apenas para a aula. Nunca faça isso
        # em um sistema real.
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "Admin@12345")
            self.stdout.write("Usuário admin criado (senha: Admin@12345).")
        if not User.objects.filter(username="aluno").exists():
            User.objects.create_user("aluno", "aluno@example.com", "Aluno@12345")
            self.stdout.write("Usuário aluno criado (senha: Aluno@12345).")

        for author_name, books in CATALOG:
            author, _ = Author.objects.get_or_create(name=author_name)
            for title, isbn, year in books:
                Book.objects.get_or_create(
                    isbn=isbn,
                    defaults={"title": title, "author": author, "published_year": year},
                )

        self.stdout.write(self.style.SUCCESS(
            f"Pronto: {Author.objects.count()} autores e {Book.objects.count()} livros."
        ))
