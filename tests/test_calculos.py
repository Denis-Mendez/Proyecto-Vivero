"""Tests de los cálculos científicos contra los ejemplos resueltos de FAO-56."""
import json
from pathlib import Path

import pytest

from simulador.core import et0 as fao
from simulador.core import gdd, alturas
from simulador.providers import openmeteo

FIX = Path(__file__).parent / "fixtures"


# --- FAO-56 ---
def test_presion_atm_ej2():                      # Ejemplo 2: z = 1800 m -> 81,8 kPa, γ = 0,054
    P = fao.presion_atm(1800)
    assert P == pytest.approx(81.8, abs=0.05)
    assert fao.gamma_psicrometrica(P) == pytest.approx(0.054, abs=0.0005)


def test_ra_ej8():                               # Ejemplo 8: 20°S, 3 de setiembre -> 32,2 MJ/m²/día
    assert fao.ra_extraterrestre(-20, 246) == pytest.approx(32.2, abs=0.05)


def test_e0_y_delta():                           # Tabla 2.3 y 2.4 (anexo 2) para T = 20 °C
    assert fao.e0(20) == pytest.approx(2.338, abs=0.001)
    assert fao.delta_pendiente(20) == pytest.approx(0.145, abs=0.001)


def test_u2_desde_10m():                         # Ejemplo 14: 3,2 m/s a 10 m -> 2,4 m/s a 2 m
    assert fao.u2_desde_uz(3.2, 10) == pytest.approx(2.4, abs=0.05)


def test_penman_monteith_ej18():                 # Ejemplo 18: Bruselas, 6 de julio -> 3,9 mm/día
    u2 = fao.u2_desde_uz(10 / 3.6, 10)
    et = fao.et0_penman_monteith(21.5, 12.3, 84, 63, u2, 22.07, 50.8, 187, 100)
    assert et == pytest.approx(3.9, abs=0.05)


def test_hargreaves_incluye_0408():
    # Con Ra = 40 MJ, Tmed 20, rango 10: 0,0023·37,8·√10·0,408·40 ≈ 4,49 mm (no 11)
    J = 15
    ra = fao.ra_extraterrestre(-33, J)
    esperado = 0.0023 * (20 + 17.8) * 10 ** 0.5 * 0.408 * ra
    assert fao.et0_hargreaves(25, 15, -33, J) == pytest.approx(esperado)
    assert fao.et0_hargreaves(25, 15, -33, J) < 8


# --- Grados día ---
def test_gd_diario():
    assert gdd.gd_diario(25, 15, tb=13) == 7
    assert gdd.gd_diario(12, 5, tb=13) == 0
    assert gdd.gd_diario(40, 20, tb=13, tsup=35) == pytest.approx((35 + 20) / 2 - 13)
    assert gdd.gd_diario(None, 10) is None


def test_gd_acumulado_y_racha():
    assert gdd.gd_acumulado([1, None, 2]) == [1, None, 3]
    assert gdd.dias_consecutivos_sobre([18, 19, 17, 18, 18, 20], 18, 3)
    assert not gdd.dias_consecutivos_sobre([18, 19, 17, 18, 18], 18, 3)


# --- Proveedor Open-Meteo (respuesta real guardada el 04-11-2026) ---
def test_interpretar_openmeteo():
    p = openmeteo.interpretar(json.loads((FIX / "om.json").read_text(encoding="utf-8")))
    assert len(p.dias) == 16 and p.elevacion == 14.0
    assert p.dias[0].fecha == "2026-11-04" and p.dias[0].rs == 26.62


def test_pm_consistente_con_openmeteo():
    """Nuestro PM diario vs la ET0 horaria de Open-Meteo: error medio < 0,4 mm/día."""
    from simulador.config import DEFAULTS
    from simulador.servicio import calcular_tabla
    p = openmeteo.interpretar(json.loads((FIX / "om.json").read_text(encoding="utf-8")))
    filas = calcular_tabla(p, DEFAULTS)["filas"]
    mae = sum(abs(f["et0_pm"] - f["et0_ref"]) for f in filas) / len(filas)
    assert mae < 0.4


def test_openmeteo_error():
    with pytest.raises(openmeteo.ErrorProveedor):
        openmeteo.interpretar({"error": True, "reason": "x"})


# --- Alturas ---
def test_alturas_regresion():
    res = alturas.analizar((FIX / "alturas.csv").read_bytes(), (FIX / "temperaturas.csv").read_bytes(),
                           tb=13, tsup=35, gd_futuros=100)
    a = next(r for r in res["resultados"] if r["local"] == "A")
    # GD = 7/día; 1-oct: 7, 15-oct: 105, 29-oct: 203. Alturas medias 5,5 / 8,5 / 11,5
    assert a["gd_actual"] == 203
    assert a["pendiente"] == pytest.approx(3 / 98, abs=1e-4)
    assert a["r"] == 1.0
    assert a["altura_proyectada"] == pytest.approx(11.5 + 100 * 3 / 98, abs=0.1)
    assert res["mediciones_sin_temperatura"] == 1      # la de B en diciembre
