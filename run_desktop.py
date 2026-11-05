"""Lanzador de escritorio del Simulador Vivero.

Levanta el servidor Flask en 127.0.0.1 (solo accesible desde esta PC) en un puerto libre
y lo abre en una ventana propia con pywebview (usa Edge WebView2 en Windows).

    python run_desktop.py              # ventana de escritorio
    python run_desktop.py --navegador  # abre en el navegador predeterminado
"""
import socket
import sys
import threading
import webbrowser

from werkzeug.serving import make_server

from simulador import create_app


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    app = create_app()
    puerto = puerto_libre()
    servidor = make_server("127.0.0.1", puerto, app, threaded=True)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    url = f"http://127.0.0.1:{puerto}/"

    usar_navegador = "--navegador" in sys.argv
    if not usar_navegador:
        try:
            import webview
        except ImportError:
            usar_navegador = True

    if usar_navegador:
        webbrowser.open(url)
        print(f"Simulador Vivero en {url} — cerrá esta ventana para salir.")
        try:
            hilo.join()
        except KeyboardInterrupt:
            pass
    else:
        webview.create_window("Simulador Vivero", url, width=1360, height=860, min_size=(900, 600))
        webview.start()
    servidor.shutdown()


if __name__ == "__main__":
    main()
