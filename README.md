# Biblioteca API (Django + DRF)

API REST de uma biblioteca online, usada como exemplo na aula de revisão.
Conceitos praticados: **autenticação JWT**, **paginação**, **filtros**,
**permissões**, **regras de negócio com transações** e **documentação Swagger**.

## Como instalar e executar

```bash
# 1. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Crie as tabelas do banco
python manage.py migrate

# 4. (Opcional) Popule com dados de exemplo
python manage.py seed_library

# 5. Suba o servidor
python manage.py runserver
```

O comando `seed_library` cria dois usuários (apenas para estudo):

| Usuário | Senha          | Perfil        |
|---------|----------------|---------------|
| `admin` | `Admin@12345`  | administrador |
| `aluno` | `Aluno@12345`  | usuário comum |

## Endereços úteis

| URL                                 | O que é                  |
|-------------------------------------|--------------------------|
| http://localhost:8000/api/docs/     | Swagger UI (interativo)  |
| http://localhost:8000/api/redoc/    | ReDoc                    |
| http://localhost:8000/api/schema/   | Schema OpenAPI           |
| http://localhost:8000/admin/        | Painel administrativo    |

## Endpoints

| Método                   | Rota                        | Acesso                               |
|--------------------------|-----------------------------|--------------------------------------|
| POST                     | `/api/auth/register/`       | Público                              |
| POST                     | `/api/auth/token/`          | Público                              |
| POST                     | `/api/auth/token/refresh/`  | Público                              |
| POST                     | `/api/auth/logout/`         | Autenticado                          |
| GET                      | `/api/authors/`             | Autenticado                          |
| GET, POST                | `/api/books/`               | Leitura: autenticado. Escrita: admin |
| GET, PUT, PATCH, DELETE  | `/api/books/{id}/`          | Leitura: autenticado. Escrita: admin |
| POST                     | `/api/books/{id}/borrow/`   | Autenticado                          |
| GET                      | `/api/loans/`               | Autenticado (apenas os próprios)     |
| POST                     | `/api/loans/{id}/return/`   | Dono do empréstimo                   |

## Testando pelo Swagger

1. Abra `/api/docs/` e use `POST /api/auth/token/` com `aluno` / `Aluno@12345`.
2. Copie o valor de `access` da resposta.
3. Clique em **Authorize** e cole o token.
4. Liste os livros em `GET /api/books/`.
5. Empreste um livro em `POST /api/books/{id}/borrow/`.
6. Veja seus empréstimos em `GET /api/loans/` e devolva com `POST /api/loans/{id}/return/`.

## Testando pelo terminal (curl)

```bash
# Login: guarda o access token em uma variável
ACCESS=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"aluno","password":"Aluno@12345"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

# Lista livros, 5 por página, ordenados por título
curl "http://localhost:8000/api/books/?page_size=5&ordering=title" \
  -H "Authorization: Bearer $ACCESS"

# Empresta o livro de id 1
curl -X POST http://localhost:8000/api/books/1/borrow/ \
  -H "Authorization: Bearer $ACCESS"
```

## Parâmetros de `GET /api/books/`

| Parâmetro        | Exemplo                  | Efeito                                  |
|------------------|--------------------------|-----------------------------------------|
| `search`         | `?search=machado`        | Busca no título ou no nome do autor     |
| `available`      | `?available=true`        | Filtra por disponibilidade              |
| `published_year` | `?published_year=1899`   | Filtra por ano                          |
| `ordering`       | `?ordering=-created_at`  | Ordena (`-` inverte). Aceita `title`, `created_at`, `published_year` |
| `page`           | `?page=2`                | Número da página                        |
| `page_size`      | `?page_size=20`          | Itens por página (padrão 10, máximo 50) |

`GET /api/authors/` usa outro estilo de paginação: `?limit=5&offset=10`.

## Testes e validação do schema

```bash
python manage.py test                                       # testes automatizados
python manage.py spectacular --validate --file schema.yml   # valida a documentação
```

## Mapa do código (leia nesta ordem)

| Arquivo                      | Conteúdo                                                        |
|------------------------------|-----------------------------------------------------------------|
| `config/settings.py`         | Configuração geral: DRF, JWT, Swagger e regras da biblioteca    |
| `config/urls.py`             | Rotas principais e rotas da documentação                        |
| `library/models.py`          | Tabelas: Author, Book e Loan                                    |
| `library/serializers.py`     | Validação de entrada e formato do JSON de saída                 |
| `library/permissions.py`     | `IsOwner` e `IsAdminOrReadOnly`                                 |
| `library/pagination.py`      | Paginação padrão (`page_size` até 50)                           |
| `library/filters.py`         | Filtros de livros                                               |
| `library/services.py`        | Regras de empréstimo e devolução (`transaction.atomic`)         |
| `library/views.py`           | ViewSets, autenticação e anotações do Swagger                   |
| `library/urls.py`            | Router e rotas de autenticação                                  |
| `library/tests.py`           | Testes automatizados                                            |
| `library/management/commands/seed_library.py` | Dados de exemplo                           |

## Variáveis de ambiente (opcionais)

| Variável               | Padrão                    | Uso                                     |
|------------------------|---------------------------|-----------------------------------------|
| `DJANGO_SECRET_KEY`    | chave insegura de estudo  | Chave secreta (obrigatória em produção) |
| `DJANGO_DEBUG`         | `True`                    | Use `False` em produção                 |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1`     | Hosts permitidos, separados por vírgula |

## Aviso

Este projeto é didático. As senhas do `seed_library` e a `SECRET_KEY` padrão
são públicas e **não devem ser usadas em produção**.
