function checkRut(rut) {
    var valor = rut.value.replace('.','').replace('.','');
    valor = valor.replace('-','');
    var cuerpo = valor.slice(0,-1);
    var dv = valor.slice(-1).toUpperCase();
    rut.value = cuerpo + '-'+ dv;
    if(cuerpo.length < 7) { rut.value = valor; return; }
    rut.value = rut.value.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

// VALIDAR LOGIN
async function handleLogin(event) {
    event.preventDefault();
    const rut = document.getElementById('rutInput').value;
    const password = document.getElementById('passwordInput').value;
    const errorMsg = document.getElementById('loginError');

    try {
        // Petición al Backend
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rut: rut, password: password })
        });
        
        const data = await response.json();

        if (response.ok) {
            // Login Exitoso
            console.log("Bienvenido " + data.nombre);
            window.location.href = "/dashboard"; 
        } else {
            // Error (Contraseña incorrecta o usuario no existe)
            errorMsg.style.display = 'block';
            errorMsg.innerText = data.mensaje;
            // Animación de error
            document.querySelector('.login-card').animate([
                { transform: 'translateX(0)' }, { transform: 'translateX(-5px)' }, 
                { transform: 'translateX(5px)' }, { transform: 'translateX(0)' }
            ], { duration: 300 });
        }
    } catch (error) {
        console.error("Error de conexión:", error);
        errorMsg.style.display = 'block';
        errorMsg.innerText = "Error de conexión con el servidor";
    }
}

// RELOJ Y NAVEGACIÓN
document.addEventListener('DOMContentLoaded', () => {
    // Reloj
    const timeDisplay = document.getElementById('currentDateTime');
    if(timeDisplay) {
        setInterval(() => {
            timeDisplay.innerText = new Date().toLocaleString();
        }, 1000);
    }

    // Tabs del Sidebar
    document.querySelectorAll('.nav-item').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            
            button.classList.add('active');
            const viewId = button.getAttribute('data-view');
            const view = document.getElementById(viewId);
            if(view) view.classList.add('active');
        });
    });
});

let map, marker;

