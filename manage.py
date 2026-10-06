#!/usr/bin/env python
"""Utilitário de linha de comando do Django.

É por aqui que rodamos todos os comandos do projeto, por exemplo:
    python manage.py runserver
    python manage.py migrate
    python manage.py test
"""
import os
import sys


def main():
    # Diz ao Django qual arquivo de configurações usar (config/settings.py).
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar o Django. Você ativou o ambiente virtual "
            "e instalou as dependências (pip install -r requirements.txt)?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
