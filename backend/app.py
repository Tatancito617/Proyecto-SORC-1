from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime
import requests
import openai
from openai import OpenAI

client = OpenAI(api_key="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")

API_KEY_WEATHER = "942cb8c1379c7ac70368698f4554c245"

load_dotenv()

# Configuración de carpetas para Flask
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Conectar a la Base de Datos
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        port=os.getenv('DB_PORT')
    )

#Login
@app.route('/api/login', methods=['POST'])
def login_api():
    try:
        data = request.get_json()
        rut_recibido = data.get('rut')
        password_recibido = data.get('password')
        
        print(f"📩 Login: Buscando RUT '{rut_recibido}' con clave '{password_recibido}'")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Buscamos el usuario
        cursor.execute("SELECT * FROM usuarios WHERE rut = %s", (rut_recibido,))
        usuario = cursor.fetchone()
        conn.close() # Cerramos conexión rápido
        
        if usuario:
            print(f"✅ Usuario encontrado: {usuario['nombre']}")
            # COMPARACIÓN SIMPLE DE TEXTO
            if usuario['password'] == password_recibido:
                return jsonify({"status": "success", "nombre": usuario['nombre']}), 200
            else:
                print(f"❌ Clave incorrecta. BD dice: '{usuario['password']}'")
                return jsonify({"status": "error", "mensaje": "Contraseña incorrecta"}), 401
        else:
            print("❌ Usuario NO encontrado en la BD")
            return jsonify({"status": "error", "mensaje": "Usuario no encontrado"}), 404

    except Exception as e:
        print(f"💥 Error: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500

# VISTAS (PÁGINAS WEB)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard_page():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Obtener Contadores
        cursor.execute("SELECT COUNT(*) as total FROM agricultores")
        n_agricultores = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM parcelas")
        n_parcelas = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM sensores")
        n_sensores = cursor.fetchone()['total']

        # 2. Obtener LISTAS COMPLETAS
        cursor.execute("SELECT * FROM agricultores ORDER BY agricultor_id DESC")
        lista_agricultores = cursor.fetchall()

        cursor.execute("SELECT * FROM parcelas ORDER BY parcela_id DESC")
        lista_parcelas = cursor.fetchall()

        cursor.execute("SELECT * FROM sensores ORDER BY fecha_instalacion DESC")
        lista_sensores = cursor.fetchall()

        # 3. Lecturas
        cursor.execute("""
            SELECT l.*, s.ubicacion 
            FROM lecturas_sensor l 
            LEFT JOIN sensores s ON l.sensor_id = s.sensor_id 
            ORDER BY l.fecha_registro DESC LIMIT 10
        """)
        tabla_lecturas = cursor.fetchall()

        conn.close()

        return render_template('dashboard.html', 
                               n_agricultores=n_agricultores,
                               n_parcelas=n_parcelas,
                               n_sensores=n_sensores,
                               agricultores=lista_agricultores,
                               parcelas=lista_parcelas,
                               sensores=lista_sensores,
                               tabla_lecturas=tabla_lecturas)
    except Exception as e:
        print(f"Error: {e}")
        return "Error en base de datos", 500

from flask import redirect, url_for

# CRUD

@app.route('/add/agricultor', methods=['POST'])
def add_agricultor():
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    email = request.form['email']
    ubicacion = request.form['ubicacion']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO agricultores (nombre, apellido, email, ubicacion) 
        VALUES (%s, %s, %s, %s)
    """, (nombre, apellido, email, ubicacion))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard_page'))

@app.route('/delete/agricultor/<int:id>', methods=['POST'])
def delete_agricultor(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM agricultores WHERE agricultor_id = %s", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/edit/agricultor', methods=['POST'])
def edit_agricultor():
    id = request.form['agricultor_id']
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    ubicacion = request.form['ubicacion']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE agricultores 
        SET nombre=%s, apellido=%s, ubicacion=%s 
        WHERE agricultor_id=%s
    """, (nombre, apellido, ubicacion, id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard_page'))

# --- CRUD PARCELAS ---

@app.route('/api/parcela/<int:parcela_id>/full-data')
def get_parcela_full_data(parcela_id):
    print(f"--- Solicitando datos para parcela ID: {parcela_id} ---")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener datos de la parcela
    cursor.execute("SELECT * FROM parcelas WHERE parcela_id = %s", (parcela_id,))
    parcela = cursor.fetchone()

    # Obtener sensor
    lectura = None
    if parcela:
        cursor.execute("""
            SELECT * FROM lecturas_sensor 
            WHERE parcela_id = %s 
            ORDER BY fecha_registro DESC LIMIT 1
        """, (parcela_id,))
        lectura = cursor.fetchone()

    conn.close()

    # CONEXIÓN A OPENWEATHER
    clima_info = None 

    if parcela and parcela.get('latitud') and parcela.get('longitud'):
        lat = parcela['latitud']
        lon = parcela['longitud']
        
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY_WEATHER}&units=metric&lang=es"
        
        print(f"Consultando Clima URL: {url}")

        try:
            response = requests.get(url)
            print(f"Status OpenWeather: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                clima_info = {
                    "temp": round(data['main']['temp'], 1),
                    "desc": data['weather'][0]['description'].capitalize(),
                    "icon": data['weather'][0]['icon'],
                    "humedad": data['main']['humidity'],
                    "viento": data['wind']['speed']
                }
            else:
                print(f"Error API Clima: {response.text}")
        except Exception as e:
            print(f"EXCEPTION conectando a OpenWeather: {e}")
    else:
        print("No se buscó clima: Faltan latitud/longitud o parcela no encontrada")

    # Devolvemos todo
    return jsonify({
        "parcela": parcela,
        "lectura": lectura,
        "clima": clima_info 
    })
    

@app.route('/add/parcela', methods=['POST'])
def add_parcela():
    # Ahora recibimos el ID del agricultor dueño
    agricultor_id = request.form['agricultor_id']
    nombre = request.form['nombre']
    superficie = request.form['superficie']
    lat = request.form['latitud']
    lon = request.form['longitud']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO parcelas (nombre, superficie_ha, latitud, longitud, agricultor_id) 
        VALUES (%s, %s, %s, %s, %s)
    """, (nombre, superficie, lat, lon, agricultor_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard_page'))

@app.route('/edit/parcela', methods=['POST'])
def edit_parcela():
    parcela_id = request.form['parcela_id']
    nombre = request.form['nombre']
    superficie = request.form['superficie']
    latitud = request.form['latitud']
    longitud = request.form['longitud']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE parcelas 
        SET nombre=%s, superficie_ha=%s, latitud=%s, longitud=%s
        WHERE parcela_id=%s
    """, (nombre, superficie, latitud, longitud, parcela_id))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard_page'))

