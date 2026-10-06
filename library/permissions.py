"""
Permissões customizadas.

Uma permission responde à pergunta: "este usuário PODE fazer isto?".
Se retornar False, o DRF responde 403 (ou 401 se o usuário não está logado).
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwner(BasePermission):
    """Só o dono do objeto pode acessá-lo (usada nos empréstimos).

    `has_object_permission` é chamado quando a view busca UM objeto, por
    exemplo ao usar `self.get_object()`. Ele NÃO roda em listagens, por isso
    o `LoanViewSet` também filtra o queryset pelo usuário logado.
    """

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id


class IsAdminOrReadOnly(BasePermission):
    """Qualquer usuário logado LÊ; só administradores (is_staff) ESCREVEM.

    SAFE_METHODS são os métodos que não alteram dados: GET, HEAD e OPTIONS.
    """

    def has_permission(self, request, view):
        # Primeiro exige estar autenticado.
        if not (request.user and request.user.is_authenticated):
            return False
        # Leitura liberada para todo usuário logado.
        if request.method in SAFE_METHODS:
            return True
        # Escrita (POST, PUT, PATCH, DELETE) somente para administradores.
        return request.user.is_staff
