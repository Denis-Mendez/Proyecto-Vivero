"""Relación altura ~ grados día acumulados (MODELO EXPERIMENTAL, fase 3 en preparación).

Reemplaza la versión anterior, que tenía tres errores:
  1. el GD acumulado se sumaba solo en las fechas con medición, no en todos los días;
  2. la "proyección a 30 días" sumaba 30 GD, no 30 días;
  3. la pendiente usaba solo la primera y la última medición.

Ahora:
  - el GD se acumula día a día sobre toda la serie de temperaturas;
  - la pendiente (cm por GD) se ajusta por mínimos cuadrados con todas las fechas;
  - la proyección usa los GD pronosticados de los próximos días.
Supone crecimiento lineal en GD: solo es razonable dentro de la fase de crecimiento medida.
"""
import csv
import io
import math
from collections import defaultdict
from datetime import date, datetime

from . import gdd

COLS_ALTURAS = {"Fecha", "Local", "MG", "Individuo", "Altura"}
COLS_TEMP = {"Fecha", "Tmax", "Tmin"}


def _fecha(txt):
    txt = txt.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(txt[:10], fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha no reconocida: {txt!r}")


def _num(txt):
    return float(str(txt).strip().replace(",", "."))


def leer_csv(contenido: bytes | str, requeridas: set):
    if isinstance(contenido, bytes):
        contenido = contenido.decode("utf-8-sig", errors="replace")
    muestra = contenido[:2048]
    sep = ";" if muestra.count(";") > muestra.count(",") else ","
    lector = csv.DictReader(io.StringIO(contenido), delimiter=sep)
    cols = {c.strip() for c in (lector.fieldnames or [])}
    faltan = requeridas - cols
    if faltan:
        raise ValueError(f"Faltan columnas: {', '.join(sorted(faltan))}")
    return [{k.strip(): v for k, v in fila.items()} for fila in lector]


def gd_acumulado_por_fecha(filas_temp, tb, tsup):
    """Serie diaria → {fecha: GD acumulado}. Avisa si faltan días en la serie."""
    serie = sorted((_fecha(f["Fecha"]), _num(f["Tmax"]), _num(f["Tmin"])) for f in filas_temp)
    acum, salida, huecos = 0.0, {}, []
    previo = None
    for d, tx, tn in serie:
        if previo and (d - previo).days > 1:
            huecos.append((previo, d))
        acum += gdd.gd_diario(tx, tn, tb, tsup)
        salida[d] = acum
        previo = d
    return salida, huecos


def _regresion(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    if sxx == 0:
        return None, None
    pend = sxy / sxx
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else None
    return pend, r


def analizar(alturas_csv, temp_csv, tb=13.0, tsup=35.0, gd_futuros=None):
    """Devuelve una fila por (Local, MG) con pendiente cm/GD, r y altura proyectada."""
    gd_fecha, huecos = gd_acumulado_por_fecha(leer_csv(temp_csv, COLS_TEMP), tb, tsup)
    grupos = defaultdict(lambda: defaultdict(list))
    sin_temp = 0
    for f in leer_csv(alturas_csv, COLS_ALTURAS):
        try:
            d, h = _fecha(f["Fecha"]), _num(f["Altura"])
        except ValueError:
            continue
        if d not in gd_fecha:
            sin_temp += 1
            continue
        grupos[(f["Local"].strip(), f["MG"].strip())][d].append(h)

    resultados = []
    for (local, mg), por_fecha in sorted(grupos.items()):
        fechas = sorted(por_fecha)
        x = [gd_fecha[d] for d in fechas]
        y = [sum(v) / len(v) for v in (por_fecha[d] for d in fechas)]   # altura media por fecha
        fila = {"local": local, "mg": mg, "n_fechas": len(fechas),
                "n_plantas": max(len(por_fecha[d]) for d in fechas),
                "ultima_fecha": fechas[-1].isoformat(), "altura_actual": round(y[-1], 1),
                "gd_actual": round(x[-1], 1), "pendiente": None, "r": None, "altura_proyectada": None}
        if len(fechas) >= 2:
            pend, r = _regresion(x, y)
            if pend is not None:
                fila["pendiente"] = round(pend, 4)
                fila["r"] = None if r is None else round(r, 2)
                if gd_futuros is not None:
                    fila["altura_proyectada"] = round(y[-1] + pend * gd_futuros, 1)
        resultados.append(fila)
    return {"resultados": resultados, "mediciones_sin_temperatura": sin_temp,
            "huecos_temperatura": [(a.isoformat(), b.isoformat()) for a, b in huecos]}
