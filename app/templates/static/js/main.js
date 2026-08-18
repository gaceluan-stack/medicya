// main.js - Medic YA

const API_BASE = '/api';

// Verificar si hay un token en localStorage
const token = localStorage.getItem('token');
const role = localStorage.getItem('role');
const email = localStorage.getItem('email');

// Capturar el parámetro de referido '?ref=XXX' de la URL y guardarlo
const urlParams = new URLSearchParams(window.location.search);
const refId = urlParams.get('ref');
if (refId) {
    localStorage.setItem('referido_por_id', refId);
    console.log("Patrocinador registrado desde enlace de referido:", refId);
}

// Inicializar la interfaz del navbar y paneles
window.addEventListener('DOMContentLoaded', () => {
    updateUserNavUI();
    
    // Si viene de referido, y no está logueado, abrir automáticamente el modal de registro
    if (refId && !token) {
        openRegisterModal();
    }
});

// Actualiza el Navbar según el estado de sesión del usuario
function updateUserNavUI() {
    const container = document.getElementById('nav-user-container');
    const b2cPanel = document.getElementById('paciente-b2c-panel');

    if (token) {
        if (role === 'PACIENTE') {
            container.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="text-right">
                        <p class="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Paciente Registrado</p>
                        <p class="text-xs text-gray-900 font-bold">${email}</p>
                    </div>
                    <button onclick="openProfileModal()" class="bg-brand-50 hover:bg-brand-100 text-brand-700 border border-brand-200/55 px-3 py-2 rounded-xl text-xs font-semibold transition-all shadow-sm flex items-center space-x-1">
                        <i class="fa-solid fa-user-gear text-xs"></i> <span>Mi Perfil</span>
                    </button>
                    <button onclick="handleLogout()" class="text-gray-500 hover:text-red-600 bg-white border border-gray-250 hover:border-red-200 px-3 py-2 rounded-xl transition-all shadow-sm">
                        <i class="fa-solid fa-power-off text-xs"></i>
                    </button>
                </div>
            `;
            if (b2cPanel) b2cPanel.classList.remove('hidden');
        } else {
            // Proveedor o Admin
            container.innerHTML = `
                <div class="flex items-center space-x-3">
                    <a href="/dashboard/${role.toLowerCase()}" class="bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all flex items-center space-x-1.5 shadow">
                        <i class="fa-solid fa-gauge"></i> <span>Mi Panel</span>
                    </a>
                    <button onclick="handleLogout()" class="text-gray-500 hover:text-red-600 bg-white border border-gray-250 px-3 py-2 rounded-xl transition-all shadow-sm">
                        <i class="fa-solid fa-power-off text-xs"></i>
                    </button>
                </div>
            `;
            if (b2cPanel) b2cPanel.classList.add('hidden');
        }
    } else {
        container.innerHTML = `
            <button onclick="openRegisterModal()" class="bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold px-4.5 py-2.5 rounded-xl transition-all shadow shadow-brand-500/10">
                <i class="fa-solid fa-user-plus mr-1.5"></i> Registro Rápido
            </button>
            <a href="/login" class="text-xs text-gray-500 hover:text-gray-900 font-bold py-2 transition-all">
                Ingreso Doctores
            </a>
        `;
        if (b2cPanel) b2cPanel.classList.add('hidden');
    }
}

function handleLogout() {
    localStorage.clear();
    window.location.href = '/';
}

// Control de modals
let currentAuthMode = 'register';

// Control de modals
function openRegisterModal(customMessage) {
    // Cargar referido si existe en localStorage
    const savedRef = localStorage.getItem('referido_por_id');
    if (savedRef) {
        document.getElementById('reg-referido-id').value = savedRef;
    }
    
    const bannerText = document.getElementById('register-promo-banner-text');
    if (bannerText) {
        if (customMessage) {
            bannerText.innerHTML = customMessage;
        } else {
            bannerText.innerHTML = "¡Regístrate en 30 segundos y recibe un <strong>Cupón de $5 USD</strong> para tu consulta!";
        }
    }
    
    document.getElementById('register-modal').classList.remove('hidden');
    switchAuthTab('register'); // Por defecto abre en registro
}

// Cerrar modal
function closeRegisterModal() {
    document.getElementById('register-modal').classList.add('hidden');
}

function switchAuthTab(mode) {
    currentAuthMode = mode;
    
    const banner = document.getElementById('register-promo-banner');
    const registerFields = document.getElementById('register-only-fields');
    const loginFields = document.getElementById('login-only-fields');
    const title = document.getElementById('auth-modal-title');
    const submitBtn = document.getElementById('auth-submit-btn');
    
    const tabRegister = document.getElementById('tab-auth-register');
    const tabLogin = document.getElementById('tab-auth-login');
    
    // Resetear visibilidad de sección de código al cambiar de pestaña
    document.getElementById('verification-code-section').classList.add('hidden');
    document.getElementById('reg-verification-code').value = "";
    
    if (mode === 'login') {
        banner.classList.add('hidden');
        registerFields.classList.add('hidden');
        loginFields.classList.remove('hidden');
        
        title.innerHTML = `<i class="fa-solid fa-right-to-bracket text-brand-500 mr-2"></i> Iniciar Sesión`;
        submitBtn.textContent = "Ingresar a mi Cuenta";
        
        tabRegister.className = "flex-1 py-3 text-center text-gray-450 hover:text-brand-500 transition-all outline-none cursor-pointer border-b border-gray-100";
        tabLogin.className = "flex-1 py-3 text-center text-brand-600 border-b-2 border-brand-500 font-bold transition-all outline-none cursor-pointer";
    } else {
        banner.classList.remove('hidden');
        registerFields.classList.remove('hidden');
        loginFields.classList.add('hidden');
        
        title.innerHTML = `<i class="fa-solid fa-user-plus text-brand-500 mr-2"></i> Registro de Paciente`;
        submitBtn.textContent = "Completar Registro Verificado";
        
        tabRegister.className = "flex-1 py-3 text-center text-brand-600 border-b-2 border-brand-500 font-bold transition-all outline-none cursor-pointer";
        tabLogin.className = "flex-1 py-3 text-center text-gray-450 hover:text-brand-500 transition-all outline-none cursor-pointer border-b border-gray-100";
    }
}

async function sendCode(tipo) {
    const destino = tipo === 'email' 
        ? document.getElementById('reg-email').value.trim() 
        : document.getElementById('reg-celular').value.trim();
        
    if (!destino) {
        alert(`Por favor, ingresa tu ${tipo === 'email' ? 'correo electrónico' : 'número de WhatsApp'} antes de solicitar el código.`);
        return;
    }
    
    const btn = document.getElementById(tipo === 'email' ? 'send-email-code-btn' : 'send-phone-code-btn');
    const oldText = btn.innerHTML;
    btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i>...`;
    btn.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE}/auth/enviar-codigo-verificacion`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ destino: destino, tipo: tipo })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Error al enviar código");
        
        showToast("Código Enviado", `El código ha sido enviado a tu ${tipo === 'email' ? 'correo' : 'WhatsApp'}.`);
        document.getElementById('verification-code-section').classList.remove('hidden');
    } catch(err) {
        alert(err.message);
    } finally {
        btn.innerHTML = oldText;
        btn.disabled = false;
    }
}

// Envío del Formulario (Registro o Login según la pestaña activa)
async function submitAuthForm(event) {
    event.preventDefault();
    
    if (currentAuthMode === 'login') {
        const destino = document.getElementById('login-destino').value.trim();
        const password = document.getElementById('login-password').value;
        if (!destino || !password) {
            alert("Por favor, ingresa tu correo o celular y tu contraseña.");
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE}/auth/login-paciente`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ destino: destino, password: password })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Error al iniciar sesión");
            
            // Guardar sesión
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('role', data.role);
            localStorage.setItem('email', destino);
            
            showToast("¡Sesión Iniciada!", "Bienvenido de vuelta a Medic YA.");
            closeRegisterModal();
            updateUserNavUI();
            window.location.reload();
        } catch (err) {
            alert(err.message);
        }
    } else {
        const code = document.getElementById('reg-verification-code').value.trim();
        const password = document.getElementById('reg-password').value;
        
        if (!code) {
            alert("Por favor, solicita y/o ingresa el código de verificación recibido.");
            return;
        }
        if (!password || password.length < 6) {
            alert("Por favor, crea una contraseña de al menos 6 caracteres.");
            return;
        }
        
        const payload = {
            nombres: document.getElementById('reg-nombres').value.trim(),
            apellidos: document.getElementById('reg-apellidos').value.trim(),
            cedula: document.getElementById('reg-cedula').value.trim(),
            celular_whatsapp: document.getElementById('reg-celular').value.trim(),
            email: document.getElementById('reg-email').value.trim(),
            password: password,
            origen_informacion: document.getElementById('reg-origen').value,
            referido_por_id: document.getElementById('reg-referido-id').value || null,
            verification_code: code
        };
        
        try {
            const response = await fetch(`${API_BASE}/auth/register-paciente`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Error al registrarse");
            
            // Guardar sesión
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('role', data.role);
            localStorage.setItem('email', payload.email);
            localStorage.removeItem('referido_por_id');
            
            showToast("¡Registro Exitoso!", "Tu cupón de $5 USD está listo en tu billetera.");
            closeRegisterModal();
            updateUserNavUI();
            window.location.reload();
        } catch (err) {
            alert(err.message);
        }
    }
}

