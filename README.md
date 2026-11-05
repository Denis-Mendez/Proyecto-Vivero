# Simulador Vivero

Herramienta de apoyo a decisiones para vivero forestal: pronóstico meteorológico, ET₀ FAO-56,
grados día y, en desarrollo, simulación del crecimiento de plantines.

Versión 2: aplicación web publicada en PythonAnywhere (https://denismendez.pythonanywhere.com),
con la identidad visual de Montes del Plata y adaptada a celular.

## Estado de los modelos

| Módulo | Estado |
|---|---|
| ET₀ Penman-Monteith FAO-56 | **Validado** contra los ejemplos resueltos de FAO-56 (tests) y contra la ET₀ de Open-Meteo |
| ET₀ Hargreaves-Samani | Validado en la fórmula; solo control (subestima en días nublados) |
| Grados día | **Experimental**: Tb 13 °C, Tsup 35 °C y umbrales sin validar por especie |
| Altura ~ GD acumulados | **Experimental**: regresión lineal, preparación para la fase 3 |

## Desarrollo local

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements-dev.txt
python app.py                    # http://127.0.0.1:5000
python -m pytest                 # tests
```

Requiere Python 3.11 o superior. `config.toml` es opcional (ver `config.example.toml`).

## Publicar cambios en PythonAnywhere

1. Subir los cambios a `main` en GitHub.
2. En la consola Bash de PythonAnywhere: `cd ~/Proyecto-Vivero && git pull`
3. Pestaña **Web** → **Reload**.

## Estructura

```
simulador/
  core/        cálculo puro, sin Flask: et0.py (FAO-56), gdd.py, alturas.py
  providers/   fuentes de datos: openmeteo.py (principal), meteoblue.py (alternativa)
  storage/     cache.py (SQLite: caché, modo sin conexión, histórico)
  web/         rutas Flask, plantillas, estáticos (librerías JS, logo y tipografía locales)
  servicio.py  une proveedor + caché + cálculos
  config.py    configuración (config.toml) y valores por defecto (ubicación del vivero)
app.py         entrada web (PythonAnywhere / gunicorn)
tests/         tests de cálculos (ejemplos FAO-56) y de la app
```

## Fuentes de datos

- **Open-Meteo** (por defecto): 16 días, radiación solar, ET₀ de referencia. El servicio gratuito es solo para
  uso no comercial; para uso en la empresa corresponde la suscripción comercial (poner la `api_key` en `config.toml`).
- **meteoblue basic-day**: sin radiación solar → solo se calcula Hargreaves.

Las API keys van en `config.toml` (excluido de git) o en las variables de entorno `OPEN_METEO_API_KEY` / `METEOBLUE_API_KEY`.

## Referencias

- Allen et al. (1998). FAO Irrigation and Drainage Paper 56. https://www.fao.org/4/x0490e/x0490e00.htm
- Open-Meteo API: https://open-meteo.com/en/docs

## Identidad visual

Colores y logo según el Manual de marca de Montes del Plata (set. 2022): verde #17954E, petróleo #194E50,
gris azulado #CFDFE2; secundarios (#007AFF, #21D4BE, #A9F236, #FF5500) solo en detalles y gráficos.
Texto en Helvetica/Arial; números destacados en Bebas Neue (licencia OFL, incluida).
