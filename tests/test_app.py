"""Tests de la app Flask con el proveedor simulado (sin internet)."""
import copy
import json
from pathlib import Path

import pytest

from simulador import create_app
from simulador.config import DEFAULTS
from simulador.providers import openmeteo
from simulador.providers.base import ErrorProveedor

FIX = Path(__file__).parent / "fixtures"
RESPUESTA = json.loads((FIX / "om.json").read_text(encoding="utf-8"))


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    llamadas = {"n": 0}

    def falso(lat, lon, *a, **k):
        llamadas["n"] += 1
        return openmeteo.interpretar(RESPUESTA)

    monkeypatch.setattr(openmeteo, "obtener", falso)
    app = create_app(copy.deepcopy(DEFAULTS), ruta_db=tmp_path / "t.db")
    app.testing = True
    c = app.test_client()
    c.llamadas = llamadas
    return c


def test_index(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and b"Consultar" in r.data


def test_api_pronostico_y_cache(cliente):
    r = cliente.post("/api/pronostico", json={"lat": -33.12, "lon": -58.3})
    t = r.get_json()
    assert r.status_code == 200 and len(t["filas"]) == 16 and not t["desde_cache"]
    assert t["filas"][0]["et0_pm"] is not None
    r2 = cliente.post("/api/pronostico", json={"lat": -33.12, "lon": -58.3}).get_json()
    assert r2["desde_cache"] and cliente.llamadas["n"] == 1


def test_sin_internet_usa_ultima(cliente, monkeypatch, tmp_path):
    cliente.post("/api/pronostico", json={"lat": -33.12, "lon": -58.3})
    cliente.application.config["SIM"]["cache"]["vigencia_horas"] = 0   # forzar consulta nueva
    monkeypatch.setattr(openmeteo, "obtener", lambda *a, **k: (_ for _ in ()).throw(ErrorProveedor("sin red")))
    t = cliente.post("/api/pronostico", json={"lat": -33.12, "lon": -58.3}).get_json()
    assert t["desde_cache"] and len(t["filas"]) == 16


def test_sin_internet_ni_cache(cliente, monkeypatch):
    monkeypatch.setattr(openmeteo, "obtener", lambda *a, **k: (_ for _ in ()).throw(ErrorProveedor("sin red")))
    r = cliente.post("/api/pronostico", json={"lat": -30, "lon": -55})
    assert r.status_code == 502 and "sin red" in r.get_json()["error"]


def test_coordenadas_invalidas(cliente):
    assert cliente.post("/api/pronostico", json={"lat": "x", "lon": 1}).status_code == 400


def test_csv(cliente):
    r = cliente.get("/exportar.csv?lat=-33.12&lon=-58.3")
    texto = r.data.decode("utf-8-sig")
    assert r.status_code == 200 and "et0_pm" in texto and "2026-11-04" in texto


def test_grados_dia(cliente):
    r = cliente.get("/grados-dia?lat=-33.12&lon=-58.3")
    assert r.status_code == 200 and b"experimental" in r.data


def test_alturas(cliente):
    datos = {"archivo_alturas": (open(FIX / "alturas.csv", "rb"), "a.csv"),
             "archivo_temp": (open(FIX / "temperaturas.csv", "rb"), "t.csv"), "proyectar": "1"}
    r = cliente.post("/alturas", data=datos, content_type="multipart/form-data")
    assert r.status_code == 200 and b"MG1" in r.data


def test_ubicacion_por_defecto_vivero(cliente):
    r = cliente.get("/")
    assert b'value="-33.1295"' in r.data and b'value="-58.1924"' in r.data
    assert b"logo-mdp-blanco.svg" in r.data
