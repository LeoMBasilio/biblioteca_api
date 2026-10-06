"""
Regras de negócio de empréstimo e devolução.

Manter essa lógica fora das views deixa o código mais limpo: a view cuida de
HTTP (requisição e resposta) e o "service" cuida das regras da biblioteca.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Book, Loan

User = get_user_model()


def borrow_book(*, book_id, user):
    """Empresta o livro `book_id` ao usuário `user`.

    Regras:
        - o livro precisa estar disponível;
        - o usuário não pode ter mais de LIBRARY_MAX_ACTIVE_LOANS ativos;
        - o prazo de devolução é hoje + LIBRARY_LOAN_DAYS dias;
        - o livro passa a ficar indisponível.

    Levanta ValidationError (HTTP 400) se alguma regra for violada e
    Http404 (HTTP 404) se o livro não existir.
    """
    # transaction.atomic(): tudo dentro do bloco é salvo junto OU nada é salvo.
    # Se qualquer exceção acontecer, o banco volta ao estado anterior. Assim
    # nunca teremos um Loan criado com o Book ainda marcado como disponível.
    with transaction.atomic():
        # select_for_update() trava a linha do livro até o fim da transação.
        # Se duas pessoas pedirem o mesmo livro ao mesmo tempo, a segunda
        # espera a primeira terminar e então enxerga available=False.
        # (O SQLite ignora essa trava; em PostgreSQL ela é efetiva.)
        book = get_object_or_404(Book.objects.select_for_update(), pk=book_id)

        # Trava também a linha do usuário, para que dois empréstimos
        # simultâneos dele não furem o limite de empréstimos ativos.
        User.objects.select_for_update().get(pk=user.pk)

        if not book.available:
            raise ValidationError({"detail": "Este livro não está disponível."})

        active_loans = Loan.objects.filter(user=user, returned_at__isnull=True).count()
        if active_loans >= settings.LIBRARY_MAX_ACTIVE_LOANS:
            raise ValidationError(
                {
                    "detail": (
                        f"Limite de {settings.LIBRARY_MAX_ACTIVE_LOANS} "
                        "empréstimos ativos atingido."
                    )
                }
            )

        loan = Loan.objects.create(
            book=book,
            user=user,
            due_date=timezone.localdate() + timedelta(days=settings.LIBRARY_LOAN_DAYS),
        )
        book.available = False
        book.save(update_fields=["available"])  # grava só a coluna alterada

    return loan


def return_loan(*, loan):
    """Registra a devolução do empréstimo `loan`.

    Preenche `returned_at` e devolve o livro à estante (available=True).
    Levanta ValidationError (HTTP 400) se o empréstimo já foi devolvido.
    """
    with transaction.atomic():
        # Relê o empréstimo já com a linha travada, para o caso de duas
        # devoluções simultâneas do mesmo empréstimo.
        loan = Loan.objects.select_for_update().get(pk=loan.pk)

        if loan.returned_at is not None:
            raise ValidationError({"detail": "Este empréstimo já foi devolvido."})

        loan.returned_at = timezone.now()
        loan.save(update_fields=["returned_at"])
        # .update() faz um UPDATE direto no banco, sem carregar o objeto.
        Book.objects.filter(pk=loan.book_id).update(available=True)

    return loan
