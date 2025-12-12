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