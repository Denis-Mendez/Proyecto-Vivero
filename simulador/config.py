"""Configuración y rutas de datos.

La app es portable: config.toml y la base de datos se guardan junto al ejecutable
(o junto a la carpeta del proyecto cuando se corre desde Python). Si esa carpeta
no se puede escribir (por ejemplo en Program Files), se usa %LOCALAPPDATA%\\SimuladorVivero.
"""
import copy
import os
import sys
import tomllib
from pathlib import Path

DEFAULTS = {
    "proveedor": "open-meteo",          # "open-meteo" o "meteoblue"
    "open_meteo": {"api_key": "", "dias": 16},
    "meteoblue": {"api_key": ""},
    "red": {"proxy": "", "timeout_s": 15},
    "cache": {"vigencia_horas": 3},
    "ubicacion": {"nombre": "Vivero", "lat": -33.12, "lon": -58.30},
    "grados_dia": {                     # hipótesis sin validar — ver core/gdd.py
        "tb": 13.0,
        "tsup": 35.0,
        "alerta_diaria": 18.0,
        "alerta_dias_consecutivos": 3,
        "umbral_acumulado": 150.0,
    },
}


def carpeta_base() -> Path:
    if getattr(sys, "frozen", False):            # ejecutable PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def carpeta_datos() -> Path:
    base = carpeta_base()
    try:
        prueba = base / ".escritura_ok"
        prueba.write_text("ok", encoding="utf-8")
        prueba.unlink()
        return base
    except OSError:
        alt = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SimuladorVivero"
        alt.mkdir(parents=True, exist_ok=True)
        return alt


def _fusionar(base: dict, extra: dict) -> dict:
    out = dict(base)
    for k, v in extra.items():
        out[k] = _fusionar(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def cargar_config(ruta: Path | None = None) -> dict:
    ruta = ruta or carpeta_datos() / "config.toml"
    cfg = copy.deepcopy(DEFAULTS)
    if ruta.exists():
        with open(ruta, "rb") as f:
            cfg = _fusionar(DEFAULTS, tomllib.load(f))
    # Variables de entorno tienen prioridad (útil en servidor)
    if os.environ.get("OPEN_METEO_API_KEY"):
        cfg["open_meteo"]["api_key"] = os.environ["OPEN_METEO_API_KEY"]
    if os.environ.get("METEOBLUE_API_KEY"):
        cfg["meteoblue"]["api_key"] = os.environ["METEOBLUE_API_KEY"]
    return cfg
