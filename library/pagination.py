"""
Classes de paginação.

Sem paginação, uma listagem com milhares de registros seria devolvida de uma
vez só, deixando a API lenta. Paginar é dividir o resultado em "páginas".
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Paginação padrão do projeto, por número de página.

    Exemplos de uso:
        GET /api/books/                       -> página 1, 10 itens
        GET /api/books/?page=2                -> página 2
        GET /api/books/?page=2&page_size=20   -> página 2, 20 itens por página

    A resposta tem sempre o formato:
        {"count": 42, "next": "<url>|null", "previous": "<url>|null", "results": [...]}
    """

    page_size = 10  # tamanho padrão da página
    page_size_query_param = "page_size"  # nome do parâmetro que o cliente usa
    max_page_size = 50  # limite: ?page_size=1000 será reduzido para 50