// Funciones de Perfil de Paciente
async function openProfileModal() {
    document.getElementById('profile-modal').classList.remove('hidden');
    try {
        const response = await fetch(`${API_BASE}/pacientes/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error("No se pudo obtener el perfil");
        const p = await response.json();
        
        document.getElementById('prof-nombres').value = p.nombres || "";
        document.getElementById('prof-apellidos').value = p.apellidos || "";
        document.getElementById('prof-celular').value = p.celular_whatsapp || "";
        document.getElementById('prof-link-instagram').value = p.link_instagram || "";
        document.getElementById('prof-link-tiktok').value = p.link_tiktok || "";
        document.getElementById('prof-link-facebook').value = p.link_facebook || "";
    } catch(e) {
        console.error(e);
    }
}

function closeProfileModal() {
    document.getElementById('profile-modal').classList.add('hidden');
}

async function submitUpdateProfile(event) {
    event.preventDefault();
    const payload = {
        nombres: document.getElementById('prof-nombres').value.trim(),
        apellidos: document.getElementById('prof-apellidos').value.trim(),
        celular_whatsapp: document.getElementById('prof-celular').value.trim(),
        link_instagram: document.getElementById('prof-link-instagram').value.trim() || null,
        link_tiktok: document.getElementById('prof-link-tiktok').value.trim() || null,
        link_facebook: document.getElementById('prof-link-facebook').value.trim() || null
    };
    
    const urlPattern = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/i;
    if (payload.link_instagram && !urlPattern.test(payload.link_instagram)) return alert("Enlace de Instagram inválido");
    if (payload.link_tiktok && !urlPattern.test(payload.link_tiktok)) return alert("Enlace de TikTok inválido");
    if (payload.link_facebook && !urlPattern.test(payload.link_facebook)) return alert("Enlace de Facebook inválido");
    
    try {
        const response = await fetch(`${API_BASE}/pacientes/me/perfil`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || "Error al actualizar perfil");
        }
        
        showToast("Perfil Actualizado", "Tus datos y redes sociales se han guardado con éxito.");
        closeProfileModal();
        window.location.reload();
    } catch(err) {
        alert(err.message);
    }
}

// B2C Wallet / Cupones
let walletCoupons = [];

async function openWalletModal() {
    document.getElementById('wallet-modal').classList.remove('hidden');
    document.getElementById('qrcode-container').innerHTML = `
        <div class="w-32 h-32 flex items-center justify-center text-gray-400 text-center text-xs font-semibold">
            Selecciona un cupón activo para ver su QR
        </div>
    `;
    document.getElementById('qrcode-caption').textContent = "N/A";
    
    await loadWalletCoupons();
}

function closeWalletModal() {
    document.getElementById('wallet-modal').classList.add('hidden');
}

async function loadWalletCoupons() {
    const listContainer = document.getElementById('wallet-coupons-list');
    try {
        const response = await fetch(`${API_BASE}/pacientes/me/cupones`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) throw new Error("No se pudo cargar la billetera");
        
        walletCoupons = await response.json();
        
        if (walletCoupons.length === 0) {
            listContainer.innerHTML = `<p class="text-xs text-gray-500 text-center py-8">No tienes cupones en este momento.</p>`;
            return;
        }
        
        listContainer.innerHTML = walletCoupons.map(c => {
            const isRedeemed = c.estado === 'REDIMIDO';
            const badgeClass = isRedeemed ? "bg-red-50 text-red-700 border border-red-200" : "bg-emerald-50 text-emerald-700 border border-emerald-200 animate-pulse";
            const btnHtml = isRedeemed ? "" : `
                <button onclick="showCouponQR('${c.codigo}')" class="mt-2 w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-1.5 rounded-lg text-[10px] transition-colors shadow">
                    Ver QR para Escaneo
                </button>
            `;
            const typeLabel = c.codigo.startsWith("WELCOME-") ? "Bienvenida" : (c.codigo.startsWith("REF-") ? "Referido Patrocinador" : (c.codigo.startsWith("REWARD-") ? "Premio Referido" : "Campaña Médica"));
            
            return `
                <div class="bg-white border border-gray-150 p-3.5 rounded-xl text-xs space-y-1 shadow-sm">
                    <div class="flex justify-between items-center">
                        <span class="font-bold text-[10px] uppercase text-brand-600 tracking-wider">${typeLabel}</span>
                        <span class="px-2 py-0.5 rounded text-[8px] font-bold ${badgeClass}">${c.estado}</span>
                    </div>
                    <div class="flex justify-between items-center pt-1">
                        <span class="text-gray-400">Descuento:</span>
                        <strong class="text-gray-900 font-bold">$${parseFloat(c.monto).toFixed(2)} USD</strong>
                    </div>
                    ${btnHtml}
                </div>
            `;
        }).join('');
    } catch(err) {
        listContainer.innerHTML = `<p class="text-xs text-red-550 py-4">${err.message}</p>`;
    }
}

// Genera el código QR del cupón seleccionado
function showCouponQR(code) {
    const qrContainer = document.getElementById('qrcode-container');
    qrContainer.innerHTML = ""; // Limpiar anterior
    
    new QRCode(qrContainer, {
        text: code,
        width: 128,
        height: 128,
        colorDark : "#1f2937",
        colorLight : "#ffffff",
        correctLevel : QRCode.CorrectLevel.H
    });
    
    document.getElementById('qrcode-caption').textContent = code;
}

// "Invita y Gana" Enlace de Referido
async function copyReferralLink() {
    try {
        const profileRes = await fetch(`${API_BASE}/pacientes/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!profileRes.ok) throw new Error("Inicia sesión para invitar amigos");
        const profile = await profileRes.json();
        
        const referralLink = `${window.location.origin}/?ref=${profile.id}`;
        await navigator.clipboard.writeText(referralLink);
        
        showToast("¡Enlace Copiado!", "Compártelo con un amigo. Cuando asista a su consulta, ambos recibirán $5 USD.");
    } catch (err) {
        alert(err.message);
    }
}

