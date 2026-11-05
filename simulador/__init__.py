"""Simulador Vivero — app web Flask."""
from flask import Flask

from .config import cargar_config, carpeta_datos
from .storage.cache import Cache

__version__ = "2.1.0"


def create_app(cfg: dict | None = None, ruta_db=None) -> Flask:
    app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
    app.config["SIM"] = cfg or cargar_config()
    app.config["CACHE"] = Cache(ruta_db or carpeta_datos() / "simulador_vivero.db")
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024   # CSV de hasta 20 MB

    from .web.routes import bp
    app.register_blueprint(bp)

    @app.template_filter("dec")
    def _dec(v, n=1):
        """Número con coma decimal (formato Uruguay); '–' si no hay dato."""
        return "–" if v is None else f"{v:.{n}f}".replace(".", ",")

    @app.context_processor
    def _version():
        return {"version": __version__}

    return app
