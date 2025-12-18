from flask import Flask, request, jsonify, render_template, redirect, url_for
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

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        port=os.getenv('DB_PORT')
    )

# ==========================================
# LOGIN (API)
# ==========================================
@app.route('/api/login', methods=['POST'])
def login_api():
    try:
        data = request.get_json()
        rut = data.get('rut')
        password = data.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE rut = %s", (rut,))
        usuario = cursor.fetchone()
        conn.close() 
        
        if usuario and usuario['password'] == password:
            datos_usuario = {
                "nombre": usuario['nombre'],
                "rut": usuario['rut'],
                "email": usuario.get('email', 'No registrado'),
                "rol": usuario.get('rol', 'Agricultor')
            }
            return jsonify({"status": "success", "usuario": datos_usuario}), 200
        else:
            return jsonify({"status": "error", "mensaje": "Credenciales incorrectas"}), 401
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

# ==========================================
# VISTAS PRINCIPALES
# ==========================================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

# Todas estas rutas cargan el Dashboard para evitar error 404 al recargar
@app.route('/dashboard')
@app.route('/agricultores')
@app.route('/parcelas')
@app.route('/sensores')
@app.route('/cultivos')
@app.route('/mapa') 
def dashboard_page():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. KPIs
        cursor.execute("SELECT COUNT(*) as total FROM agricultores")
        n_agricultores = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM parcelas")
        n_parcelas = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM sensores")
        n_sensores = cursor.fetchone()['total']

        # 2. Listas Completas
        cursor.execute("SELECT * FROM agricultores ORDER BY agricultor_id DESC")
        lista_agricultores = cursor.fetchall()

        cursor.execute("SELECT * FROM parcelas ORDER BY parcela_id DESC")
        lista_parcelas = cursor.fetchall()

        # 3. Datos para Tabla "Últimas Lecturas"
        cursor.execute("""
            SELECT l.*, s.ubicacion 
            FROM lecturas_sensor l 
            LEFT JOIN sensores s ON l.sensor_id = s.sensor_id 
            ORDER BY l.fecha_registro DESC LIMIT 10
        """)
        tabla_lecturas = cursor.fetchall()
        cursor.execute("""
            SELECT temperatura, humedad_suelo, fecha_registro 
            FROM lecturas_sensor 
            ORDER BY fecha_registro DESC LIMIT 15
        """)
        grafico_lecturas = cursor.fetchall() 
        cursor.execute("SELECT nombre, superficie_ha FROM parcelas")
        grafico_parcelas = cursor.fetchall()

        conn.close()

        return render_template('dashboard.html', 
                               n_agricultores=n_agricultores,
                               n_parcelas=n_parcelas,
                               n_sensores=n_sensores,
                               agricultores=lista_agricultores,
                               parcelas=lista_parcelas,
                               tabla_lecturas=tabla_lecturas,
                               grafico_lecturas=grafico_lecturas,
                               grafico_parcelas=grafico_parcelas)
    except Exception as e:
        print(f"Error DB: {e}")
        return f"Error en base de datos: {str(e)}", 500

# ==========================================
# CRUD AGRICULTORES
# ==========================================

@app.route('/add/agricultor', methods=['POST'])
def add_agricultor():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO agricultores (nombre, apellido, email, ubicacion) VALUES (%s, %s, %s, %s)",
                   (request.form['nombre'], request.form['apellido'], request.form['email'], request.form['ubicacion']))
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
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE agricultores SET nombre=%s, apellido=%s, ubicacion=%s WHERE agricultor_id=%s",
                   (request.form['nombre'], request.form['apellido'], request.form['ubicacion'], request.form['agricultor_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard_page'))

# ==========================================
# CRUD PARCELAS Y APIs
# ==========================================

@app.route('/add/parcela', methods=['POST'])
def add_parcela():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO parcelas (nombre, superficie_ha, latitud, longitud, agricultor_id) VALUES (%s, %s, %s, %s, %s)",
                   (request.form['nombre'], request.form['superficie'], request.form['latitud'], request.form['longitud'], request.form['agricultor_id']))
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

@app.route('/api/agricultor/<int:id>/parcelas')
def get_parcelas_by_agricultor(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM parcelas WHERE agricultor_id = %s", (id,))
    parcelas = cursor.fetchall()
    conn.close()
    return jsonify(parcelas)

@app.route('/api/parcela/<int:parcela_id>/full-data')
def get_parcela_full_data(parcela_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM parcelas WHERE parcela_id = %s", (parcela_id,))
    parcela = cursor.fetchone()
    
    lectura = None
    if parcela:
        cursor.execute("SELECT * FROM lecturas_sensor WHERE parcela_id = %s ORDER BY fecha_registro DESC LIMIT 1", (parcela_id,))
        lectura = cursor.fetchone()
    conn.close()

    clima_info = None 
    if parcela and parcela.get('latitud'):
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={parcela['latitud']}&lon={parcela['longitud']}&appid={API_KEY_WEATHER}&units=metric&lang=es"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                d = resp.json()
                clima_info = { "temp": round(d['main']['temp'], 1), "desc": d['weather'][0]['description'], "icon": d['weather'][0]['icon'], "humedad": d['main']['humidity'] }
        except Exception: pass
    
    return jsonify({ "parcela": parcela, "lectura": lectura, "clima": clima_info })

@app.route('/api/sensor/lectura', methods=['POST'])
def recibir_lectura():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO lecturas_sensor (sensor_id, parcela_id, temperatura, humedad_suelo, ph, bateria_nivel, fecha_registro) VALUES (%s, %s, %s, %s, %s, %s, NOW())",
                       (data.get('sensor_id'), data.get('parcela_id'), data.get('temp'), data.get('hum'), data.get('ph'), data.get('bateria_nivel', 100)))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parcela/<int:parcela_id>/recomendacion-ia', methods=['POST'])
def get_recomendacion_ia(parcela_id):
    try:
        return jsonify({"recomendacion": "<b>Diagnóstico:</b> Suelo con pH estable.<br><b>Recomendación:</b> Monitorear riego.", "status": "success"})
    except Exception as e:
        return jsonify({"mensaje": "Error IA"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)