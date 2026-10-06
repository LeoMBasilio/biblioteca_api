"""
Rotas principais do projeto.

O Django percorre esta lista de cima para baixo até achar uma rota que combine
com a URL pedida. Cada `path()` associa um prefixo a uma view ou a outro
arquivo de rotas (include).
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Painel administrativo do Django (cadastro manual de livros, usuários...).
    path("admin/", admin.site.urls),
    # Todas as rotas de negócio ficam em library/urls.py, sob o prefixo /api/.
    path("api/", include("library.urls")),
    # --- Documentação -------------------------------------------------------
    # Schema OpenAPI em formato YAML/JSON (a "fonte" da documentação).
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Swagger UI: interface interativa para testar a API no navegador.
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # ReDoc: outra visualização do mesmo schema, mais voltada para leitura.
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
