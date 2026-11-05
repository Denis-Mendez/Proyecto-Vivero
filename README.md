# Simulador Vivero

Herramienta de apoyo a decisiones para vivero forestal: pronóstico meteorológico, ET₀ FAO-56,
grados día y, en desarrollo, simulación del crecimiento de plantines.

Versión 2 (rama `v2-escritorio`): app de escritorio portable para Windows, que también puede correr como web.

## Estado de los modelos

| Módulo | Estado |
|---|---|
| ET₀ Penman-Monteith FAO-56 | **Validado** contra los ejemplos resueltos de FAO-56 (tests) y contra la ET₀ de Open-Meteo |
| ET₀ Hargreaves-Samani | Validado en la fórmula; solo control (subestima en días nublados) |
| Grados día | **Experimental**: Tb 13 °C, Tsup 35 °C y umbrales sin validar por especie |
| Altura ~ GD acumulados | **Experimental**: regresión lineal, preparación para la fase 3 |

## Usar en la PC (desarrollo)

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy config.example.toml config.toml      & rem editar si hace falta
python run_desktop.py                     & rem ventana de escritorio
python run_desktop.py --navegador         & rem o en el navegador
python -m pytest                          & rem tests
```

Requiere Python 3.11 o superior.

## Generar la versión portable

```bat
build\build_windows.bat
```

Crea `build\dist\SimuladorVivero\` con `SimuladorVivero.exe` y `config.toml`. Se copia la carpeta completa
(a un pendrive, una carpeta compartida, etc.) y se ejecuta sin instalar Python. Usa Edge WebView2, que viene con Windows 10/11.

La base `simulador_vivero.db` (caché e histórico de consultas) se crea junto al .exe; si esa carpeta
no permite escribir, se usa `%LOCALAPPDATA%\SimuladorVivero`.

## Estructura

```
simulador/
  core/        cálculo puro, sin Flask: et0.py (FAO-56), gdd.py, alturas.py
  providers/   fuentes de datos: openmeteo.py (principal), meteoblue.py (alternativa)
  storage/     cache.py (SQLite: caché, modo sin conexión, histórico)
  web/         rutas Flask, plantillas, estáticos (librerías JS locales)
  servicio.py  une proveedor + caché + cálculos
  config.py    configuración (config.toml) y rutas de datos portables
run_desktop.py lanzador de escritorio (pywebview)
app.py         entrada web (gunicorn app:app, compatible con Render)
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

## Descargar el ejecutable (sin instalar Python)

GitHub genera el `.exe` automáticamente en cada push (`.github/workflows/build-windows.yml`):

1. En el repo, pestaña **Actions** → **Build Windows** → la ejecución más reciente (tilde verde).
2. Abajo, en **Artifacts**, descargar **SimuladorVivero-windows** (zip).
3. Descomprimir y abrir `SimuladorVivero.exe`. Para otras PCs, copiar la carpeta completa.

Para una versión "oficial" con descarga permanente, crear un tag (ej. `v2.0.0`): el zip queda en **Releases**.
