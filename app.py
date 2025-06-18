from flask import Flask, render_template, request, jsonify, send_file
import requests
import math
import datetime
import csv
import os
import pandas as pd
import json

app = Flask(__name__)

# Clave de API de meteoblue (reemplázala con la tuya)
API_KEY = "Dtj1cl64zpfdXZgS"

# Función para obtener datos de Meteoblue
def obtener_datos_meteoblue(lat, lon):
    url = f"https://my.meteoblue.com/packages/basic-day?apikey={API_KEY}&lat={lat}&lon={lon}&asl=100&format=json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        datos = response.json()
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

import math

def calcular_et0_hargreaves(tmax, tmin, latitud, dia_juliano):
    tmedia = (tmax + tmin) / 2
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * dia_juliano)
    delta = 0.409 * math.sin((2 * math.pi / 365 * dia_juliano) - 1.39)
    phi = math.radians(latitud)
    ws = math.acos(-math.tan(phi) * math.tan(delta))
    ra = (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )
    et0 = 0.0023 * (tmedia + 17.8) * math.sqrt(tmax - tmin) * ra
    return round(et0, 2)

def detectar_alertas_predictivas(parametros, tb=13, umbral_gd=18, dias_consecutivos=3):
    tmax_list = parametros.get("temperature_max", [])
    tmin_list = parametros.get("temperature_min", [])
    num_dias = min(len(tmax_list), len(tmin_list))
    
    alerta_dias = []
    dias_criticos = 0

    for i in range(num_dias):
        tmax = tmax_list[i]
        tmin = tmin_list[i]
        if tmax is None or tmin is None:
            dias_criticos = 0
            alerta_dias.append(None)
            continue
        tx = (tmax + tmin) / 2
        gd = max(tx - tb, 0)
        alerta_dias.append(round(gd, 2))
        if gd >= umbral_gd:
            dias_criticos += 1
            if dias_criticos >= dias_consecutivos:
                return True, alerta_dias
        else:
            dias_criticos = 0

    return False, alerta_dias

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
                fecha_obj = datetime.datetime.today() + datetime.timedelta(days=i)
                dia_juliano = fecha_obj.timetuple().tm_yday
                fecha = fecha_obj.strftime("%d-%m-%Y")

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

                # Calcular ET₀ usando Hargreaves
                ET0 = calcular_et0_hargreaves(T_max, T_min, lat, dia_juliano)

                predicciones.append({
                    "fecha": fecha,
                    "T_max": round(T_max, 2),
                    "T_min": round(T_min, 2),
                    "Humedad": round(RH, 2),
                    "Radiacion": round(R_n, 2),
                    "Viento": round(u2, 2),  # Nuevo campo en la tabla
                    "ET0": ET0
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

        # Crear el archivo CSV en memoria
        from io import StringIO
        import csv

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["fecha", "T_max", "T_min", "Humedad", "Radiacion", "Viento", "ET0"])
        writer.writeheader()
        writer.writerows(predicciones)

        # Configurar la respuesta con el archivo CSV
        response = app.response_class(
            response=output.getvalue(),
            mimetype='text/csv'  # Cambiar el encabezado Content-Type a 'text/csv'
        )
        response.headers['Content-Disposition'] = 'attachment; filename=predicciones.csv'
        return response

    except Exception as e:
        return jsonify({'error': f'Error al exportar CSV: {str(e)}'}), 500

@app.route('/grados-dia', methods=['GET', 'POST'])
def grados_dia():
    try:
        # Si la solicitud es GET, obtener los parámetros de la URL
        if request.method == 'GET':
            lat = request.args.get('lat')
            lon = request.args.get('lon')
        else:  # Si la solicitud es POST, obtener los datos del cuerpo de la solicitud
            data = request.json
            lat = data.get('lat')
            lon = data.get('lon')

        # Validar que lat y lon no sean None o vacíos
        if not lat or not lon:
            return jsonify({'error': 'Latitud y longitud son requeridas'}), 400

        lat = float(lat)
        lon = float(lon)

        # Obtener datos de predicción desde la API de Meteoblue
        datos_meteoblue = obtener_datos_meteoblue(lat, lon)

        if not datos_meteoblue:
            return jsonify({'error': 'No se pudieron obtener datos de meteoblue'}), 500

        parametros = datos_meteoblue.get("data_day", {})

        # Validar que existan datos suficientes
        num_dias = min(
            len(parametros.get("temperature_max", [])),
            len(parametros.get("temperature_min", []))
        )

        if num_dias == 0:
            return jsonify({'error': 'No hay datos suficientes en meteoblue'}), 500

        # Calcular grados día
        tb = 13  # Temperatura base
        gd_dias = []
        fechas = []
        valores_gd = []
        temperaturas_promedio = []
        acumulado = 0
        alerta = False

        for i in range(num_dias):
            fecha = (datetime.datetime.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            tmax = parametros.get("temperature_max", [None] * num_dias)[i]
            tmin = parametros.get("temperature_min", [None] * num_dias)[i]

            if tmax is None or tmin is None:
                continue

            tx = (tmax + tmin) / 2
            gd = max(tx - tb, 0)
            acumulado += gd
            if gd >= 18:
                alerta = True
            gd_dias.append({'Fecha': fecha, 'GD': round(gd, 2)})
            fechas.append(fecha)
            valores_gd.append(round(gd, 2))
            temperaturas_promedio.append(round(tx, 2))

        # Detectar alerta predictiva
        alerta_predictiva, lista_gd = detectar_alertas_predictivas(parametros)

        return render_template(
            'grados_dias.html',
            datos=gd_dias,
            total_gd=round(acumulado, 2),
            alerta=alerta,  # alerta por días individuales
            alerta_predictiva=alerta_predictiva,  # NUEVA alerta por días consecutivos
            fechas=fechas,
            valores_gd=valores_gd,
            temperaturas_promedio=temperaturas_promedio
        )

    except Exception as e:
        return jsonify({'error': f'Error al calcular grados día: {str(e)}'}), 500

@app.route('/prever-gd', methods=['POST'])
def prever_gd():
    try:
        data = request.json
        lat = float(data['lat'])
        lon = float(data['lon'])

        # Obtener datos de predicción desde la API de Meteoblue
        datos_meteoblue = obtener_datos_meteoblue(lat, lon)

        if not datos_meteoblue:
            return jsonify({'error': 'No se pudieron obtener datos de meteoblue'}), 500

        parametros = datos_meteoblue.get("data_day", {})

        # Validar que existan datos suficientes
        num_dias = min(
            len(parametros.get("temperature_max", [])),
            len(parametros.get("temperature_min", []))
        )

        if num_dias == 0:
            return jsonify({'error': 'No hay datos suficientes en meteoblue'}), 500

        # Calcular grados día
        tb = 13  # Temperatura base
        acumulado = 0
        alerta = False

        for i in range(num_dias):
            tmax = parametros.get("temperature_max", [None] * num_dias)[i]
            tmin = parametros.get("temperature_min", [None] * num_dias)[i]

            if tmax is None or tmin is None:
                continue

            tx = (tmax + tmin) / 2
            gd = max(tx - tb, 0)
            acumulado += gd
            if gd >= 18:
                alerta = True

        return jsonify({'alerta': alerta, 'gd': round(acumulado, 2)})

    except Exception as e:
        return jsonify({'error': f'Error al prever grados día: {str(e)}'}), 500

# Nuevo endpoint para subir archivo CSV con alturas y generar proyecciones
@app.route('/subir-alturas')
def subir_alturas_form():
    return '''
    <!doctype html>
    <title>Subir archivo de alturas</title>
    <h1>📤 Cargar CSV de alturas desde Power BI</h1>
    <form action="/procesar-alturas" method="post" enctype="multipart/form-data">
      <input type="file" name="archivo">
      <input type="submit" value="Cargar">
    </form>
    '''

@app.route('/procesar_alturas', methods=['POST'])
def procesar_alturas():
    if 'archivo' not in request.files:
        return "No se subió ningún archivo."

    archivo = request.files['archivo']
    if archivo.filename == '':
        return "Nombre de archivo vacío."

    if archivo:
        df = pd.read_csv(archivo)

        columnas_requeridas = {'Fecha', 'Local', 'MG', 'Individuo', 'Altura'}
        if not columnas_requeridas.issubset(df.columns):
            return f"Faltan columnas necesarias: {columnas_requeridas - set(df.columns)}"

        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha'])

        # Diccionario de ubicaciones con latitud y longitud
        ubicaciones = {
            "Local1": {"lat": -33.0, "lon": -56.0},
            "Local2": {"lat": -34.5, "lon": -57.5},
            "Local3": {"lat": -32.8, "lon": -55.2},
            # Agrega más ubicaciones según sea necesario
        }

        # Calcular grados día reales
        gd_reales = []
        for _, row in df.iterrows():
            fecha = row['Fecha']
            local = row['Local']

            if local not in ubicaciones:
                gd_reales.append(None)
                continue

            lat = ubicaciones[local]['lat']
            lon = ubicaciones[local]['lon']

            # Obtener datos de Meteoblue
            datos_meteoblue = obtener_datos_meteoblue(lat, lon)
            if not datos_meteoblue:
                gd_reales.append(None)
                continue

            parametros = datos_meteoblue.get("data_day", {})
            tmax_list = parametros.get("temperature_max", [])
            tmin_list = parametros.get("temperature_min", [])

            # Buscar el índice correspondiente a la fecha
            fecha_actual = datetime.datetime.strptime(fecha.strftime('%Y-%m-%d'), '%Y-%m-%d')
            indice = (fecha_actual - datetime.datetime.today()).days

            if 0 <= indice < len(tmax_list):
                tmax = tmax_list[indice]
                tmin = tmin_list[indice]
                if tmax is not None and tmin is not None:
                    tx = (tmax + tmin) / 2
                    gd = max(tx - 13, 0)  # Temperatura base = 13
                    gd_reales.append(gd)
                else:
                    gd_reales.append(None)
            else:
                gd_reales.append(None)

        # Agregar los grados día reales al DataFrame
        df['GD acumulado'] = gd_reales
        print("Grados día calculados:", gd_reales)

        # Verificar el contenido del DataFrame
        print("Contenido del DataFrame después de agregar GD acumulado:", df)

        proyecciones = []
        series_chart = []

        for (local, mg), grupo in df.groupby(['Local', 'MG']):
            # Filtrar filas con valores válidos
            grupo = grupo.dropna(subset=['GD acumulado', 'Altura'])
            if len(grupo) < 2:
                continue

            x = grupo['GD acumulado']
            y = grupo['Altura']
            fechas = grupo['Fecha'].dt.strftime('%Y-%m-%d').tolist()

            # Validar que x e y tengan al menos dos valores válidos
            if len(x) < 2 or len(y) < 2:
                continue

            coef = pd.Series(y).corr(x)
            pendiente = (y.iloc[-1] - y.iloc[0]) / (x.iloc[-1] - x.iloc[0])
            gd_futuro = x.iloc[-1] + 30
            altura_futura = y.iloc[-1] + pendiente * 30

            proyecciones.append({
                'Local': local,
                'MG': mg,
                'Altura actual': y.iloc[-1],
                'GD actual': x.iloc[-1],
                'Altura proyectada (30 días)': round(altura_futura, 2),
                'Pendiente estimada': round(pendiente, 3),
                'Correlación GD-Altura': round(coef, 2)
            })
            series_chart.append({
                'label': f'{local} - {mg}',
                'data': y.tolist(),
                'fill': False
            })

        # Verificar las proyecciones y los datos del gráfico
        print("Proyecciones generadas:", proyecciones)
        print("Datos para el gráfico:", series_chart)

        # Agregar las fechas únicas ordenadas para el gráfico
        fechas_unicas = sorted(df['Fecha'].dt.strftime('%Y-%m-%d').unique().tolist())
        print("Fechas únicas para el gráfico:", fechas_unicas)

        html = '''
        <!doctype html>
        <html>
        <head>
        <title>Proyección de Altura</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
        <h2>📊 Proyección de crecimiento por MG y Local</h2>
        <table border="1" cellpadding="6" style="border-collapse: collapse;">
          <tr>
            <th>Local</th>
            <th>MG</th>
            <th>Altura actual</th>
            <th>GD actual</th>
            <th>Altura proyectada (30 días)</th>
            <th>Pendiente estimada</th>
            <th>Correlación GD-Altura</th>
          </tr>
        '''
        for fila in proyecciones:
            html += f"<tr><td>{fila['Local']}</td><td>{fila['MG']}</td><td>{fila['Altura actual']}</td><td>{fila['GD actual']}</td><td>{fila['Altura proyectada (30 días)']}</td><td>{fila['Pendiente estimada']}</td><td>{fila['Correlación GD-Altura']}</td></tr>"
        html += "</table><br><h3>📈 Evolución de Altura</h3><canvas id='graficoAltura'></canvas><br><a href='/subir-alturas'>⬅️ Volver</a>"
        html += f"""
        <script>
        const ctx = document.getElementById('graficoAltura').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(fechas_unicas)},
                datasets: {json.dumps(series_chart)}
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: false }},
                    x: {{ title: {{ display: true, text: 'Fecha' }} }}
                }}
            }}
        }});
        </script>
        </body>
        </html>
        """
        return html

# Nuevo endpoint para subir archivos de alturas y temperaturas históricas
@app.route('/subir-alturas-y-temperaturas')
def subir_alturas_y_temperaturas_form():
    return '''
    <!doctype html>
    <title>Subir archivos</title>
    <h1>📤 Cargar CSV de alturas y temperaturas</h1>
    <form action="/procesar-alturas-y-temperaturas" method="post" enctype="multipart/form-data">
      <label>Alturas CSV:</label><br>
      <input type="file" name="archivo_alturas"><br><br>
      <label>Temperaturas CSV (con columnas Fecha, Tmax, Tmin):</label><br>
      <input type="file" name="archivo_temp"><br><br>
      <input type="submit" value="Cargar">
    </form>
    '''

@app.route('/procesar-alturas-y-temperaturas', methods=['POST'])
def procesar_alturas_y_temperaturas():
    if 'archivo_alturas' not in request.files or 'archivo_temp' not in request.files:
        return "Faltan archivos."

    archivo_alturas = request.files['archivo_alturas']
    archivo_temp = request.files['archivo_temp']

    df_alturas = pd.read_csv(archivo_alturas)
    df_temp = pd.read_csv(archivo_temp)

    # Validación mínima
    if not {'Fecha', 'Tmax', 'Tmin'}.issubset(df_temp.columns):
        return "El archivo de temperaturas debe tener columnas: Fecha, Tmax, Tmin"
    if not {'Fecha', 'Local', 'MG', 'Individuo', 'Altura'}.issubset(df_alturas.columns):
        return "El archivo de alturas debe tener columnas: Fecha, Local, MG, Individuo, Altura"

    # Convertir fechas
    df_alturas['Fecha'] = pd.to_datetime(df_alturas['Fecha'])
    df_temp['Fecha'] = pd.to_datetime(df_temp['Fecha'])

    # Calcular GD = ((Tmax + Tmin)/2 - 13) con límite inferior 0
    df_temp['GD'] = ((df_temp['Tmax'] + df_temp['Tmin']) / 2 - 13).clip(lower=0)

    # Unir por fecha
    df = df_alturas.merge(df_temp[['Fecha', 'GD']], on='Fecha', how='left')

    # GD acumulado por grupo
    df['GD acumulado'] = df.groupby(['Local', 'MG', 'Individuo'])['GD'].cumsum()

    # Proyección lineal simple
    resultados = []
    for (local, mg), grupo in df.groupby(['Local', 'MG']):
        if len(grupo) < 2:
            continue
        x = grupo['GD acumulado']
        y = grupo['Altura']
        pendiente = (y.iloc[-1] - y.iloc[0]) / (x.iloc[-1] - x.iloc[0])
        altura_futura = y.iloc[-1] + pendiente * 30
        resultados.append({
            'Local': local,
            'MG': mg,
            'Altura actual': y.iloc[-1],
            'Altura proyectada (30 días)': round(altura_futura, 2),
            'Pendiente': round(pendiente, 3)
        })

    html = '<h2>📊 Resultados con temperaturas reales</h2><table border="1" cellpadding="5"><tr><th>Local</th><th>MG</th><th>Altura actual</th><th>Altura proyectada</th><th>Pendiente</th></tr>'
    for fila in resultados:
        html += f"<tr><td>{fila['Local']}</td><td>{fila['MG']}</td><td>{fila['Altura actual']}</td><td>{fila['Altura proyectada (30 días)']}</td><td>{fila['Pendiente']}</td></tr>"
    html += '</table><br><a href="/subir-alturas-y-temperaturas">⬅️ Volver</a>'
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)