@app.route('/delete/parcela/<int:id>', methods=['POST'])
def delete_parcela(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM parcelas WHERE parcela_id = %s", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# --- API PARA OBTENER PARCELAS DE UN AGRICULTOR ESPECÍFICO ---
@app.route('/api/agricultor/<int:id>/parcelas')
def get_parcelas_by_agricultor(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM parcelas WHERE agricultor_id = %s", (id,))
    parcelas = cursor.fetchall()
    conn.close()
    return jsonify(parcelas)

# API (PARA EL ESP32)
@app.route('/api/sensor/lectura', methods=['POST'])
def recibir_lectura():
    data = request.json
    
    # Validamos que lleguen los datos críticos
    parcela_id = data.get('parcela_id')
    sensor_id = data.get('sensor_id')
    
    if not parcela_id:
        return jsonify({"error": "Falta parcela_id"}), 400
        
    # Extraemos el resto (si no vienen, ponemos valores por defecto o None)
    temp = data.get('temp')
    hum = data.get('hum')
    ph = data.get('ph')
    bateria = data.get('bateria_nivel', 100) # Por defecto 100% si no se envía

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insertamos INCLUYENDO la batería y la parcela_id
        query = """
            INSERT INTO lecturas_sensor 
            (sensor_id, parcela_id, temperatura, humedad_suelo, ph, bateria_nivel, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        cursor.execute(query, (sensor_id, parcela_id, temp, hum, ph, bateria))
        conn.commit()
        
        return jsonify({
            "status": "success", 
            "mensaje": f"Lectura registrada en parcela {parcela_id}"
        }), 201

    except Exception as e:
        conn.rollback()
        print(f"Error al guardar lectura: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/parcela/<int:parcela_id>/recomendacion-ia', methods=['POST'])
def get_recomendacion_ia(parcela_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Recuperamos la ÚLTIMA lectura real
    cursor.execute("""
        SELECT * FROM lecturas_sensor 
        WHERE parcela_id = %s 
        ORDER BY fecha_registro DESC LIMIT 1
    """, (parcela_id,))
    lectura = cursor.fetchone()
    
    # 2. Recuperamos datos de la parcela
    cursor.execute("SELECT * FROM parcelas WHERE parcela_id = %s", (parcela_id,))
    parcela = cursor.fetchone()
    conn.close()

    if not lectura:
        return jsonify({"mensaje": "Faltan datos del sensor para analizar."})

    # 3. OBTENER EL CLIMA ACTUAL (Nuevo paso)
    clima_desc = "Desconocido"
    temp_amb = "Desconocida"
    humedad_amb = "Desconocida"

    if parcela and parcela.get('latitud') and parcela.get('longitud'):
        try:
            # Asegúrate de usar TU variable de API Key aquí
            # API_KEY_WEATHER = "TU_CLAVE_AQUI" 
            lat = parcela['latitud']
            lon = parcela['longitud']
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY_WEATHER}&units=metric&lang=es"
            
            res_clima = requests.get(url, timeout=5) # Timeout para que no se cuelgue
            if res_clima.status_code == 200:
                data_clima = res_clima.json()
                clima_desc = data_clima['weather'][0]['description']
                temp_amb = f"{data_clima['main']['temp']}°C"
                humedad_amb = f"{data_clima['main']['humidity']}%"
        except Exception as e:
            print(f"No se pudo obtener clima para IA: {e}")

    # 4. CONSTRUIR EL PROMPT AVANZADO
    prompt = f"""
    Actúa como un Ingeniero Agrónomo Senior y experto en edafología. 
    Analiza la siguiente situación para la parcela '{parcela['nombre']}':

    [DATOS DEL SUELO - SENSOR]
    - pH: {lectura['ph']} (Crucial: Evalúa acidez/alcalinidad)
    - Humedad Suelo: {lectura['humedad_suelo']}%
    - Temperatura Suelo: {lectura['temperatura']}°C

    [DATOS DEL ENTORNO - CLIMA ACTUAL]
    - Condición: {clima_desc}
    - Temp. Ambiente: {temp_amb}
    - Humedad Ambiente: {humedad_amb}

    [TU TAREA]
    Genera un informe técnico pero claro en formato HTML (usa <b>, <ul>, <li>, <br>).
    Estructura la respuesta en estas 3 secciones obligatorias:

    1. <b>🔍 Diagnóstico Integral:</b> Analiza cómo interactúa el pH del suelo con el clima actual. ¿Hay estrés hídrico? ¿Bloqueo de nutrientes?
    2. <b>🛠️ Plan de Manejo de Suelo:</b> Acciones concretas para corregir el pH (ej: encalado o acidificación) y manejo del riego según la humedad actual.
    3. <b>🌱 Recomendación de Cultivos:</b> Sugiere los 3 mejores cultivos para sembrar AHORA mismo considerando ESTE pH específico y ESTE clima. Explica brevemente por qué.

    No cortes la respuesta. Sé resolutivo.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": "Eres un asistente agronómico experto que da consejos prácticos y detallados."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,  # AUMENTADO: Para que no corte la respuesta
            temperature=0.7
        )
        
        recomendacion = response.choices[0].message.content
        return jsonify({"recomendacion": recomendacion, "status": "success"})

    except Exception as e:
        print(f"Error OpenAI: {e}")
        return jsonify({"mensaje": "La IA está saturada. Intenta de nuevo."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)