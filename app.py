"""Punto de entrada web (compatibilidad con Render: `gunicorn app:app`).

Toda la lógica vive en el paquete `simulador/`. Para la versión de escritorio usar run_desktop.py.
"""
import os

from simulador import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True)
