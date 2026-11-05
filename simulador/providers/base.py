"""Formato común de datos meteorológicos diarios.

Cada proveedor (Open-Meteo, meteoblue, CSV, ...) devuelve un `Pronostico`.
El resto de la app no sabe de qué API vienen los datos.
"""
from dataclasses import dataclass, field, asdict


@dataclass
class DiaClima:
    fecha: str                  # ISO yyyy-mm-dd, en hora local del punto
    tmax: float | None = None   # °C, a 2 m
    tmin: float | None = None
    tmedia: float | None = None
    hr_max: float | None = None  # %
    hr_min: float | None = None
    hr_media: float | None = None
    viento10: float | None = None  # m/s, media diaria a 10 m
    rs: float | None = None      # radiación solar global, MJ/m²/día
    precip: float | None = None  # mm
    et0_ref: float | None = None  # ET0 calculada por el proveedor (control), mm/día


@dataclass
class Pronostico:
    fuente: str
    lat: float
    lon: float
    elevacion: float | None
    dias: list[DiaClima] = field(default_factory=list)
    desde_cache: bool = False
    consultado: str = ""         # fecha-hora ISO de la consulta a la API

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["dias"] = [DiaClima(**x) for x in d.get("dias", [])]
        return cls(**d)


class ErrorProveedor(Exception):
    """Error al consultar o interpretar la API meteorológica."""
