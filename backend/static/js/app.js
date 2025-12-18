
// ==========================================
// 1. GESTIÓN DE SESIÓN Y NAVEGACIÓN
// ==========================================
function checkRut(rut) {
    var valor = rut.value.replace(/\./g,'').replace(/-/g,'');
    
    if (valor.length === 0) { return; }

    var cuerpo = valor.slice(0,-1);
    var dv = valor.slice(-1).toUpperCase();
    rut.value = cuerpo + '-'+ dv;

    if(cuerpo.length < 7) { rut.value = valor; return; }

    cuerpo = cuerpo.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    rut.value = cuerpo + '-' + dv;
}

async function handleLogin(event) {
    event.preventDefault();
    
    const rutInput = document.getElementById('rutInput');
    const rut = rutInput.value.trim(); 
    const password = document.getElementById('passwordInput').value.trim();
    const errorMsg = document.getElementById('loginError');

    if (rut.length < 8) {
        errorMsg.style.display = 'block';
        errorMsg.innerText = "El RUT ingresado es muy corto.";
        return;
    }

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rut: rut, password: password }) 
        });
        
        const data = await response.json();

        if (response.ok) {
            localStorage.setItem('usuarioActivo', JSON.stringify(data.usuario));
            window.location.href = "/dashboard"; 
        } else {
            errorMsg.style.display = 'block';
            errorMsg.innerText = data.mensaje || "Credenciales incorrectas";
        }
    } catch (error) {
        console.error("Error:", error);
        errorMsg.style.display = 'block';
        errorMsg.innerText = "Error de conexión con el servidor";
    }
}

function cerrarSesion() {
    localStorage.removeItem('usuarioActivo');
    
    window.location.href = "/logout";
}

function verPerfil() {
    const data = localStorage.getItem('usuarioActivo');
    if (data) {
        const u = JSON.parse(data);
        document.getElementById('perfilNombre').innerText = u.nombre;
        document.getElementById('perfilRut').innerText = u.rut;
        document.getElementById('perfilEmail').innerText = u.email;
        document.getElementById('perfilRol').innerText = u.rol;
        const modal = new bootstrap.Modal(document.getElementById('modalPerfil'));
        modal.show();
    } else {
        window.location.href = "/login";
    }
}

// INICIALIZACIÓN
document.addEventListener('DOMContentLoaded', () => {
    // Reloj
    const t = document.getElementById('currentDateTime');
    if(t) setInterval(() => { t.innerText = new Date().toLocaleString(); }, 1000);

    // Cargar Nombre Usuario
    const data = localStorage.getItem('usuarioActivo');
    if(data) {
        const u = JSON.parse(data);
        const lbl = document.getElementById('navNombreUsuario');
        if(lbl) lbl.innerText = u.nombre.split(' ')[0];
    } 

    // Navegación URL
    const path = window.location.pathname;
    if (path.includes('/agricultores')) mostrarSeccion('agricultores');
    else if (path.includes('/parcelas')) mostrarSeccion('parcelas');
    else mostrarSeccion('resumen');

    initCharts();
});

function mostrarSeccion(nombre) {
    const p = ['panel-resumen', 'panel-lista-agricultores', 'panel-lista-parcelas', 'panel-detalle-parcela'];
    p.forEach(id => { const el = document.getElementById(id); if(el) el.style.display = 'none'; });

    let id = 'panel-resumen';
    if(nombre === 'agricultores') id = 'panel-lista-agricultores';
    if(nombre === 'parcelas') id = 'panel-lista-parcelas';
    if(nombre === 'detalle') id = 'panel-detalle-parcela';
    
    const div = document.getElementById(id);
    if(div) div.style.display = 'block';
}

