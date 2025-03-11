from flask import Flask, render_template, request, jsonify, send_file
import requests
import math
import datetime
import csv
import os

app = Flask(__name__)

# Clave de API de meteoblue (reemplázala con la tuya)
API_KEY = "Dtj1cl64zpfdXZgS"

def obtener_datos_meteoblue(lat, lon):
    url = f"https://my.meteoblue.com/packages/basic-day?apikey={API_KEY}&lat={lat}&lon={lon}&asl=100&format=json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        datos = response.json()

        # ✅ Imprimir datos para verificar estructura
        print("Datos de meteoblue:", datos)

        if "data_day" not in datos:
            print("Error: Datos no válidos de meteoblue")
            return None

        return datos
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener datos de meteoblue: {e}")
        return None

def calcular_evapotranspiracion(T_max, T_min, T_media, RH, R_n, u2):
    gamma = 0.665 * 10**-3  # Constante psicrométrica en kPa/°C
    
    # 🔹 Cálculo de la presión de vapor de saturación
    es_Tmax = 0.6108 * math.exp((17.27 * T_max) / (T_max + 237.3))
    es_Tmin = 0.6108 * math.exp((17.27 * T_min) / (T_min + 237.3))
    es = (es_Tmax + es_Tmin) / 2
    
    # 🔹 Cálculo de la presión de vapor real
    ea = (RH / 100) * es  

    # 🔹 Cálculo de la pendiente de la curva de presión de vapor
    delta = (4098 * es) / ((T_media + 237.3) ** 2)

    # 🔹 Aproximación de radiación neta (si no hay datos de radiación)
    if R_n is None:
        R_n = 0.16 * (T_max - T_min)  # Estimación empírica

    # 🔹 Cálculo final de ET₀
    ET0 = (0.408 * delta * (R_n - 0) + gamma * (900 / (T_media + 273)) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))

    return ET0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calcular', methods=['POST'])
def calcular():
    try:
        data = request.json
        lat = float(data['lat'])
        lon = float(data['lon'])
        datos_meteoblue = obtener_datos_meteoblue(lat, lon)

        if not datos_meteoblue:
            return jsonify({'error': 'No se pudieron obtener datos de meteoblue'}), 500

        parametros = datos_meteoblue.get("data_day", {})

        # 🔹 Determinar la cantidad de días disponibles
        num_dias = min(
            len(parametros.get("temperature_max", [])),
            len(parametros.get("temperature_min", [])),
            len(parametros.get("relativehumidity_mean", [])),
            len(parametros.get("temperature_mean", [])),
            len(parametros.get("windspeed_mean", []))  # Agregamos el viento
        )
        print(f"Número de días disponibles: {num_dias}")

        if num_dias == 0:
            return jsonify({'error': 'No hay datos suficientes en meteoblue'}), 500

        predicciones = []
        for i in range(min(num_dias, 14)):  # Solo iterar hasta 14 días como máximo
            try:
                fecha = (datetime.datetime.today() + datetime.timedelta(days=i)).strftime("%d-%m-%Y")

                # Obtener valores de forma segura
                T_max = parametros.get("temperature_max", [None] * num_dias)[i]
                T_min = parametros.get("temperature_min", [None] * num_dias)[i]
                RH = parametros.get("relativehumidity_mean", [None] * num_dias)[i]
                R_n = parametros.get("temperature_mean", [None] * num_dias)[i]  # Se usa temp media en vez de radiación
                u2 = parametros.get("windspeed_mean", [2.0] * num_dias)[i]  # ⚠️ Nuevo: Usa `windspeed_mean`, por defecto 2 m/s

                # 🔹 Validar que los datos existan antes de usarlos
                if None in [T_max, T_min, RH, R_n, u2]:
                    print(f"Datos incompletos para {fecha}, omitiendo...")
                    continue

                T_media = (T_max + T_min) / 2
                ET0 = calcular_evapotranspiracion(T_max, T_min, T_media, RH, R_n, u2)

                predicciones.append({
                    "fecha": fecha,
                    "T_max": round(T_max, 2),
                    "T_min": round(T_min, 2),
                    "Humedad": round(RH, 2),
                    "Radiacion": round(R_n, 2),
                    "Viento": round(u2, 2),  # Nuevo campo en la tabla
                    "ET0": round(ET0, 2)
                })
            except Exception as e:
                print(f"Error procesando datos para {fecha}: {str(e)}")

        return jsonify({'predicciones': predicciones})

    except Exception as e:
        return jsonify({'error': f'Error en la solicitud: {str(e)}'}), 500

@app.route('/exportar_csv', methods=['POST'])
def exportar_csv():
    try:
        data = request.json
        predicciones = data.get('predicciones', [])

        if not predicciones:
            return jsonify({'error': 'No hay datos para exportar'}), 400

        # Crear archivo CSV
        csv_filename = 'predicciones.csv'
        with open(csv_filename, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=predicciones[0].keys())
            writer.writeheader()
            for prediccion in predicciones:
                writer.writerow(prediccion)

        return send_file(csv_filename, as_attachment=True)

    except Exception as e:
        return jsonify({'error': f'Error al exportar CSV: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)