// Canjear promociones
function openPromoModal() {
    document.getElementById('promo-modal').classList.remove('hidden');
}

function closePromoModal() {
    document.getElementById('promo-modal').classList.add('hidden');
    document.getElementById('promo-code-input').value = "";
}

async function submitPromoCode() {
    const code = document.getElementById('promo-code-input').value.trim();
    if (!code) return alert("Por favor ingresa un código promocional");
    
    try {
        const response = await fetch(`${API_BASE}/proveedores/canjear-campana?codigo_campana=${encodeURIComponent(code)}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Código promocional no válido");
        
        showToast("¡Cupón Agregado!", data.message);
        closePromoModal();
        await loadWalletCoupons();
    } catch(err) {
        alert(err.message);
    }
}

// --- CALIFICACIONES Y RESEÑAS VERIFICADAS ---
let currentReviewProviderId = null;

function openReviewsModal(providerId, providerName) {
    currentReviewProviderId = providerId;
    document.getElementById('reviews-title').textContent = `Reseñas de ${providerName}`;
    document.getElementById('reviews-modal').classList.remove('hidden');
    
    // Ocultar sección de post si no está logueado como paciente
    const postSection = document.getElementById('post-review-section');
    if (token && role === 'PACIENTE') {
        postSection.classList.remove('hidden');
    } else {
        postSection.classList.add('hidden');
    }
    
    loadReviews(providerId);
}

function closeReviewsModal() {
    document.getElementById('reviews-modal').classList.add('hidden');
    document.getElementById('review-comment').value = "";
    document.getElementById('review-stars').value = "5";
}

async function loadReviews(providerId) {
    const listContainer = document.getElementById('reviews-list-container');
    try {
        const response = await fetch(`${API_BASE}/proveedores/${providerId}/resenas`);
        if (!response.ok) throw new Error("Error al obtener opiniones");
        
        const reviews = await response.json();
        if (reviews.length === 0) {
            listContainer.innerHTML = `<p class="text-xs text-gray-500 text-center py-10">Ninguna reseña verificada disponible todavía.</p>`;
            return;
        }
        
        listContainer.innerHTML = reviews.map(r => {
            const stars = "⭐".repeat(r.calificacion);
            return `
                <div class="bg-white border border-gray-150 p-3.5 rounded-xl text-xs space-y-1.5 shadow-sm">
                    <div class="flex justify-between items-center font-semibold">
                        <strong class="text-gray-900">${r.paciente_nombre}</strong>
                        <span class="text-amber-500 font-bold">${stars}</span>
                    </div>
                    <p class="text-gray-600 leading-normal">${r.comentario || '<em>Sin comentarios.</em>'}</p>
                    <span class="text-[9px] text-gray-400 block text-right">${new Date(r.created_at).toLocaleDateString()}</span>
                </div>
            `;
        }).join('');
    } catch(err) {
        listContainer.innerHTML = `<p class="text-xs text-red-500">${err.message}</p>`;
    }
}

async function submitReview() {
    const calificacion = parseInt(document.getElementById('review-stars').value);
    const comentario = document.getElementById('review-comment').value.trim();
    
    try {
        const response = await fetch(`${API_BASE}/proveedores/${currentReviewProviderId}/resenas`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ calificacion, comentario })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Error al publicar opinión");
        
        showToast("¡Reseña Guardada!", "Tu calificación verificada se publicó exitosamente.");
        document.getElementById('review-comment').value = "";
        loadReviews(currentReviewProviderId);
    } catch(err) {
        alert(err.message);
    }
}

// Toast Alerts
function showToast(title, msg) {
    const toast = document.getElementById('toast');
    document.getElementById('toast-title').textContent = title;
    document.getElementById('toast-msg').textContent = msg;
    
    toast.classList.remove('hidden');
    setTimeout(() => {
        toast.className = toast.className.replace('translate-y-10 opacity-0', 'translate-y-0 opacity-100');
    }, 100);
    
    // Auto-ocultar tras 5 segundos
    setTimeout(closeToast, 5000);
}

function closeToast() {
    const toast = document.getElementById('toast');
    toast.className = toast.className.replace('translate-y-0 opacity-100', 'translate-y-10 opacity-0');
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 300);
}

// --- PACIENTE ADVERTISING MODAL CONTROLLERS ---
function openAdCampaignModal() {
    document.getElementById('patient-ad-modal').classList.remove('hidden');
}

function closeAdCampaignModal() {
    document.getElementById('patient-ad-modal').classList.add('hidden');
}

async function submitPatientAdCampaign() {
    const platforms = [];
    if (document.getElementById('pat-ad-instagram').checked) platforms.push('Instagram');
    if (document.getElementById('pat-ad-facebook').checked) platforms.push('Facebook');
    if (document.getElementById('pat-ad-tiktok').checked) platforms.push('TikTok');
    
    if (platforms.length === 0) {
        return alert("Por favor selecciona al menos una red social para publicar");
    }
    
    const pkgValue = document.getElementById('pat-ad-package').value;
    const [vistas, precio] = pkgValue.split('-').map(Number);
    
    try {
        const response = await fetch(`${API_BASE}/pacientes/solicitar-publicidad`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                plataformas: platforms.join(', '),
                cantidad_vistas: vistas,
                precio: precio
            })
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Error al solicitar publicidad");
        
        alert(data.message);
        closeAdCampaignModal();
    } catch(err) {
        alert(err.message);
    }
}
