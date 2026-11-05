"""Proveedor Open-Meteo (https://open-meteo.com/en/docs).

Sin API key usa el servicio gratuito (solo uso no comercial).
Con API key usa el endpoint comercial customer-api.open-meteo.com.
"""
import requests

from .base import DiaClima, Pronostico, ErrorProveedor

VARIABLES = [
    "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
    "relative_humidity_2m_max", "relative_humidity_2m_min", "relative_humidity_2m_mean",
    "wind_speed_10m_mean", "shortwave_radiation_sum", "precipitation_sum",
    "et0_fao_evapotranspiration",
]

MAPEO = {
    "tmax": "temperature_2m_max", "tmin": "temperature_2m_min", "tmedia": "temperature_2m_mean",
    "hr_max": "relative_humidity_2m_max", "hr_min": "relative_humidity_2m_min",
    "hr_media": "relative_humidity_2m_mean", "viento10": "wind_speed_10m_mean",
    "rs": "shortwave_radiation_sum", "precip": "precipitation_sum",
    "et0_ref": "et0_fao_evapotranspiration",
}

UNIDADES_ESPERADAS = {"wind_speed_10m_mean": "m/s", "shortwave_radiation_sum": "MJ/m²"}


def construir_url_y_params(lat, lon, dias=16, api_key=""):
    base = "https://customer-api.open-meteo.com" if api_key else "https://api.open-meteo.com"
    params = {
        "latitude": lat, "longitude": lon, "daily": ",".join(VARIABLES),
        "forecast_days": dias, "timezone": "auto", "wind_speed_unit": "ms",
    }
    if api_key:
        params["apikey"] = api_key
    return f"{base}/v1/forecast", params


def interpretar(datos: dict) -> Pronostico:
    """Convierte la respuesta JSON de Open-Meteo al formato común."""
    if datos.get("error"):
        raise ErrorProveedor(f"Open-Meteo: {datos.get('reason', 'error desconocido')}")
    daily = datos.get("daily")
    if not daily or "time" not in daily:
        raise ErrorProveedor("Open-Meteo: respuesta sin datos diarios")
    unidades = datos.get("daily_units", {})
    for var, unidad in UNIDADES_ESPERADAS.items():
        if var in unidades and unidades[var] != unidad:
            raise ErrorProveedor(f"Open-Meteo: unidad inesperada para {var}: {unidades[var]}")

    dias = []
    for i, fecha in enumerate(daily["time"]):
        valores = {campo: (daily.get(var) or [None] * len(daily["time"]))[i] for campo, var in MAPEO.items()}
        dias.append(DiaClima(fecha=fecha, **valores))
    return Pronostico(fuente="Open-Meteo", lat=datos["latitude"], lon=datos["longitude"],
                      elevacion=datos.get("elevation"), dias=dias)


def obtener(lat, lon, dias=16, api_key="", timeout=15, proxies=None) -> Pronostico:
    url, params = construir_url_y_params(lat, lon, dias, api_key)
    try:
        r = requests.get(url, params=params, timeout=timeout, proxies=proxies)
    except requests.RequestException as e:
        raise ErrorProveedor(f"No se pudo conectar con Open-Meteo: {e}") from e
    if r.status_code != 200:
        try:
            motivo = r.json().get("reason", r.text[:200])
        except ValueError:
            motivo = r.text[:200]
        raise ErrorProveedor(f"Open-Meteo respondió {r.status_code}: {motivo}")
    return interpretar(r.json())
