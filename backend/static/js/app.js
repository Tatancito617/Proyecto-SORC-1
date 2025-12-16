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

function openModal(modalId) {
    document.getElementById(modalId).classList.add('show');
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
function verDetalleParcela(idParcela, nombre, lat, lon) {
    parcelaSeleccionada = idParcela;
    
    // Llenar datos estáticos
    document.getElementById('det-nombre-parcela').innerText = nombre;
    
    // Configurar Mapa
    const linkMap = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`;
    document.getElementById('btn-maps').href = linkMap;

    // SIMULAR CARGA DE DATOS (Backend)
    // Pronto aquí harás: fetch('/api/parcela/' + id + '/full-data')
    document.getElementById('val-temp').innerText = "22°C"; // Dato simulado
    document.getElementById('val-hum').innerText = "45%";   // Dato simulado
    document.getElementById('val-ph').innerText = "6.8";    // Dato simulado
    
    // Limpiar IA anterior
    document.getElementById('ai-result').style.display = 'none';
    
    mostrarNivel('detalle');
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