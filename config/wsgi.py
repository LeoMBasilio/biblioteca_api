"""Ponto de entrada WSGI (usado por servidores como o gunicorn em produção)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
