"""Configuración y carpeta de datos.

config.toml (opcional) y la base SQLite se guardan en la carpeta del proyecto.
Las API keys también pueden venir de variables de entorno (OPEN_METEO_API_KEY, METEOBLUE_API_KEY).
"""
import copy
import os
import tomllib
from pathlib import Path

DEFAULTS = {
    "proveedor": "open-meteo",          # "open-meteo" o "meteoblue"
    "open_meteo": {"api_key": "", "dias": 16},
    "meteoblue": {"api_key": ""},
    "red": {"proxy": "", "timeout_s": 15},
    "cache": {"vigencia_horas": 3},
    # Vivero Fray Bentos (MdP)
    "ubicacion": {"nombre": "Vivero Fray Bentos", "lat": -33.1295, "lon": -58.1924, "zoom": 16},
    "grados_dia": {                     # hipótesis sin validar — ver core/gdd.py
        "tb": 13.0,
        "tsup": 35.0,
        "alerta_diaria": 18.0,
        "alerta_dias_consecutivos": 3,
        "umbral_acumulado": 150.0,
    },
}


def carpeta_datos() -> Path:
    return Path(__file__).resolve().parent.parent


def _fusionar(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in extra.items():
        out[k] = _fusionar(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def cargar_config(ruta: Path | None = None) -> dict:
    ruta = ruta or carpeta_datos() / "config.toml"
    cfg = copy.deepcopy(DEFAULTS)
    if ruta.exists():
        with open(ruta, "rb") as f:
            cfg = _fusionar(DEFAULTS, tomllib.load(f))
    if os.environ.get("OPEN_METEO_API_KEY"):
        cfg["open_meteo"]["api_key"] = os.environ["OPEN_METEO_API_KEY"]
    if os.environ.get("METEOBLUE_API_KEY"):
        cfg["meteoblue"]["api_key"] = os.environ["METEOBLUE_API_KEY"]
    return cfg
