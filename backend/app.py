from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime
import requests

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
    print(f"--- Solicitando datos para parcela ID: {parcela_id} ---") # DEBUG
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Obtener datos de la parcela
    cursor.execute("SELECT * FROM parcelas WHERE parcela_id = %s", (parcela_id,))
    parcela = cursor.fetchone()

    # 2. Obtener sensor (Si falla, que no rompa todo)
    lectura = None
    if parcela:
        try:
            cursor.execute("""
                SELECT l.* FROM lecturas_sensor l
                JOIN sensores s ON l.sensor_id = s.sensor_id
                WHERE s.ubicacion LIKE %s 
                ORDER BY l.fecha_registro DESC LIMIT 1
            """, (f"%{parcela['nombre']}%",))
            lectura = cursor.fetchone()
        except Exception as e:
            print(f"Error buscando sensor: {e}")
    
    conn.close()

    # 3. CONEXIÓN A OPENWEATHER (Depurada)
    # Valores por defecto
    clima_info = None 

    if parcela and parcela.get('latitud') and parcela.get('longitud'):
        lat = parcela['latitud']
        lon = parcela['longitud']
        
        # IMPORTANTE: Asegúrate que esta variable esté definida arriba o impórtala
        # API_KEY_WEATHER = "TU_API_KEY_AQUI" 
        
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY_WEATHER}&units=metric&lang=es"
        
        print(f"Consultando Clima URL: {url}") # DEBUG: Copia esta URL y pégala en el navegador para ver si funciona

        try:
            response = requests.get(url)
            print(f"Status OpenWeather: {response.status_code}") # DEBUG: Debe ser 200

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
                print(f"Error API Clima: {response.text}") # DEBUG: Te dirá por qué falló (ej. 401 Unauthorized)
        except Exception as e:
            print(f"EXCEPTION conectando a OpenWeather: {e}") # DEBUG
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
@app.route('/api/v1/sensor-sync', methods=['POST'])
def recibir_lectura():
    try:
        data = request.get_json()
        if not data or 'sensor_id' not in data:
            return jsonify({"error": "Faltan datos"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO lecturas_sensor (sensor_id, temperatura, humedad_suelo, bateria_nivel, fecha_registro)
            VALUES (%s, %s, %s, %s, %s)
        """
        ahora = datetime.now()
        # Valores por defecto si faltan
        temp = data.get('temperatura', 0)
        hum = data.get('humedad_suelo', 0)
        bat = data.get('bateria', 100)

        cursor.execute(query, (data['sensor_id'], temp, hum, bat, ahora))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "mensaje": "Guardado"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)