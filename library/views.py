"""
Views da API.

Uma view recebe a requisição HTTP e devolve a resposta. Aqui usamos:
    - ViewSets: agrupam as operações de um recurso (listar, criar, editar...).
    - Routers (library/urls.py): geram as URLs a partir dos ViewSets.
    - @extend_schema: enriquece a documentação Swagger de cada endpoint.
"""
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .filters import BookFilter
from .models import Author, Book, Loan
from .permissions import IsAdminOrReadOnly, IsOwner
from .serializers import (
    AuthorSerializer,
    BookSerializer,
    ErrorSerializer,
    LoanSerializer,
    LogoutSerializer,
    RegisterSerializer,
)
from .services import borrow_book, return_loan

# Respostas de erro reutilizadas na documentação das actions.
UNAUTHORIZED = OpenApiResponse(
    response=ErrorSerializer, description="Token ausente, inválido ou expirado."
)


# ===========================================================================
# AUTENTICAÇÃO
# ===========================================================================
@extend_schema(
    tags=["Auth"],
    summary="Cadastra um novo usuário",
    auth=[],  # endpoint público: não mostra o cadeado no Swagger
)
class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ - cria um usuário comum."""

    serializer_class = RegisterSerializer
    # Esta view é pública, então liberamos o acesso (o padrão exige login)...
    permission_classes = [AllowAny]
    # ...e desligamos a autenticação para que um token inválido enviado por
    # engano não faça o cadastro falhar com 401.
    authentication_classes = []


@extend_schema(
    tags=["Auth"],
    summary="Login: obtém o access e o refresh token",
    auth=[],
)
class LoginView(TokenObtainPairView):
    """POST /api/auth/token/ - recebe username e password, devolve os tokens.

    Reaproveitamos a view pronta do simplejwt; criamos a subclasse apenas para
    colocar a documentação (tag e resumo) no Swagger.
    """


@extend_schema(
    tags=["Auth"],
    summary="Renova o access token",
    auth=[],
)
class RefreshView(TokenRefreshView):
    """POST /api/auth/token/refresh/ - troca um refresh válido por novos tokens.

    Com ROTATE_REFRESH_TOKENS=True a resposta traz também um novo `refresh`,
    e o anterior vai para a blacklist.
    """


@extend_schema(
    tags=["Auth"],
    summary="Logout: invalida o refresh token",
    request=LogoutSerializer,
    responses={
        205: OpenApiResponse(description="Logout realizado. Sem conteúdo."),
        400: OpenApiResponse(response=ErrorSerializer, description="Refresh token inválido."),
        401: UNAUTHORIZED,
    },
)
class LogoutView(APIView):
    """POST /api/auth/logout/ - coloca o refresh token na blacklist.

    Depois disso o refresh não pode mais gerar access tokens. O access token
    atual continua válido até expirar (no máximo 15 minutos), pois JWT não é
    guardado no servidor.
    """

    # Sem permission_classes: herda IsAuthenticated, ou seja, só quem está
    # logado consegue fazer logout.

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # 400 se faltar o campo
        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            return Response(
                {"detail": "Refresh token inválido ou já utilizado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # 205 Reset Content: a ação deu certo e não há corpo na resposta.
        return Response(status=status.HTTP_205_RESET_CONTENT)


# ===========================================================================
# AUTORES
# ===========================================================================
@extend_schema(tags=["Authors"])
class AuthorViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """GET /api/authors/ - lista os autores (somente leitura).

    Usamos `ListModelMixin` + `GenericViewSet` em vez de `ModelViewSet`
    porque só precisamos da operação de listar.
    """

    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    # Sobrescreve a paginação global para praticar o segundo estilo:
    #   /api/authors/?limit=5&offset=10
    pagination_class = LimitOffsetPagination


# ===========================================================================
# LIVROS
# ===========================================================================
@extend_schema(tags=["Books"])
class BookViewSet(viewsets.ModelViewSet):
    """CRUD de livros.

    Rotas geradas pelo router:
        GET    /api/books/              lista (paginada, com busca e filtros)
        POST   /api/books/              cria (admin)
        GET    /api/books/{id}/         detalhe
        PUT    /api/books/{id}/         substitui (admin)
        PATCH  /api/books/{id}/         altera parcialmente (admin)
        DELETE /api/books/{id}/         remove (admin)
        POST   /api/books/{id}/borrow/  empresta o livro
    """

    # select_related("author") faz um JOIN e evita uma consulta extra por livro
    # ao serializar o nome do autor (o clássico problema "N+1").
    queryset = Book.objects.select_related("author")
    serializer_class = BookSerializer

    # --- Busca, filtros e ordenação ----------------------------------------
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BookFilter  # ?available=true  ?published_year=2020
    search_fields = ["title", "author__name"]  # ?search=machado
    ordering_fields = ["title", "created_at", "published_year"]  # ?ordering=-created_at

    def get_permissions(self):
        """Escolhe as permissões de acordo com a action atual."""
        if self.action == "borrow":
            # Qualquer usuário logado pode emprestar.
            return [IsAuthenticated()]
        # Demais actions: leitura para logados, escrita só para admin.
        return [IsAdminOrReadOnly()]

    @extend_schema(
        summary="Empresta o livro ao usuário logado",
        description=(
            "Cria um empréstimo com prazo de 14 dias e marca o livro como "
            "indisponível. Não precisa de corpo na requisição.\n\n"
            "Regras: o livro deve estar disponível e o usuário pode ter, no "
            "máximo, 3 empréstimos ativos."
        ),
        request=None,  # esta action não recebe corpo
        responses={
            201: LoanSerializer,
            400: OpenApiResponse(
                response=ErrorSerializer,
                description="Livro indisponível ou limite de empréstimos atingido.",
            ),
            401: UNAUTHORIZED,
            404: OpenApiResponse(response=ErrorSerializer, description="Livro não encontrado."),
        },
        examples=[
            OpenApiExample(
                "Empréstimo criado",
                value={
                    "id": 7,
                    "book": 3,
                    "book_title": "Dom Casmurro",
                    "loaned_at": "2026-10-01T14:30:00-03:00",
                    "due_date": "2026-10-15",
                    "returned_at": None,
                    "is_active": True,
                },
                response_only=True,
                status_codes=["201"],
            ),
            OpenApiExample(
                "Livro indisponível",
                value={"detail": "Este livro não está disponível."},
                response_only=True,
                status_codes=["400"],
            ),
        ],
    )
    @action(detail=True, methods=["post"])
    def borrow(self, request, pk=None):
        """POST /api/books/{id}/borrow/"""
        # Toda a regra de negócio está em services.py; a view só traduz o
        # resultado para HTTP.
        loan = borrow_book(book_id=pk, user=request.user)
        return Response(LoanSerializer(loan).data, status=status.HTTP_201_CREATED)


# ===========================================================================
# EMPRÉSTIMOS
# ===========================================================================
@extend_schema(tags=["Loans"])
class LoanViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Empréstimos do usuário logado.

    GET  /api/loans/             lista os empréstimos do usuário
    POST /api/loans/{id}/return/ devolve o livro
    """

    # Este queryset NÃO é usado nas requisições (o get_queryset abaixo o
    # substitui). Ele existe só para o drf-spectacular descobrir o model e o
    # tipo do {id} ao gerar o Swagger, sem precisar de um usuário logado.
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    # IsAuthenticated: precisa estar logado. IsOwner: só mexe no que é dele.
    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        """Devolve SOMENTE os empréstimos do usuário logado.

        Este é o ponto-chave da segurança: como o queryset já vem filtrado,
        o usuário A nunca enxerga (nem alcança pelo ID) os empréstimos do B.
        Pedir o ID de outra pessoa resulta em 404, não em 403, o que também
        evita revelar que aquele empréstimo existe.
        """
        return Loan.objects.filter(user=self.request.user).select_related("book")

    @extend_schema(
        summary="Devolve o livro",
        description=(
            "Preenche `returned_at` e marca o livro como disponível novamente. "
            "Só o dono do empréstimo pode devolvê-lo."
        ),
        request=None,
        responses={
            200: LoanSerializer,
            400: OpenApiResponse(
                response=ErrorSerializer, description="Empréstimo já devolvido."
            ),
            401: UNAUTHORIZED,
            403: OpenApiResponse(response=ErrorSerializer, description="Sem permissão."),
            404: OpenApiResponse(
                response=ErrorSerializer,
                description="Empréstimo não encontrado (ou pertence a outro usuário).",
            ),
        },
        examples=[
            OpenApiExample(
                "Devolução registrada",
                value={
                    "id": 7,
                    "book": 3,
                    "book_title": "Dom Casmurro",
                    "loaned_at": "2026-10-01T14:30:00-03:00",
                    "due_date": "2026-10-15",
                    "returned_at": "2026-10-05T09:12:00-03:00",
                    "is_active": False,
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    # `return` é palavra reservada do Python, então o método tem outro nome e
    # url_path define que a rota continua sendo /return/.
    @action(detail=True, methods=["post"], url_path="return", url_name="return")
    def return_loan(self, request, pk=None):
        """POST /api/loans/{id}/return/"""
        # get_object() usa get_queryset() (já filtrado pelo usuário) e depois
        # executa IsOwner.has_object_permission.
        loan = self.get_object()
        loan = return_loan(loan=loan)
        return Response(LoanSerializer(loan).data)
