from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv() # Carga el archivo .env

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv('SECRET_KEY', 'clave_por_defecto_si_falla_el_env')
CORS(app)

# Clave de OpenWeather
API_KEY_WEATHER = os.getenv('OPENWEATHER_API_KEY')

# Clave de OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

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
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Recogemos los datos (incluyendo el RUT nuevo)
        rut = request.form['rut']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']
        ubicacion = request.form['ubicacion']

        # 2. Insertamos el RUT en la base de datos
        sql = """
            INSERT INTO agricultores (rut_agri, nombre, apellido, email, ubicacion) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (rut, nombre, apellido, email, ubicacion))
        conn.commit()
        
        flash('Agricultor agregado correctamente.', 'success')

    except mysql.connector.Error as err:
        # --- AQUÍ ESTÁ LA MAGIA ---
        # El código 1062 significa "Entrada Duplicada" en MySQL
        if err.errno == 1062:
            # Usamos categoría 'warning' para que salga amarillo (alerta) en vez de rojo
            flash(f'⚠️ Advertencia: El RUT {rut} ya se encuentra registrado en el sistema.', 'warning')
        else:
            flash(f'Error de base de datos: {err}', 'danger')
            print(f"Error DB: {err}")

    except Exception as e:
        flash(f'Error inesperado: {str(e)}', 'danger')
        print(f"Error Python: {e}")

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    return redirect("/agricultores")

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
    
    sql_parcela = "INSERT INTO parcelas (nombre, superficie_ha, latitud, longitud, agricultor_id) VALUES (%s, %s, %s, %s, %s)"
    val_parcela = (request.form['nombre'], request.form['superficie'], request.form['latitud'], request.form['longitud'], request.form['agricultor_id'])
    cursor.execute(sql_parcela, val_parcela)
    
    parcela_id = cursor.lastrowid

    tiene_cultivo = request.form.get('tiene_cultivo')
    
    if tiene_cultivo == 'si':
        nombre_cultivo = request.form['nombre_cultivo']
        fecha_siembra = request.form['fecha_siembra']
        
        sql_cultivo = "INSERT INTO cultivos (parcela_id, nombre, fecha_siembra, estado) VALUES (%s, %s, %s, 'activo')"
        cursor.execute(sql_cultivo, (parcela_id, nombre_cultivo, fecha_siembra))

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

@app.route('/api/parcela/rotar-cultivo', methods=['POST'])
def rotar_cultivo():
    parcela_id = request.form['parcela_id']
    accion = request.form['accion']
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE cultivos SET estado = 'cosechado' WHERE parcela_id = %s AND estado = 'activo'", (parcela_id,))
    
    if accion == 'nuevo':
        nombre = request.form['nuevo_nombre_cultivo']
        fecha = request.form['nueva_fecha_siembra']
        cursor.execute("INSERT INTO cultivos (parcela_id, nombre, fecha_siembra, estado) VALUES (%s, %s, %s, 'activo')", 
                       (parcela_id, nombre, fecha))
    
    conn.commit()
    conn.close()
    return redirect("/agricultores")

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

    cultivo = None
    if parcela:
        cursor.execute("SELECT * FROM cultivos WHERE parcela_id = %s AND estado = 'activo' LIMIT 1", (parcela_id,))
        cultivo = cursor.fetchone()

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
    
    return jsonify({ "parcela": parcela, "lectura": lectura, "clima": clima_info, "cultivo": cultivo })

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

    cursor.execute("SELECT * FROM cultivos WHERE parcela_id = %s AND estado = 'activo' LIMIT 1", (parcela_id,))
    cultivo_data = cursor.fetchone()
    conn.close()

    info_cultivo = "Suelo desnudo (Sin cultivo activo)"
    if cultivo_data:
        info_cultivo = f"CULTIVO ACTIVO: {cultivo_data['nombre']} (Sembrado: {cultivo_data['fecha_siembra']})"

    if not lectura:
        return jsonify({"mensaje": "Faltan datos del sensor."})

    # 2. CLIMA
    clima_actual_desc = "Desconocido"
    resumen_pronostico = "No disponible"

    if parcela and parcela.get('latitud'):
        try:
            lat = float(parcela['latitud'])
            lon = float(parcela['longitud'])
            
            # Clima Actual
            url_now = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY_WEATHER}&units=metric&lang=es"
            
            res_now = requests.get(url_now, timeout=5)
            if res_now.status_code == 200:
                data_now = res_now.json()
                clima_actual_desc = f"{data_now['weather'][0]['description']}, {data_now['main']['temp']}°C"

            # Pronóstico
            url_forecast = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY_WEATHER}&units=metric&lang=es"
            
            res_fore = requests.get(url_forecast, timeout=5)
            if res_fore.status_code == 200:
                data_fore = res_fore.json()
                lista = data_fore['list']
                proyecciones = []
                # 8 (24h), 16 (48h) y 24 (72h)
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

    # 4. PROMPT
    prompt = f"""
    Actúa como un Ingeniero Agrónomo experto. Tienes los siguientes datos reales de la parcela '{parcela['nombre']}':

    [CONTEXTO AGRÍCOLA]
    - {info_cultivo}  <-- ¡ESTO ES CLAVE!
    
    [DATOS SUELO]
    - pH: {lectura['ph']}
    - Humedad Suelo: {lectura['humedad_suelo']}%
    - Temperatura Suelo: {lectura['temperatura']}°C
    
    [DATOS CLIMA]
    - Actual: {clima_actual_desc}
    - Pronóstico (3 días): 
    {resumen_pronostico}

    [TAREA]
    IMPORTANTE: 
    Si hay cultivo, di si el pH y humedad actuales son buenos para ESE cultivo específico.
    Si NO hay cultivo, recomienda qué sembrar basándote en el suelo.
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
        
        # LIMPIEZA DE SEGURIDAD
        recomendacion = recomendacion.replace("```html", "").replace("```", "").strip()

        return jsonify({"recomendacion": recomendacion, "status": "success"})

    except Exception as e:
        print(f"Error OpenAI: {e}")
        return jsonify({"mensaje": "Error en el análisis inteligente."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)