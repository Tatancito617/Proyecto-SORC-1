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
    # 1. Conexión y obtención de datos
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM lecturas_sensor WHERE parcela_id = %s ORDER BY fecha_registro DESC LIMIT 1", (parcela_id,))
    lectura = cursor.fetchone()
    
    cursor.execute("SELECT * FROM parcelas WHERE parcela_id = %s", (parcela_id,))
    parcela = cursor.fetchone()
    conn.close()

    if not lectura:
        return jsonify({"mensaje": "Faltan datos del sensor."})

    # 2. CLIMA (URLs LIMPIAS)
    clima_actual_desc = "Desconocido"
    resumen_pronostico = "No disponible"

    if parcela and parcela.get('latitud'):
        try:
            # Convertimos a float para evitar errores de espacios
            lat = float(parcela['latitud'])
            lon = float(parcela['longitud'])
            
            # --- AQUÍ ESTABA EL ERROR: URLs LIMPIAS ---
            # Asegúrate de que API_KEY_WEATHER esté definida arriba en tu archivo
            
            # A. Clima Actual
            url_now = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY_WEATHER}&units=metric&lang=es"
            
            res_now = requests.get(url_now, timeout=5)
            if res_now.status_code == 200:
                data_now = res_now.json()
                clima_actual_desc = f"{data_now['weather'][0]['description']}, {data_now['main']['temp']}°C"

            # B. Pronóstico
            url_forecast = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY_WEATHER}&units=metric&lang=es"
            
            res_fore = requests.get(url_forecast, timeout=5)
            if res_fore.status_code == 200:
                data_fore = res_fore.json()
                lista = data_fore['list']
                proyecciones = []
                # Tomamos índices 8 (24h), 16 (48h) y 24 (72h)
                for i in [8, 16, 24]: 
                    if i < len(lista):
                        item = lista[i]
                        fecha = item['dt_txt'].split(" ")[0]
                        desc = item['weather'][0]['description']
                        temp = item['main']['temp']
                        pop = item.get('pop', 0) * 100
                        proyecciones.append(f"- Día {fecha}: {desc}, {temp}°C (Lluvia: {int(pop)}%)")
                
                if proyecciones:
                    resumen_pronostico = "\n".join(proyecciones)

        except Exception as e:
            print(f"Error clima URL: {e}")

    # 4. PROMPT CORREGIDO (Sin Markdown)
    prompt = f"""
    Actúa como un Ingeniero Agrónomo experto. Tienes los siguientes datos reales de la parcela '{parcela['nombre']}':
    
    [DATOS SUELO]
    - pH: {lectura['ph']}
    - Humedad Suelo: {lectura['humedad_suelo']}%
    - Temperatura Suelo: {lectura['temperatura']}°C
    
    [DATOS CLIMA]
    - Actual: {clima_actual_desc}
    - Pronóstico (3 días): 
    {resumen_pronostico}

    [TAREA]
    Escribe un diagnóstico agronómico DETALLADO y REAL.
    Cruza los datos: Si el pH es malo, recomiendalo corregir. Si va a llover, no recomiendes regar.
    
    [FORMATO OBLIGATORIO]
    Responde ÚNICAMENTE con código HTML (sin markdown). Usa esta estructura exacta pero REEMPLAZA EL CONTENIDO con tu análisis:

    <h3>Informe Agronómico: {parcela['nombre']}</h3>
    
    <h4>🔍 Diagnóstico Integral</h4>
    <p>
    AQUÍ ESCRIBE TU ANÁLISIS: Explica detalladamente la relación entre el pH de {lectura['ph']} y la humedad actual. Menciona explícitamente si el pronóstico del clima ayuda o empeora la situación.
    </p>
    
    <h4>💧 Plan de Riego Inteligente</h4>
    <p>
    AQUÍ ESCRIBE TU PLAN: Da instrucciones precisas de riego basadas en la probabilidad de lluvia que te mostré arriba. ¿Se debe regar hoy o esperar?
    </p>

    <h4>🛠️ Manejo de Suelo y Cultivos</h4>
    <p>
    AQUÍ ESCRIBE TUS CONSEJOS: Recomienda qué hacer para corregir el pH (ej. encalado o acidificación) y sugiere 3 cultivos ideales para este suelo y clima específico.
    </p>
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": "Eres un sistema backend que devuelve HTML puro sin formato markdown."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=900, 
            temperature=0.7
        )
        
        recomendacion = response.choices[0].message.content
        
        # 5. LIMPIEZA DE SEGURIDAD (El truco final)
        # Si la IA desobedece y manda ```html, lo borramos a la fuerza.
        recomendacion = recomendacion.replace("```html", "").replace("```", "").strip()

        return jsonify({"recomendacion": recomendacion, "status": "success"})

    except Exception as e:
        print(f"Error OpenAI: {e}")
        return jsonify({"mensaje": "Error en el análisis inteligente."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)