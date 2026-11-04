"""Caché local en SQLite.

- Evita consultar la API cada vez (respeta los límites de uso).
- Si no hay internet, devuelve la última consulta guardada y la marca como "desde caché".
- Cada consulta queda guardada: con el tiempo arma un histórico de pronósticos emitidos,
  útil para comparar pronóstico vs. real en fases posteriores.
"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS consultas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fuente TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    consultado TEXT NOT NULL,
    datos TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_consultas_punto ON consultas (fuente, lat, lon, consultado);
"""


def _redondear(x):
    return round(float(x), 3)          # ~100 m: mismo punto a efectos de caché


class Cache:
    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)
        with self._con() as c:
            c.executescript(ESQUEMA)

    def _con(self):
        return sqlite3.connect(self.ruta)

    def guardar(self, fuente, lat, lon, datos: dict, momento: datetime | None = None):
        momento = (momento or datetime.now()).isoformat(timespec="seconds")
        with self._con() as c:
            c.execute("INSERT INTO consultas (fuente, lat, lon, consultado, datos) VALUES (?,?,?,?,?)",
                      (fuente, _redondear(lat), _redondear(lon), momento, json.dumps(datos)))
        return momento

    def ultima(self, fuente, lat, lon, vigencia_horas: float | None = None):
        """Última consulta del punto. Con vigencia_horas, solo si es más reciente que eso."""
        sql = "SELECT consultado, datos FROM consultas WHERE fuente=? AND lat=? AND lon=?"
        args = [fuente, _redondear(lat), _redondear(lon)]
        if vigencia_horas is not None:
            sql += " AND consultado >= ?"
            args.append((datetime.now() - timedelta(hours=vigencia_horas)).isoformat(timespec="seconds"))
        sql += " ORDER BY consultado DESC LIMIT 1"
        with self._con() as c:
            fila = c.execute(sql, args).fetchone()
        return (fila[0], json.loads(fila[1])) if fila else None
