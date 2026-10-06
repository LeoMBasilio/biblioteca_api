"""
Rotas do app `library` (todas sob o prefixo /api/, definido em config/urls.py).
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuthorViewSet,
    BookViewSet,
    LoanViewSet,
    LoginView,
    LogoutView,
    RefreshView,
    RegisterView,
)

# O router cria automaticamente as rotas de lista/detalhe/actions de cada
# ViewSet. `basename` é o prefixo usado nos nomes internos das rotas.
router = DefaultRouter()
router.register("authors", AuthorViewSet, basename="author")
router.register("books", BookViewSet, basename="book")
router.register("loans", LoanViewSet, basename="loan")

urlpatterns = [
    # --- Autenticação (views comuns, registradas manualmente) ---------------
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", LoginView.as_view(), name="token-obtain"),
    path("auth/token/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    # --- Rotas geradas pelo router -------------------------------------------
    path("", include(router.urls)),
]
