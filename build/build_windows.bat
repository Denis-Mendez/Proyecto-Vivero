@echo off
REM Genera la carpeta portable dist\SimuladorVivero\ con SimuladorVivero.exe
REM Requiere: Python 3.11+ en Windows y  pip install -r requirements-dev.txt
cd /d %~dp0\..
pyinstaller --noconfirm --clean --onedir --windowed ^
  --name SimuladorVivero ^
  --icon simulador\web\static\favicon.ico ^
  --add-data "simulador\web\templates;simulador\web\templates" ^
  --add-data "simulador\web\static;simulador\web\static" ^
  --distpath build\dist --workpath build\work --specpath build ^
  run_desktop.py
if errorlevel 1 exit /b 1
copy /Y config.example.toml build\dist\SimuladorVivero\config.toml >nul
echo.
echo Listo: build\dist\SimuladorVivero\SimuladorVivero.exe
echo Para distribuir, comprimir la carpeta build\dist\SimuladorVivero completa.
