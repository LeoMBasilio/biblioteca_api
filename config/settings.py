"""
Configurações do projeto "Biblioteca API".

Este arquivo concentra tudo que o Django, o DRF, o JWT e o Swagger precisam
saber para funcionar. Os trechos mais importantes para a aula são:

    1. INSTALLED_APPS          -> quais apps estão ativos
    2. REST_FRAMEWORK          -> autenticação, permissões e paginação padrão
    3. SIMPLE_JWT              -> validade e comportamento dos tokens
    4. SPECTACULAR_SETTINGS    -> informações da documentação Swagger
    5. LIBRARY_*               -> regras de negócio configuráveis da biblioteca
"""
import os
from datetime import timedelta
from pathlib import Path

# Pasta raiz do projeto (a que contém o manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Segurança
# ---------------------------------------------------------------------------
# Em produção, a SECRET_KEY NUNCA deve ficar escrita no código. Aqui lemos de
# uma variável de ambiente e usamos um valor inseguro apenas para estudo.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "chave-insegura-somente-para-estudo")

# DEBUG=True mostra páginas de erro detalhadas. Nunca use True em produção.
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---------------------------------------------------------------------------
# Apps instalados
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    # Apps padrão do Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Bibliotecas de terceiros
    "rest_framework",  # Django REST Framework (a API em si)
    # Habilita a "lista negra" de refresh tokens. É ela que permite invalidar
    # um token no logout. Cria tabelas no banco (rode o migrate).
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",  # Gera o schema OpenAPI e o Swagger UI
    "django_filters",  # Filtros por query string (?available=true)
    # Nosso app
    "library",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
# SQLite é um banco em arquivo, ideal para estudo. Para produção, troque por
# PostgreSQL (desafio extra do exercício).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Validadores usados ao cadastrar senhas (inclusive no endpoint de registro).
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internacionalização
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True  # Datas/horas são guardadas em UTC e convertidas na exibição.

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # Como o DRF descobre QUEM está fazendo a requisição.
    # Aqui: lendo o header "Authorization: Bearer <access_token>".
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # O que cada usuário PODE fazer. Por padrão, todo endpoint exige login.
    # Os endpoints públicos (registro e login) liberam isso explicitamente.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Paginação global: toda listagem usa esta classe, a menos que a view
    # defina outra (como fazemos em /api/authors/).
    "DEFAULT_PAGINATION_CLASS": "library.pagination.StandardPagination",
    # Faz o drf-spectacular gerar o schema OpenAPI a partir das views.
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ---------------------------------------------------------------------------
# JWT (djangorestframework-simplejwt)
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    # Access token: curto, porque não dá para "cancelar" um JWT já emitido.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    # Refresh token: longo, serve apenas para pedir novos access tokens.
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # A cada renovação, o servidor devolve também um NOVO refresh token...
    "ROTATE_REFRESH_TOKENS": True,
    # ...e coloca o refresh antigo na blacklist (não pode mais ser usado).
    "BLACKLIST_AFTER_ROTATION": True,
    # Prefixo esperado no header: "Authorization: Bearer <token>".
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Documentação (drf-spectacular)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Biblioteca API",
    "DESCRIPTION": (
        "API de uma biblioteca online, feita para estudo de Django REST Framework.\n\n"
        "**Como autenticar no Swagger:** use `POST /api/auth/register/` para criar "
        "um usuário e depois `POST /api/auth/token/` para obter o `access`. "
        "Clique em **Authorize** e cole o valor do `access`."
    ),
    "VERSION": "1.0.0",
    # Não mostra o próprio /api/schema/ dentro da documentação.
    "SERVE_INCLUDE_SCHEMA": False,
    # Descrição das tags (grupos) exibidas no Swagger.
    "TAGS": [
        {"name": "Auth", "description": "Cadastro, login, renovação de token e logout."},
        {"name": "Authors", "description": "Consulta de autores."},
        {"name": "Books", "description": "Catálogo de livros e empréstimo."},
        {"name": "Loans", "description": "Empréstimos do usuário logado."},
    ],
    # Mantém o token preenchido no Swagger mesmo após recarregar a página.
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": True},
}

# ---------------------------------------------------------------------------
# Regras de negócio da biblioteca (usadas em library/services.py)
# ---------------------------------------------------------------------------
LIBRARY_LOAN_DAYS = 14  # prazo de devolução, em dias
LIBRARY_MAX_ACTIVE_LOANS = 3  # máximo de empréstimos ativos por usuário
