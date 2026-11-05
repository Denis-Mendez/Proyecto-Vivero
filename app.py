"""Punto de entrada web (PythonAnywhere: `from app import app as application`; gunicorn: `app:app`).

Toda la lógica vive en el paquete `simulador/`. Para desarrollo local: python app.py
"""
import os

from simulador import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