// 1. INICIALIZAR MAPA (Llamar a esta función cuando se abra el modal)
function initMap() {
    // Si el mapa ya existe, no lo creamos de nuevo
    if (map) return; 

    // Coordenadas iniciales (Osorno)
    map = L.map('mapaSelector').setView([-40.5725, -73.1353], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Evento: Al hacer clic en el mapa
    map.on('click', function(e) {
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;

        // Mover el marcador
        if (marker) {
            marker.setLatLng(e.latlng);
        } else {
            marker = L.marker(e.latlng).addTo(map);
        }

        // Llenar los inputs del formulario
        document.getElementById('input_lat').value = lat.toFixed(6);
        document.getElementById('input_lon').value = lng.toFixed(6);
    });
}

// 2. BUSCADOR DE CIUDAD (Nominatim API - Gratis)
async function buscarEnMapa() {
    const query = document.getElementById('buscadorMapa').value;
    if(!query) return;

    try {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
        const data = await response.json();

        if (data && data.length > 0) {
            const lat = data[0].lat;
            const lon = data[0].lon;
            map.setView([lat, lon], 14); // Mover mapa al lugar encontrado
        } else {
            alert("Lugar no encontrado 😅");
        }
    } catch (error) {
        console.error("Error buscando lugar:", error);
    }
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('show');
    
    if(modalId === 'modalParcela') {
        // Truco: Esperar un poco a que el modal sea visible para cargar el mapa
        setTimeout(() => {
            initMap();
            map.invalidateSize(); // Arregla el error de que el mapa se ve gris
        }, 200);
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

// Cerrar si hacen clic fuera de la ventanita
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
}

// --- LÓGICA DE NAVEGACIÓN JERÁRQUICA ---

let parcelaSeleccionada = null; // Guardará el ID para usarlo en la IA

// 1. Función para cambiar entre niveles (Ocultar/Mostrar divs)
function mostrarNivel(nivel) {
    // Ocultar todo
    document.getElementById('panel-lista-agricultores').style.display = 'none';
    document.getElementById('panel-lista-parcelas').style.display = 'none';
    document.getElementById('panel-detalle-parcela').style.display = 'none';

    // Mostrar el deseado
    if (nivel === 'agricultores') document.getElementById('panel-lista-agricultores').style.display = 'block';
    if (nivel === 'parcelas') document.getElementById('panel-lista-parcelas').style.display = 'block';
    if (nivel === 'detalle') document.getElementById('panel-detalle-parcela').style.display = 'block';
}

// 2. Al hacer clic en un Agricultor
function verParcelasDe(nombreAgricultor, idAgricultor) {
    document.getElementById('titulo-cliente').innerText = `Parcelas de ${nombreAgricultor}`;
    const contenedor = document.getElementById('contenedor-parcelas');
    
    // AQUÍ PRONTO HAREMOS: fetch('/api/agricultor/' + id + '/parcelas')
    // POR AHORA: Simulamos tarjetas para ver el diseño
    contenedor.innerHTML = `
        <div class="stat-card card-hover" onclick="verDetalleParcela(101, 'Parcela Los Pinos', -40.57, -73.13)">
            <h3 style="color: var(--primary-green);">Parcela Los Pinos</h3>
            <p>🌽 Maíz • 15 ha</p>
            <button class="btn--primary" style="margin-top:10px; width:100%">Diagnosticar 🩺</button>
        </div>
        <div class="stat-card card-hover" onclick="verDetalleParcela(102, 'Parcela El Bajo', -40.60, -73.10)">
            <h3 style="color: #e67e22;">Parcela El Bajo</h3>
            <p>🌾 Trigo • 8 ha</p>
            <button class="btn--primary" style="margin-top:10px; width:100%">Diagnosticar 🩺</button>
        </div>
    `;
    
    mostrarNivel('parcelas');
}

// 3. Al hacer clic en una Parcela (Vista Final)
async function verDetalleParcela(idParcela) {
    // ... (Tu código de mostrar div 'detalle') ...
    mostrarNivel('detalle');
    document.getElementById('det-nombre-parcela').innerText = "Cargando...";

    try {
        const res = await fetch(`/api/parcela/${idParcela}/full-data`);
        
        // Verificación: Si la respuesta no es OK, lanzamos error
        if (!res.ok) throw new Error("Error al obtener datos del servidor");

        const data = await res.json();
        
        // Muestra en la consola qué datos llegaron realmente (para depurar)
        console.log("Datos recibidos:", data);

        // 1. Datos Básicos
        // Usamos ?. (optional chaining) para evitar errores si 'parcela' no existe
        document.getElementById('det-nombre-parcela').innerText = data.parcela?.nombre || "Sin nombre";
        
        // 2. CLIMA REAL
        const climaWidget = document.querySelector('.weather-widget');
        
        // Verificamos que el widget exista Y que hayan llegado datos de clima
        if (climaWidget && data.clima) {
            climaWidget.innerHTML = `
                <img src="https://openweathermap.org/img/wn/${data.clima.icon}@2x.png" alt="Icono" style="width: 60px;">
                <div class="weather-info">
                    <span class="temp">${data.clima.temp}°C</span>
                    <span class="desc">${data.clima.desc}</span>
                    <small>Humedad: ${data.clima.humedad}% | Viento: ${data.clima.viento} m/s</small>
                </div>
            `;
        } else {
            console.error("No se encontró el widget o no hay datos de clima");
            if(climaWidget) climaWidget.innerHTML = "<p>Datos del clima no disponibles</p>";
        }

        // 3. Link Google Maps
        // Asegúrate que lat y lon sean números válidos
        const lat = data.parcela?.latitud;
        const lon = data.parcela?.longitud;

        if (lat && lon) {
            // CORRECCIÓN PRINCIPAL AQUÍ:
            const mapsUrl = `https://www.google.com/maps?q=${lat},${lon}`;

            const btnMap = document.getElementById('btn-maps');
            if (btnMap) {
                btnMap.href = mapsUrl;
                btnMap.target = "_blank"; 
                console.log("Link generado:", mapsUrl); // Para verificar en consola
            }
        }

        // ... (El resto de tu código de sensores e IA) ...

    } catch (error) {
        console.error("Falló la función verDetalleParcela:", error);
        document.getElementById('det-nombre-parcela').innerText = "Error de carga";
    }
}

// 4. Botón de IA
function generarRecomendacion() {
    const btn = document.querySelector('.btn-ai');
    const caja = document.getElementById('ai-result');
    
    btn.disabled = true;
    btn.innerText = "Pensando... 🧠";
    
    // Simulación de espera de API
    setTimeout(() => {
        caja.style.display = 'block';
        caja.innerHTML = `
            <strong>💡 Recomendación:</strong><br>
            El pH de 6.8 es óptimo para el Maíz. Sin embargo, la humedad del 45% es baja considerando el clima despejado. Se recomienda riego por goteo esta tarde.
        `;
        btn.innerText = "✨ Generar Diagnóstico IA";
        btn.disabled = false;
    }, 2000);
}

let agricultorActualID = null; // Variable global para saber en qué carpeta estamos

// 1. ABRIR PARCELAS (Y guardar el ID del agricultor)
async function verParcelasDe(nombre, id) {
    agricultorActualID = id; // Guardamos el ID en memoria
    
    // Ponemos el ID en el formulario oculto de "Nueva Parcela" automáticamente
    document.getElementById('input_agri_id_parcela').value = id; 
    
    document.getElementById('titulo-cliente').innerText = `Parcelas de ${nombre}`;
    const contenedor = document.getElementById('contenedor-parcelas');
    contenedor.innerHTML = '<p>Cargando...</p>';

    mostrarNivel('parcelas'); // Tu función de cambiar vista

    // LLAMADA REAL A LA BD
    const response = await fetch(`/api/agricultor/${id}/parcelas`);
    const parcelas = await response.json();

    contenedor.innerHTML = ''; // Limpiar
    
    if(parcelas.length === 0) {
        contenedor.innerHTML = '<p>Este agricultor no tiene parcelas aún.</p>';
        return;
    }

    parcelas.forEach(p => {
        // Creamos la tarjeta HTML
        const card = document.createElement('div');
        card.className = 'stat-card card-hover';
        card.innerHTML = `
            <h3>${p.nombre}</h3>
            <p>${p.superficie_ha} ha</p>
            <div style="margin-top:10px;">
                <button class="btn--primary" onclick="verDetalleParcela(${p.parcela_id}, '${p.nombre}', ${p.latitud}, ${p.longitud})">Ver Datos</button>
                <button class="btn-icon danger" onclick="borrarParcela(${p.parcela_id})">🗑️</button>
            </div>
        `;
        contenedor.appendChild(card);
    });
}

// 2. FUNCIONES DE BORRAR
async function borrarAgricultor(id) {
    if(!confirm("¿Seguro? Se borrarán también todas sus parcelas.")) return;
    
    await fetch(`/delete/agricultor/${id}`, { method: 'POST' });
    window.location.reload(); // Recargar para ver cambios
}

async function borrarParcela(id) {
    if(!confirm("¿Borrar parcela?")) return;
    
    await fetch(`/delete/parcela/${id}`, { method: 'POST' });
    // Recargamos solo la vista de parcelas (truco rápido: recargar página)
    window.location.reload();
}

// 3. FUNCIÓN EDITAR AGRICULTOR
function abrirEditarAgricultor(id, nombre, apellido, ubicacion) {
    // Rellenamos el modal con los datos actuales
    document.getElementById('edit_agri_id').value = id;
    document.getElementById('edit_agri_nombre').value = nombre;
    document.getElementById('edit_agri_apellido').value = apellido;
    document.getElementById('edit_agri_ubicacion').value = ubicacion;
    
    openModal('modalEditarAgricultor');
}