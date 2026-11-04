import csv
import io

from flask import Blueprint, current_app, jsonify, render_template, request, Response

from .. import servicio
from ..core import alturas
from ..providers.base import ErrorProveedor

bp = Blueprint("web", __name__)


def _cfg():
    return current_app.config["SIM"]


def _coords(origen):
    try:
        lat, lon = float(origen.get("lat")), float(origen.get("lon"))
    except (TypeError, ValueError):
        raise ValueError("Latitud y longitud son requeridas y deben ser números")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Coordenadas fuera de rango")
    return lat, lon


def _tabla(lat, lon):
    p = servicio.obtener_pronostico(_cfg(), current_app.config["CACHE"], lat, lon)
    return servicio.calcular_tabla(p, _cfg())


@bp.get("/")
def index():
    return render_template("index.html", ubicacion=_cfg()["ubicacion"], g=_cfg()["grados_dia"])


@bp.post("/api/pronostico")
def api_pronostico():
    try:
        lat, lon = _coords(request.get_json(silent=True) or {})
        return jsonify(_tabla(lat, lon))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ErrorProveedor as e:
        return jsonify({"error": str(e)}), 502


@bp.get("/exportar.csv")
def exportar_csv():
    try:
        lat, lon = _coords(request.args)
        t = _tabla(lat, lon)
    except (ValueError, ErrorProveedor) as e:
        return Response(str(e), status=400, mimetype="text/plain")
    buf = io.StringIO()
    buf.write(f"# Fuente: {t['fuente']} | punto {t['lat']}, {t['lon']} | elevación {t['elevacion']} m | consultado {t['consultado']}\n")
    w = csv.DictWriter(buf, fieldnames=servicio.COLUMNAS_CSV, extrasaction="ignore", delimiter=";")
    w.writeheader()
    for f in t["filas"]:
        w.writerow({k: ("" if v is None else str(v).replace(".", ",")) if k != "fecha" else v
                    for k, v in f.items()})
    # BOM para que Excel en español abra bien acentos y separador ;
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=pronostico_vivero.csv"})


@bp.get("/grados-dia")
def grados_dia():
    origen = request.args if request.args.get("lat") else _cfg()["ubicacion"]
    try:
        lat, lon = _coords(origen)
        t = _tabla(lat, lon)
    except (ValueError, ErrorProveedor) as e:
        return render_template("error.html", mensaje=str(e)), 400
    return render_template("grados_dia.html", t=t)


@bp.route("/alturas", methods=["GET", "POST"])
def alturas_view():
    g = _cfg()["grados_dia"]
    if request.method == "GET":
        return render_template("alturas.html", res=None, error=None, g=g)
    fa, ft = request.files.get("archivo_alturas"), request.files.get("archivo_temp")
    if not fa or not ft or not fa.filename or not ft.filename:
        return render_template("alturas.html", res=None, error="Faltan archivos.", g=g), 400
    gd_futuros, aviso = None, None
    if request.form.get("proyectar"):
        try:
            u = _cfg()["ubicacion"]
            t = _tabla(u["lat"], u["lon"])
            gd_futuros = t["gd_total"]
            aviso = f"Proyección con {gd_futuros} GD pronosticados ({len(t['filas'])} días, {u['nombre']})."
        except ErrorProveedor as e:
            aviso = f"Sin proyección: {e}"
    try:
        res = alturas.analizar(fa.read(), ft.read(), g["tb"], g["tsup"], gd_futuros)
    except ValueError as e:
        return render_template("alturas.html", res=None, error=str(e), g=g), 400
    return render_template("alturas.html", res=res, error=None, aviso=aviso, g=g)
