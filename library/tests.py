"""
Testes automatizados da API.

Cada teste roda em um banco temporário e vazio, criado e apagado
automaticamente. Para executar:

    python manage.py test

Usamos `APITestCase`, que fornece `self.client`, um cliente HTTP de teste.
O método `setUp` roda ANTES de cada teste, preparando os dados.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Author, Book, Loan

User = get_user_model()

PASSWORD = "Senha@12345Forte"


class BaseTestCase(APITestCase):
    """Cria usuários e livros usados por todos os testes."""

    def setUp(self):
        self.user_a = User.objects.create_user("ana", password=PASSWORD)
        self.user_b = User.objects.create_user("bruno", password=PASSWORD)
        self.admin = User.objects.create_user("admin", password=PASSWORD, is_staff=True)
        self.author = Author.objects.create(name="Machado de Assis")
        self.book = self.make_book(1)

    def make_book(self, number, **extra):
        """Cria um livro com ISBN único a partir de um número."""
        data = {
            "title": f"Livro {number}",
            "isbn": f"{number:013d}",  # 13 dígitos, completado com zeros
            "author": self.author,
            "published_year": 2000 + number % 20,
        }
        data.update(extra)
        return Book.objects.create(**data)

    def login(self, user):
        """Autentica o cliente como `user`, sem passar pelo endpoint de login."""
        self.client.force_authenticate(user=user)


# ---------------------------------------------------------------------------
# Autenticação JWT
# ---------------------------------------------------------------------------
class AuthTests(BaseTestCase):
    def test_request_without_token_returns_401(self):
        """1. Acesso sem token retorna 401."""
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_returns_access_and_refresh(self):
        """2. Login retorna access e refresh."""
        response = self.client.post(
            "/api/auth/token/", {"username": "ana", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_wrong_password_returns_401(self):
        response = self.client.post(
            "/api/auth/token/", {"username": "ana", "password": "errada"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_opens_protected_endpoint(self):
        """O access obtido no login realmente autentica as próximas requisições."""
        tokens = self.client.post(
            "/api/auth/token/", {"username": "ana", "password": PASSWORD}
        ).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_refresh_returns_new_access(self):
        tokens = self.client.post(
            "/api/auth/token/", {"username": "ana", "password": PASSWORD}
        ).data
        response = self.client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_logout_blacklists_refresh_token(self):
        """Depois do logout, o refresh token não pode mais ser usado."""
        tokens = self.client.post(
            "/api/auth/token/", {"username": "ana", "password": PASSWORD}
        ).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        logout = self.client.post("/api/auth/logout/", {"refresh": tokens["refresh"]})
        self.assertEqual(logout.status_code, status.HTTP_205_RESET_CONTENT)

        # Tenta renovar com o refresh que acabou de ser invalidado.
        self.client.credentials()  # remove o header de autenticação
        renew = self.client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]})
        self.assertEqual(renew.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_creates_user(self):
        response = self.client.post(
            "/api/auth/register/",
            {"username": "novo", "email": "novo@example.com", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)  # senha nunca é devolvida
        self.assertTrue(User.objects.filter(username="novo").exists())

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            "/api/auth/register/", {"username": "fraco", "password": "123"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Permissões em livros
# ---------------------------------------------------------------------------
class BookPermissionTests(BaseTestCase):
    payload = {
        "title": "Novo Livro",
        "isbn": "9788535910663",
        "published_year": 2020,
    }

    def test_regular_user_cannot_create_book(self):
        """3a. Usuário comum não consegue criar livro (403)."""
        self.login(self.user_a)
        response = self.client.post("/api/books/", {**self.payload, "author": self.author.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_book(self):
        """3b. Admin consegue criar livro (201)."""
        self.login(self.admin)
        response = self.client.post("/api/books/", {**self.payload, "author": self.author.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["isbn"], "9788535910663")

    def test_regular_user_can_read_books(self):
        self.login(self.user_a)
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_isbn_returns_400(self):
        self.login(self.admin)
        response = self.client.post(
            "/api/books/", {**self.payload, "isbn": "123", "author": self.author.id}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_cannot_set_available_directly(self):
        """O campo `available` é somente leitura: o valor enviado é ignorado."""
        self.login(self.admin)
        response = self.client.post(
            "/api/books/",
            {**self.payload, "author": self.author.id, "available": False},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["available"])


# ---------------------------------------------------------------------------
# Empréstimo e devolução
# ---------------------------------------------------------------------------
class LoanTests(BaseTestCase):
    def borrow(self, book):
        return self.client.post(f"/api/books/{book.id}/borrow/")

    def test_borrow_marks_book_unavailable_and_sets_due_date(self):
        self.login(self.user_a)
        response = self.borrow(self.book)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.book.refresh_from_db()  # relê o livro do banco
        self.assertFalse(self.book.available)

        loan = Loan.objects.get(pk=response.data["id"])
        self.assertEqual(loan.due_date, timezone.localdate() + timedelta(days=14))
        self.assertIsNone(loan.returned_at)

    def test_borrow_unavailable_book_returns_400(self):
        """4. Empréstimo de livro indisponível retorna 400."""
        self.book.available = False
        self.book.save()
        self.login(self.user_a)
        response = self.borrow(self.book)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_borrow_unknown_book_returns_404(self):
        self.login(self.user_a)
        response = self.client.post("/api/books/99999/borrow/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_limit_of_three_active_loans(self):
        """5. O limite de 3 empréstimos ativos é respeitado."""
        books = [self.book] + [self.make_book(n) for n in (2, 3, 4)]
        self.login(self.user_a)

        for book in books[:3]:
            self.assertEqual(self.borrow(book).status_code, status.HTTP_201_CREATED)

        # O quarto empréstimo deve ser recusado...
        self.assertEqual(self.borrow(books[3]).status_code, status.HTTP_400_BAD_REQUEST)

        # ...mas, ao devolver um, o usuário volta a poder emprestar.
        first_loan = Loan.objects.filter(user=self.user_a).first()
        self.client.post(f"/api/loans/{first_loan.id}/return/")
        self.assertEqual(self.borrow(books[3]).status_code, status.HTTP_201_CREATED)

    def test_return_makes_book_available_again(self):
        self.login(self.user_a)
        loan_id = self.borrow(self.book).data["id"]

        response = self.client.post(f"/api/loans/{loan_id}/return/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_active"])

        self.book.refresh_from_db()
        self.assertTrue(self.book.available)

    def test_return_twice_returns_400(self):
        self.login(self.user_a)
        loan_id = self.borrow(self.book).data["id"]
        self.client.post(f"/api/loans/{loan_id}/return/")
        response = self.client.post(f"/api/loans/{loan_id}/return/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_only_sees_own_loans(self):
        """6. O usuário A não enxerga os empréstimos do usuário B."""
        other_book = self.make_book(2)
        self.login(self.user_a)
        self.borrow(self.book)
        self.login(self.user_b)
        self.borrow(other_book)

        # A lista de A tem apenas o empréstimo de A.
        self.login(self.user_a)
        response = self.client.get("/api/loans/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["book"], self.book.id)

    def test_user_cannot_return_someone_elses_loan(self):
        """Devolver o empréstimo de outra pessoa resulta em 404."""
        self.login(self.user_a)
        loan_id = self.borrow(self.book).data["id"]

        self.login(self.user_b)
        response = self.client.post(f"/api/loans/{loan_id}/return/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # E o livro continua emprestado.
        self.book.refresh_from_db()
        self.assertFalse(self.book.available)


# ---------------------------------------------------------------------------
# Paginação, busca, filtros e ordenação
# ---------------------------------------------------------------------------
class PaginationAndFilterTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Com o livro criado no setUp da classe base, são 25 livros no total.
        for n in range(2, 26):
            self.make_book(n)
        self.login(self.user_a)

    def test_default_pagination_has_expected_shape(self):
        """7. A paginação retorna count, next, previous e results."""
        response = self.client.get("/api/books/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ("count", "next", "previous", "results"):
            self.assertIn(key, response.data)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 10)  # tamanho padrão
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_second_and_last_pages(self):
        page3 = self.client.get("/api/books/?page=3")
        self.assertEqual(len(page3.data["results"]), 5)  # 25 = 10 + 10 + 5
        self.assertIsNone(page3.data["next"])

    def test_custom_page_size(self):
        response = self.client.get("/api/books/?page_size=20")
        self.assertEqual(len(response.data["results"]), 20)

    def test_page_size_is_capped_at_50(self):
        for n in range(26, 61):  # total de 60 livros
            self.make_book(n)
        response = self.client.get("/api/books/?page_size=1000")
        self.assertEqual(len(response.data["results"]), 50)

    def test_invalid_page_returns_404(self):
        response = self.client.get("/api/books/?page=99")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authors_use_limit_offset_pagination(self):
        for n in range(10):
            Author.objects.create(name=f"Autor {n:02d}")
        response = self.client.get("/api/authors/?limit=4&offset=2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 4)
        self.assertEqual(response.data["count"], 11)  # 10 criados + o do setUp

    def test_filter_by_available(self):
        Book.objects.filter(pk__in=[1, 2, 3]).update(available=False)
        response = self.client.get("/api/books/?available=false&page_size=50")
        self.assertEqual(response.data["count"], 3)

    def test_filter_by_published_year(self):
        response = self.client.get("/api/books/?published_year=2005&page_size=50")
        for book in response.data["results"]:
            self.assertEqual(book["published_year"], 2005)

    def test_search_by_title_and_author(self):
        other = Author.objects.create(name="Clarice Lispector")
        self.make_book(100, title="A Hora da Estrela", author=other)

        by_title = self.client.get("/api/books/?search=Estrela")
        self.assertEqual(by_title.data["count"], 1)

        by_author = self.client.get("/api/books/?search=Clarice")
        self.assertEqual(by_author.data["count"], 1)

    def test_ordering(self):
        asc = self.client.get("/api/books/?ordering=title&page_size=50")
        desc = self.client.get("/api/books/?ordering=-title&page_size=50")
        titles_asc = [b["title"] for b in asc.data["results"]]
        titles_desc = [b["title"] for b in desc.data["results"]]
        self.assertEqual(titles_asc, sorted(titles_asc))
        self.assertEqual(titles_desc, sorted(titles_desc, reverse=True))


# ---------------------------------------------------------------------------
# Documentação
# ---------------------------------------------------------------------------
class DocsTests(BaseTestCase):
    def test_docs_are_public(self):
        """Schema, Swagger e ReDoc abrem sem login."""
        for url in ("/api/schema/", "/api/docs/", "/api/redoc/"):
            self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK, url)
