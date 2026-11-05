"""Capa de servicio: une proveedor + caché + cálculos.

Las rutas de Flask llaman a estas funciones; así la lógica se puede probar sin interfaz.
"""
import datetime as dt

from .core import et0 as fao
from .core import gdd
from .providers import openmeteo, meteoblue
from .providers.base import Pronostico, ErrorProveedor


def _proxies(cfg):
    p = cfg["red"].get("proxy")
    return {"http": p, "https": p} if p else None


def obtener_pronostico(cfg, cache, lat, lon) -> Pronostico:
    """Devuelve el pronóstico usando caché vigente; si la API falla, usa la última consulta guardada."""
    fuente = cfg["proveedor"]
    vigente = cache.ultima(fuente, lat, lon, cfg["cache"]["vigencia_horas"])
    if vigente:
        p = Pronostico.from_dict(vigente[1])
        p.consultado, p.desde_cache = vigente[0], True
        return p
    try:
        if fuente == "meteoblue":
            p = meteoblue.obtener(lat, lon, cfg["meteoblue"]["api_key"],
                                  cfg["red"]["timeout_s"], _proxies(cfg))
        else:
            p = openmeteo.obtener(lat, lon, cfg["open_meteo"]["dias"], cfg["open_meteo"]["api_key"],
                                  cfg["red"]["timeout_s"], _proxies(cfg))
    except ErrorProveedor:
        vieja = cache.ultima(fuente, lat, lon)        # sin límite de antigüedad
        if not vieja:
            raise
        p = Pronostico.from_dict(vieja[1])
        p.consultado, p.desde_cache = vieja[0], True
        return p
    p.consultado = cache.guardar(fuente, lat, lon, p.to_dict())
    return p


def _r(x, n=2):
    return None if x is None else round(x, n)


def calcular_tabla(p: Pronostico, cfg) -> dict:
    """Calcula ET0 (PM y Hargreaves) y grados día para cada día del pronóstico."""
    g = cfg["grados_dia"]
    z = p.elevacion if p.elevacion is not None else 0.0
    filas = []
    for d in p.dias:
        J = dt.date.fromisoformat(d.fecha).timetuple().tm_yday
        u2 = fao.u2_desde_uz(d.viento10) if d.viento10 is not None else None
        pm = hs = None
        if None not in (d.tmax, d.tmin, d.hr_max, d.hr_min, u2, d.rs):
            pm = fao.et0_penman_monteith(d.tmax, d.tmin, d.hr_max, d.hr_min, u2, d.rs, p.lat, J, z)
        if None not in (d.tmax, d.tmin):
            hs = fao.et0_hargreaves(d.tmax, d.tmin, p.lat, J)
        filas.append({
            "fecha": d.fecha, "tmax": d.tmax, "tmin": d.tmin, "tmedia": d.tmedia,
            "hr_max": d.hr_max, "hr_min": d.hr_min, "viento10": d.viento10, "u2": _r(u2),
            "rs": d.rs, "precip": d.precip,
            "et0_pm": _r(pm), "et0_hs": _r(hs), "et0_ref": d.et0_ref,
            "gd": _r(gdd.gd_diario(d.tmax, d.tmin, g["tb"], g["tsup"])),
        })
    acum = gdd.gd_acumulado([f["gd"] for f in filas])
    for f, a in zip(filas, acum):
        f["gd_acum"] = _r(a)
    gds = [f["gd"] for f in filas]
    return {
        "fuente": p.fuente, "lat": p.lat, "lon": p.lon, "elevacion": p.elevacion,
        "consultado": p.consultado, "desde_cache": p.desde_cache,
        "hay_radiacion": any(f["rs"] is not None for f in filas),
        "filas": filas,
        "gd_total": _r(acum[-1] if acum and acum[-1] is not None else 0),
        "alerta_diaria": any(v is not None and v >= g["alerta_diaria"] for v in gds),
        "alerta_consecutiva": gdd.dias_consecutivos_sobre(gds, g["alerta_diaria"], g["alerta_dias_consecutivos"]),
        "parametros_gd": g,
    }


COLUMNAS_CSV = ["fecha", "tmax", "tmin", "tmedia", "hr_max", "hr_min", "viento10", "u2", "rs",
                "precip", "et0_pm", "et0_hs", "et0_ref", "gd", "gd_acum"]