// ==========================================
// 2. GRÁFICOS
// ==========================================
function initCharts() {
    if (!window.datosGlobales) return;

    // Tarta
    const ctxPie = document.getElementById('graficoParcelas');
    if (ctxPie && window.datosGlobales.parcelas.length > 0) {
        const d = window.datosGlobales.parcelas;
        new Chart(ctxPie, {
            type: 'doughnut',
            data: {
                labels: d.map(p => p.nombre),
                datasets: [{
                    data: d.map(p => p.superficie_ha),
                    backgroundColor: ['#28a745', '#17a2b8', '#ffc107', '#dc3545', '#6f42c1'],
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    // Línea
    const ctxLine = document.getElementById('graficoLecturas');
    if (ctxLine && window.datosGlobales.lecturas.length > 0) {
        const d = [...window.datosGlobales.lecturas].reverse();
        new Chart(ctxLine, {
            type: 'line',
            data: {
                labels: d.map(l => new Date(l.fecha_registro).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})),
                datasets: [
                    { label: 'Temp', data: d.map(l => l.temperatura), borderColor: '#dc3545', fill: true, tension: 0.4 },
                    { label: 'Humedad', data: d.map(l => l.humedad_suelo), borderColor: '#0d6efd', fill: true, tension: 0.4 }
                ]
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: false } } }
        });
    }
}

// ==========================================
// 3. MAPAS Y NEGOCIO
// ==========================================
let map, marker;
function initMap() {
    if (map) return;
    map = L.map('mapaSelector').setView([-40.5725, -73.1353], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    map.on('click', function(e) {
        if (marker) marker.setLatLng(e.latlng); else marker = L.marker(e.latlng).addTo(map);
        document.getElementById('input_lat').value = e.latlng.lat.toFixed(6);
        document.getElementById('input_lon').value = e.latlng.lng.toFixed(6);
    });
}
async function buscarEnMapa() {
    const q = document.getElementById('buscadorMapa').value;
    if(!q) return;
    const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${q}`);
    const d = await r.json();
    if(d.length > 0) map.setView([d[0].lat, d[0].lon], 14);
}

// Agricultores y Parcelas
let agricultorActualID = null;

async function verParcelasDe(nombre, id) {
    agricultorActualID = id;
    const inp = document.getElementById('input_agri_id_parcela');
    if(inp) inp.value = id;
    
    document.getElementById('titulo-cliente').innerText = `Parcelas de ${nombre}`;
    const cont = document.getElementById('contenedor-parcelas');
    cont.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';
    
    mostrarSeccion('parcelas');

    try {
        const res = await fetch(`/api/agricultor/${id}/parcelas`);
        const data = await res.json();
        cont.innerHTML = '';

        if(data.length === 0) { cont.innerHTML = '<div class="alert alert-warning">Sin parcelas.</div>'; return; }

        data.forEach(p => {
            const div = document.createElement('div');
            div.className = 'col-md-4 mb-4';
            div.innerHTML = `
                <div class="card h-100 shadow-sm border-0">
                    <div class="card-body text-center">
                        <i class="fas fa-seedling fa-3x text-success mb-3"></i>
                        <h5 class="fw-bold">${p.nombre}</h5>
                        <p>${p.superficie_ha} ha</p>
                        <button class="btn btn-outline-primary w-100 mb-2" onclick="verDetalleParcela(${p.parcela_id})">Diagnosticar</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="borrarParcela(${p.parcela_id})"><i class="fas fa-trash"></i></button>
                    </div>
                </div>`;
            cont.appendChild(div);
        });
    } catch(e) { console.error(e); }
}

async function verDetalleParcela(id) {
    idParcelaActual = id;
    mostrarSeccion('detalle');
    document.getElementById('det-nombre-parcela').innerText = "Cargando...";
    const btnMaps = document.getElementById('btn-directions');
    btnMaps.style.display = 'none'; 
    btnMaps.href = '#';

    try {
        const res = await fetch(`/api/parcela/${id}/full-data`);
        const data = await res.json();
        document.getElementById('det-nombre-parcela').innerText = data.parcela?.nombre || 'Parcela';

        if (data.parcela && data.parcela.latitud && data.parcela.longitud) {
            const lat = data.parcela.latitud;
            const lon = data.parcela.longitud;
            
            btnMaps.href = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`;
            
            btnMaps.style.display = 'inline-flex'; 
        }
        
        const w = document.querySelector('.weather-widget');
        if(w && data.clima) {
            w.innerHTML = `<div class="card bg-info text-white p-3 d-flex justify-content-between align-items-center"><div><h2 class="mb-0">${data.clima.temp}°C</h2><span>${data.clima.desc}</span></div><img src="https://openweathermap.org/img/wn/${data.clima.icon}@2x.png" width="60"></div>`;
        }

        const l = data.lectura || {};
        document.getElementById('val-ph').innerText = l.ph || '--';
        document.getElementById('val-hum').innerText = (l.humedad_suelo || '--') + '%';
        document.getElementById('val-temp').innerText = (l.temperatura || '--') + '°C';

        // --- NUEVO: PINTAR EL CULTIVO ---
        if (data.cultivo) {
            document.getElementById('val-cultivo').innerText = data.cultivo.nombre;
            // Formatear fecha simple
            const fecha = new Date(data.cultivo.fecha_siembra).toLocaleDateString();
            document.getElementById('val-fecha-siembra').innerText = `Sembrado: ${fecha}`;
        } else {
            document.getElementById('val-cultivo').innerText = "Sin Cultivo";
            document.getElementById('val-fecha-siembra').innerText = "Suelo Desnudo";
        }
        // --------------------------------

        const btn = document.querySelector('.btn-ai');
        const box = document.getElementById('ai-result');
        if(box) { box.style.display='none'; box.innerHTML=''; }
        if(btn) {
            const nBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(nBtn, btn);
            nBtn.onclick = () => generarRecomendacion(id);
        }
    } catch(e) { console.error(e); }
}

async function generarRecomendacion(id) {
    const btn = document.querySelector('.btn-ai');
    const box = document.getElementById('ai-result');
    btn.disabled = true; btn.innerHTML = 'Analizando...';
    try {
        const res = await fetch(`/api/parcela/${id}/recomendacion-ia`, { method: 'POST' });
        const d = await res.json();
        box.style.display = 'block'; box.className = 'alert alert-light border mt-3';
        box.innerHTML = `<strong>Diagnóstico IA:</strong><br>${d.recomendacion || d.mensaje}`;
    } catch(e) { box.innerHTML = 'Error IA'; } finally { btn.disabled = false; btn.innerHTML = 'Generar Diagnóstico'; }
}

async function borrarParcela(id) {
    if(confirm("¿Eliminar?")) { await fetch(`/delete/parcela/${id}`, { method: 'POST' }); if(agricultorActualID) verParcelasDe('', agricultorActualID); else window.location.reload(); }
}

async function borrarAgricultor(id) {
    if(confirm("¿Eliminar agricultor?")) { await fetch(`/delete/agricultor/${id}`, { method: 'POST' }); window.location.reload(); }
}

function abrirEditarAgricultor(id, n, a, u) {
    document.getElementById('edit_agri_id').value = id;
    document.getElementById('edit_agri_nombre').value = n;
    document.getElementById('edit_agri_apellido').value = a;
    document.getElementById('edit_agri_ubicacion').value = u;
    const m = new bootstrap.Modal(document.getElementById('modalEditarAgricultor'));
    m.show();
}

function toggleCultivo(mostrar) {
    const div = document.getElementById('inputs-cultivo');
    div.style.display = mostrar ? 'block' : 'none';
    
    const inputs = div.querySelectorAll('input');
    inputs.forEach(input => input.required = mostrar);
}

let idParcelaActual = null;
function abrirModalRotacion() {
    console.log("Intentando rotar parcela ID:", idParcelaActual);
    
    if(!idParcelaActual) {
        alert("Error: No se ha cargado el ID de la parcela.");
        return;
    }
    
    document.getElementById('rotar_parcela_id').value = idParcelaActual;
    
    const myModal = new bootstrap.Modal(document.getElementById('modalRotacion'));
    myModal.show();
}