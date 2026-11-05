"""Proveedor meteoblue, paquete basic-day (https://docs.meteoblue.com/).

Se mantiene como alternativa. basic-day NO trae radiación solar, por lo que con esta
fuente la ET0 Penman-Monteith no se calcula y se muestra solo Hargreaves.
No probado contra la API en vivo en esta versión (la key estaba vencida).
"""
import requests

from .base import DiaClima, Pronostico, ErrorProveedor

MAPEO = {
    "tmax": "temperature_max", "tmin": "temperature_min", "tmedia": "temperature_mean",
    "hr_max": "relativehumidity_max", "hr_min": "relativehumidity_min",
    "hr_media": "relativehumidity_mean", "viento10": "windspeed_mean",
    "precip": "precipitation",
}


def interpretar(datos: dict, lat, lon) -> Pronostico:
    dd = datos.get("data_day")
    if not dd or "time" not in dd:
        raise ErrorProveedor("meteoblue: respuesta sin data_day")
    n = len(dd["time"])
    dias = []
    for i, fecha in enumerate(dd["time"]):
        valores = {campo: (dd.get(var) or [None] * n)[i] for campo, var in MAPEO.items()}
        dias.append(DiaClima(fecha=fecha, **valores))
    meta = datos.get("metadata", {})
    return Pronostico(fuente="meteoblue basic-day", lat=meta.get("latitude", lat),
                      lon=meta.get("longitude", lon), elevacion=meta.get("height"), dias=dias)


def obtener(lat, lon, api_key, timeout=15, proxies=None) -> Pronostico:
    if not api_key:
        raise ErrorProveedor("meteoblue: falta api_key en config.toml")
    url = "https://my.meteoblue.com/packages/basic-day"
    params = {"apikey": api_key, "lat": lat, "lon": lon, "format": "json",
              "windspeed": "ms-1", "timeformat": "YYYY-MM-DD"}
    try:
        r = requests.get(url, params=params, timeout=timeout, proxies=proxies)
        r.raise_for_status()
    except requests.RequestException as e:
        raise ErrorProveedor(f"meteoblue: {e}") from e
    return interpretar(r.json(), lat, lon)
