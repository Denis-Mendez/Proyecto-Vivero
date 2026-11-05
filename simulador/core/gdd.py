"""Grados día (acumulación térmica).

MODELO EXPERIMENTAL: Tb = 13 °C y Tsup = 35 °C son hipótesis de trabajo,
no parámetros validados para las especies del vivero. Se configuran en config.toml
y deben calibrarse con mediciones de altura (fase 3).
"""


def gd_diario(tmax, tmin, tb=13.0, tsup=None):
    """Método del promedio: GD = max(0, (Tmax+Tmin)/2 - Tb).

    Si se indica tsup, se aplica corte horizontal: Tmax y Tmin se limitan a tsup
    antes de promediar (la temperatura por encima del umbral no suma).
    """
    if tmax is None or tmin is None:
        return None
    if tsup is not None:
        tmax, tmin = min(tmax, tsup), min(tmin, tsup)
    return max(0.0, (tmax + tmin) / 2 - tb)


def gd_acumulado(valores):
    """Suma acumulada que ignora días sin dato (None queda como None)."""
    acum, salida = 0.0, []
    for v in valores:
        if v is None:
            salida.append(None)
        else:
            acum += v
            salida.append(acum)
    return salida


def dias_consecutivos_sobre(valores, umbral, n):
    """True si hay al menos n días seguidos con GD >= umbral."""
    racha = 0
    for v in valores:
        racha = racha + 1 if (v is not None and v >= umbral) else 0
        if racha >= n:
            return True
    return False
