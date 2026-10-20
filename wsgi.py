"""Production WSGI entry point. Requires explicit secrets and a prepared database."""
from app import create_app

app = create_app('production')
