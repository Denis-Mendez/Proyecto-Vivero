"""Cálculo de ET0 diaria según FAO-56 (Allen et al., 1998).
Cada función cita la ecuación de FAO-56 que implementa."""
import math


def presion_atm(z):                       # ec. 7, kPa
    return 101.3 * ((293 - 0.0065 * z) / 293) ** 5.26


def gamma_psicrometrica(P):               # ec. 8, kPa/°C
    return 0.000665 * P


def e0(T):                                # ec. 11, kPa
    return 0.6108 * math.exp(17.27 * T / (T + 237.3))


def delta_pendiente(Tmedia):              # ec. 13, kPa/°C
    return 4098 * e0(Tmedia) / (Tmedia + 237.3) ** 2


def ea_desde_hr(Tmax, Tmin, RHmax, RHmin):  # ec. 17
    return (e0(Tmin) * RHmax / 100 + e0(Tmax) * RHmin / 100) / 2


def u2_desde_uz(uz, z=10.0):              # ec. 47
    return uz * 4.87 / math.log(67.8 * z - 5.42)


def ra_extraterrestre(lat_deg, J):        # ec. 21-25, MJ/m2/día
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * J)
    dec = 0.409 * math.sin(2 * math.pi / 365 * J - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec))))
    return (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.sin(ws))


def rn_neta(Rs, Ra, Tmax, Tmin, ea, z, albedo=0.23):   # ec. 37-40
    Rso = (0.75 + 2e-5 * z) * Ra
    Rns = (1 - albedo) * Rs
    sigma = 4.903e-9
    ratio = min(Rs / Rso, 1.0)
    Rnl = sigma * ((Tmax + 273.16) ** 4 + (Tmin + 273.16) ** 4) / 2 \
        * (0.34 - 0.14 * math.sqrt(ea)) * (1.35 * ratio - 0.35)
    return Rns - Rnl


def et0_penman_monteith(Tmax, Tmin, RHmax, RHmin, u2, Rs, lat, J, z):  # ec. 6
    Tmedia = (Tmax + Tmin) / 2            # FAO-56 usa (Tmax+Tmin)/2 para cálculo diario
    gam = gamma_psicrometrica(presion_atm(z))
    es = (e0(Tmax) + e0(Tmin)) / 2        # ec. 12
    ea = ea_desde_hr(Tmax, Tmin, RHmax, RHmin)
    D = delta_pendiente(Tmedia)
    Rn = rn_neta(Rs, ra_extraterrestre(lat, J), Tmax, Tmin, ea, z)
    G = 0.0                               # ec. 42: G≈0 a paso diario
    return (0.408 * D * (Rn - G) + gam * 900 / (Tmedia + 273) * u2 * (es - ea)) / \
           (D + gam * (1 + 0.34 * u2))


def et0_hargreaves(Tmax, Tmin, lat, J):   # ec. 52 (Ra convertida a mm/día con 0,408)
    Tmedia = (Tmax + Tmin) / 2
    return 0.0023 * (Tmedia + 17.8) * math.sqrt(max(Tmax - Tmin, 0)) * 0.408 * ra_extraterrestre(lat, J)
