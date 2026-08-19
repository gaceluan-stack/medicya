// map.js - Medic YA

let map;
let markerCluster;
let currentCategory = null;
let userCoords = [-0.180653, -78.467834]; // Quito default
let loadedProviders = {}; // Guardar los objetos de proveedores para el cotizador
let allProvidersData = []; // Guardar todos los proveedores para los filtros avanzados
let activeMobileView = 'list'; // 'list' o 'map' en móvil

// Servicios predefinidos por categoría
const CATEGORY_SERVICES = {
    'Doctores': [
        { id: 'consulta', name: 'Consulta Médica General', price: 0 }, // Precio base del doctor
        { id: 'chequeo', name: 'Chequeo Clínico Preventivo', price: 25.00 },
        { id: 'ecg', name: 'Electrocardiograma (ECG)', price: 40.00 },
        { id: 'laboratorio', name: 'Análisis de Laboratorio Básico', price: 15.00 }
    ],
    'Spas y Estética': [
        { id: 'masaje', name: 'Masaje Relajante Corporal', price: 0 }, // Precio base del spa
        { id: 'facial', name: 'Limpieza Facial Profunda', price: 20.00 },
        { id: 'exfoliacion', name: 'Exfoliación e Hidratación Completa', price: 30.00 },
        { id: 'reductor', name: 'Tratamiento Reductor Localizado', price: 50.00 }
    ],
    'Clínicas': [
        { id: 'emergencia', name: 'Atención de Emergencia 24/7', price: 0 }, // Precio base de la clínica
        { id: 'rx', name: 'Radiografía Digital (RX)', price: 35.00 },
        { id: 'eco', name: 'Ecografía Abdominal completa', price: 45.00 },
        { id: 'laboratorio_cli', name: 'Perfil de Exámenes Clínicos', price: 25.00 }
    ],
    'Farmacias': [
        { id: 'atencion', name: 'Atención Farmacéutica Base', price: 0 }, // Precio base
        { id: 'presion', name: 'Monitoreo de Presión Arterial', price: 3.00 },
        { id: 'inyectologia', name: 'Servicio de Inyectología', price: 5.00 },
        { id: 'delivery', name: 'Envío de Medicinas a Domicilio', price: 2.00 }
    ],
    'Laboratorios': [
        { id: 'atencion', name: 'Toma de Muestra a Domicilio', price: 0 }, // Precio base
        { id: 'sangre', name: 'Examen de Sangre completo', price: 18.00 },
        { id: 'orina', name: 'Examen de Orina y Coprológico', price: 10.00 }
    ]
};

// Cargar el mapa interactivo
window.addEventListener('load', () => {
    initMap();
});

async function initMap() {
    // 1. Intentar Geolocalización por GPS o GeoIP fallback
    await obtainUserLocation();
    
    // 2. Instanciar mapa centrado
    map = L.map('map').setView(userCoords, 14);
    
    // 3. Cargar CartoDB Positron (Fondo blanco premium, sin restaurantes ni POIs locales)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);
    
    // 4. Agregar pin del usuario
    const userIcon = L.icon({
        iconUrl: 'https://cdn-icons-png.flaticon.com/512/1041/1041916.png',
        iconSize: [35, 35],
        iconAnchor: [17, 35],
        popupAnchor: [0, -35]
    });
    
    L.marker(userCoords, { icon: userIcon })
        .addTo(map)
        .bindPopup("<strong class='text-brand-700'>Tu Ubicación Actual</strong>")
        .openPopup();
        
    // 5. Inicializar Marker Cluster Group
    markerCluster = L.markerClusterGroup({
        showCoverageOnHover: false,
        spiderfyOnMaxZoom: true
    });
    map.addLayer(markerCluster);
    
    // 6. Cargar proveedores iniciales
    await loadProviders();
}

async function obtainUserLocation() {
    return new Promise((resolve) => {
        if ("geolocation" in navigator) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    userCoords = [position.coords.latitude, position.coords.longitude];
                    console.log("Ubicación por GPS obtenida:", userCoords);
                    resolve();
                },
                async (error) => {
                    console.warn("Permiso de GPS denegado o fallo. Activando GeoIP Fallback...");
                    await fetchGeoIPFallback();
                    resolve();
                },
                { timeout: 5000 }
            );
        } else {
            console.warn("Geolocalización no soportada por el navegador. Activando GeoIP Fallback...");
            fetchGeoIPFallback().then(resolve);
        }
    });
}

// Fallback de ubicación utilizando ipapi.co (basado en IP pública del cliente)
async function fetchGeoIPFallback() {
    try {
        const response = await fetch('https://ipapi.co/json/');
        if (!response.ok) throw new Error("Fallo ipapi");
        const data = await response.json();
        if (data.latitude && data.longitude) {
            userCoords = [data.latitude, data.longitude];
            console.log(`Ubicación GeoIP estimada (${data.city}, ${data.country}):`, userCoords);
        }
    } catch (err) {
        console.error("Error en GeoIP Fallback:", err);
    }
}

// Retorna el elemento HTML y la clase para el pin del mapa según la categoría y premium
function getProviderIcon(category, esPremium) {
    let pinClass = "";
    let iconHtml = "";
    let pointerColor = "";
    
    if (category === 'Doctores') {
        pinClass = esPremium 
            ? "bg-sky-500 text-white border-yellow-400 border-[3px] shadow-[0_0_12px_rgba(245,158,11,0.8)] scale-110" 
            : "bg-sky-500 text-white border-white border-2 shadow-md";
        iconHtml = '<i class="fa-solid fa-user-doctor text-base"></i>';
        pointerColor = esPremium ? "border-t-yellow-400" : "border-t-sky-500";
    } else if (category === 'Spas y Estética') {
        pinClass = esPremium 
            ? "bg-pink-500 text-white border-yellow-400 border-[3px] shadow-[0_0_12px_rgba(245,158,11,0.8)] scale-110" 
            : "bg-pink-500 text-white border-white border-2 shadow-md";
        iconHtml = '<i class="fa-solid fa-spa text-base"></i>';
        pointerColor = esPremium ? "border-t-yellow-400" : "border-t-pink-500";
    } else if (category === 'Clínicas') {
        pinClass = esPremium 
            ? "bg-emerald-500 text-white border-yellow-400 border-[3px] shadow-[0_0_12px_rgba(245,158,11,0.8)] scale-110" 
            : "bg-emerald-500 text-white border-white border-2 shadow-md";
        iconHtml = '<i class="fa-solid fa-hospital text-base"></i>';
        pointerColor = esPremium ? "border-t-yellow-400" : "border-t-emerald-500";
    } else if (category === 'Farmacias') {
        pinClass = esPremium 
            ? "bg-purple-500 text-white border-yellow-400 border-[3px] shadow-[0_0_12px_rgba(245,158,11,0.8)] scale-110" 
            : "bg-purple-500 text-white border-white border-2 shadow-md";
        iconHtml = '<i class="fa-solid fa-prescription-bottle-medical text-base"></i>';
        pointerColor = esPremium ? "border-t-yellow-400" : "border-t-purple-500";
    } else {
        pinClass = esPremium 
            ? "bg-amber-500 text-white border-yellow-400 border-[3px] shadow-[0_0_12px_rgba(245,158,11,0.8)] scale-110" 
            : "bg-amber-500 text-white border-white border-2 shadow-md";
        iconHtml = '<i class="fa-solid fa-flask-vial text-base"></i>';
        pointerColor = esPremium ? "border-t-yellow-400" : "border-t-amber-500";
    }
    
    let crownHtml = esPremium 
        ? '<div class="absolute -top-4.5 left-1/2 transform -translate-x-1/2 text-amber-500 text-[11px] filter drop-shadow-[0_1.5px_2px_rgba(0,0,0,0.4)] animate-bounce" style="animation-duration: 2.5s;"><i class="fa-solid fa-crown"></i></div>' 
        : '';
        
    return L.divIcon({
        className: 'custom-leaflet-marker',
        html: `
            <div class="relative flex flex-col items-center">
                <!-- Cabeza del Pin -->
                <div class="relative w-10 h-10 rounded-full flex items-center justify-center p-0.5 overflow-hidden transition-all duration-300 ${pinClass}">
                    ${crownHtml}
                    ${iconHtml}
                </div>
                <!-- Punta del Pin -->
                <div class="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] ${pointerColor} -mt-[1px]"></div>
            </div>
        `,
        iconSize: [40, 48],
        iconAnchor: [20, 48],
        popupAnchor: [0, -48]
    });
}

function getProviderDefaultImage(prov) {
    if (prov.imagen_url) return prov.imagen_url;
    
    const cat = prov.categoria;
    const nameLower = prov.nombre_comercial.toLowerCase();
    
    if (cat === "Doctores") {
        // Si comienza con Dra. o Dra, es doctora (femenino)
        if (nameLower.startsWith("dra.") || nameLower.startsWith("dra ") || nameLower.includes(" dra. ") || nameLower.includes(" dra ")) {
            return "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=150";
        }
        // Si comienza con Dr. o Dr, es doctor (masculino)
        if (nameLower.startsWith("dr.") || nameLower.startsWith("dr ") || nameLower.includes(" dr. ") || nameLower.includes(" dr ")) {
            return "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&q=80&w=150";
        }
        // Por defecto
        return "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=150";
    } else if (cat === "Farmacias") {
        return "https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&q=80&w=150";
    } else if (cat === "Laboratorios Clínicos") {
        return "https://images.unsplash.com/photo-1579154204601-01588f351167?auto=format&fit=crop&q=80&w=150";
    } else if (cat === "Spas y Estética") {
        return "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&q=80&w=150";
    } else {
        return "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=150";
    }
}

// Cargar y pintar los proveedores en el mapa y en la lista lateral
async function loadProviders() {
    let url = '/api/proveedores/mapa';
    if (currentCategory) {
        url += `?categoria=${encodeURIComponent(currentCategory)}`;
    }
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        allProvidersData = [];
        loadedProviders = {};
        
        for (const prov of data) {
            let ratingText = "Sin valoraciones";
            let ratingVal = 0;
            try {
                const rRes = await fetch(`/api/proveedores/${prov.id}/resenas`);
                if (rRes.ok) {
                    const reviews = await rRes.json();
                    if (reviews.length > 0) {
                        ratingVal = reviews.reduce((sum, r) => sum + r.calificacion, 0) / reviews.length;
                        ratingText = `⭐ ${ratingVal.toFixed(1)} (${reviews.length} opiniones)`;
                    }
                }
            } catch(e) {}
            
            prov.ratingText = ratingText;
            prov.ratingVal = ratingVal;
            loadedProviders[prov.id] = prov;
            allProvidersData.push(prov);
        }
        
        applyAdvancedFilters();
    } catch (err) {
        console.error("Error al cargar proveedores:", err);
    }
}

function applyAdvancedFilters() {
    const filterCiudad = document.getElementById('filter-ciudad').value;
    const filterSector = document.getElementById('filter-sector').value;
    const filterRating = parseFloat(document.getElementById('filter-rating').value || "0");
    const filterPremium = document.getElementById('filter-premium').value;
    const filterEspecialidad = document.getElementById('filter-especialidad') ? document.getElementById('filter-especialidad').value.trim().toLowerCase() : "";
    
    // Filtrar los datos locales
    let filtered = allProvidersData.filter(prov => {
        if (filterCiudad && prov.ciudad !== filterCiudad) return false;
        if (filterSector && prov.sector !== filterSector) return false;
        if (filterRating > 0 && prov.ratingVal < filterRating) return false;
        if (filterPremium === 'premium' && !prov.es_premium) return false;
        if (filterPremium === 'basic' && prov.es_premium) return false;
        if (filterEspecialidad) {
            const esp = (prov.especialidad || "").toLowerCase();
            if (!esp.includes(filterEspecialidad)) return false;
        }
        return true;
    });
    
    // Limpiar marcadores antiguos del cluster
    markerCluster.clearLayers();
    
    const listContainer = document.getElementById('providers-list');
    const listTitle = document.getElementById('list-title');
    
    if (filtered.length === 0) {
        listContainer.innerHTML = `
            <p class="text-xs text-gray-500 text-center py-10">Ningún profesional de la salud coincide con los filtros aplicados.</p>
        `;
        listTitle.textContent = "Sin resultados";
        return;
    }
    
    listTitle.textContent = `${filtered.length} Especialistas Encontrados`;
    let listHtml = "";
    
    for (const prov of filtered) {
        // 1. Crear marcadores en el mapa
        const marker = L.marker([prov.latitud, prov.longitud], {
            icon: getProviderIcon(prov.categoria, prov.es_premium)
        });
        
        const docImgPopup = getProviderDefaultImage(prov);
        const badgeHtml = prov.es_premium ? `<span class="bg-teal-50 text-teal-700 border border-teal-200 px-2 py-0.5 rounded-lg font-bold text-[9px]">Membresía Premium</span>` : `<span class="bg-gray-50 text-gray-500 border border-gray-200 px-2 py-0.5 rounded-lg font-semibold text-[9px]">Membresía Básica</span>`;
        
        const isLoggedIn = !!localStorage.getItem('token');
        const blurClass = isLoggedIn ? "" : "auth-blur";

        let socialIconsHtml = "";
        if (!isLoggedIn) {
            socialIconsHtml = `
                <div class="text-[9px] text-gray-400 font-bold flex items-center space-x-1">
                    <i class="fa-solid fa-lock text-brand-500 animate-pulse"></i>
                    <span>Inicia sesión</span>
                </div>
            `;
        } else if (prov.es_premium) {
            socialIconsHtml = `
                <div class="flex space-x-1.5">
                    ${prov.link_instagram ? `<a href="${prov.link_instagram}" target="_blank" class="w-6 h-6 rounded-full bg-teal-50 border border-teal-200 text-teal-600 hover:bg-teal-100 flex items-center justify-center transition-colors"><i class="fa-brands fa-instagram text-[10px]"></i></a>` : ''}
                    ${prov.link_tiktok ? `<a href="${prov.link_tiktok}" target="_blank" class="w-6 h-6 rounded-full bg-teal-50 border border-teal-200 text-teal-600 hover:bg-teal-100 flex items-center justify-center transition-colors"><i class="fa-brands fa-tiktok text-[10px]"></i></a>` : ''}
                    ${prov.link_facebook ? `<a href="${prov.link_facebook}" target="_blank" class="w-6 h-6 rounded-full bg-teal-50 border border-teal-200 text-teal-600 hover:bg-teal-100 flex items-center justify-center transition-colors"><i class="fa-brands fa-facebook-f text-[10px]"></i></a>` : ''}
                </div>
            `;
        } else {
            socialIconsHtml = `
                <div class="flex space-x-1 opacity-55">
                    <span class="w-6 h-6 rounded-full bg-gray-50 border border-gray-200 text-gray-400 flex items-center justify-center" title="Básico"><i class="fa-solid fa-lock text-[8px]"></i></span>
                </div>
            `;
        }

        const popupHtml = `
            <div class="p-2 space-y-3 text-xs text-gray-700" style="min-width: 230px; font-family: 'Outfit', sans-serif;">
                <div class="flex items-start space-x-3">
                    <img src="${docImgPopup}" alt="${prov.nombre_comercial}" class="w-12 h-12 rounded-full object-cover border border-gray-150 shadow-sm flex-shrink-0">
                    <div class="min-w-0 flex-1">
                        <h4 class="font-bold text-gray-900 text-sm leading-tight truncate ${blurClass}">${prov.nombre_comercial}</h4>
                        <p class="text-[10px] text-gray-550 font-semibold mt-0.5 ${blurClass}">(${prov.especialidad || 'Especialista'}) • <span class="text-amber-500 font-bold">⭐ ${prov.ratingVal > 0 ? prov.ratingVal.toFixed(1) : 'Nuevo'}</span></p>
                        <div class="mt-1.5">${badgeHtml}</div>
                    </div>
                </div>
                
                <div class="space-y-1 text-[10px] text-gray-600 border-t border-b border-gray-100 py-2 ${blurClass}">
                    <p class="flex items-center"><i class="fa-solid fa-location-dot text-brand-500 mr-2 flex-shrink-0 w-3.5 text-center"></i> ${[prov.ciudad, prov.sector].filter(Boolean).join(', ') || 'Ubicación no especificada'}</p>
                    <p class="flex items-center font-bold text-gray-800"><i class="fa-solid fa-circle-check text-emerald-500 mr-2 flex-shrink-0 w-3.5 text-center"></i> Consulta Presencial: $${parseFloat(prov.precio_consulta).toFixed(2)}</p>
                    <p class="flex items-center text-gray-500"><i class="fa-solid fa-video text-brand-500 mr-2 flex-shrink-0 w-3.5 text-center"></i> Consulta Online: $${(parseFloat(prov.precio_consulta) * 0.8).toFixed(2)}</p>
                </div>
                
                <div class="flex items-center justify-between mt-1">
                    ${socialIconsHtml}
                    <button onclick="selectProviderForRouting('${prov.id}')" class="bg-brand-600 hover:bg-brand-700 text-white font-bold py-1.5 px-3 rounded-xl text-[10px] transition-all shadow-sm flex items-center space-x-1">
                        <span>Agendar Cita</span> <i class="fa-solid fa-chevron-right text-[8px]"></i>
                    </button>
                </div>
            </div>
        `;
        
        marker.bindPopup(popupHtml);
        markerCluster.addLayer(marker);
        
        // 2. Tarjeta lateral
        let listSocialHtml = "";
        if (!isLoggedIn) {
            listSocialHtml = `
                <div class="pt-2 border-t border-gray-100 flex items-center justify-between text-[10px] text-gray-400">
                    <span class="flex items-center space-x-1.5"><i class="fa-solid fa-lock text-[9px] text-brand-500 animate-pulse"></i> <span>Registrado Requerido</span></span>
                    <span class="text-brand-600 font-bold hover:underline">Acceder</span>
                </div>
            `;
        } else if (prov.es_premium) {
            const cleanWa = (prov.celular_whatsapp || '593987654321').replace(/[^0-9]/g, '');
            listSocialHtml = `
                <div class="flex space-x-2 pt-2 border-t border-gray-100 justify-start mt-1">
                    ${prov.link_instagram ? `<a href="${prov.link_instagram}" target="_blank" onclick="event.stopPropagation();" class="w-7 h-7 rounded-full bg-teal-50 border border-teal-200 hover:bg-teal-100 text-teal-600 hover:text-teal-800 flex items-center justify-center transition-all" title="Instagram"><i class="fa-brands fa-instagram text-xs"></i></a>` : ''}
                    ${prov.link_tiktok ? `<a href="${prov.link_tiktok}" target="_blank" onclick="event.stopPropagation();" class="w-7 h-7 rounded-full bg-teal-50 border border-teal-200 hover:bg-teal-100 text-teal-600 hover:text-teal-800 flex items-center justify-center transition-all" title="TikTok"><i class="fa-brands fa-tiktok text-xs"></i></a>` : ''}
                    ${prov.link_facebook ? `<a href="${prov.link_facebook}" target="_blank" onclick="event.stopPropagation();" class="w-7 h-7 rounded-full bg-teal-50 border border-teal-200 hover:bg-teal-100 text-teal-600 hover:text-teal-800 flex items-center justify-center transition-all" title="Facebook"><i class="fa-brands fa-facebook-f text-xs"></i></a>` : ''}
                    <a href="https://wa.me/${cleanWa}" target="_blank" onclick="event.stopPropagation();" class="w-7 h-7 rounded-full bg-teal-50 border border-teal-200 hover:bg-teal-100 text-teal-600 hover:text-teal-800 flex items-center justify-center transition-all" title="WhatsApp"><i class="fa-brands fa-whatsapp text-xs"></i></a>
                    <a href="#" target="_blank" onclick="event.stopPropagation();" class="w-7 h-7 rounded-full bg-teal-50 border border-teal-200 hover:bg-teal-100 text-teal-650 hover:text-teal-800 flex items-center justify-center transition-all" title="LinkedIn"><i class="fa-brands fa-linkedin-in text-xs"></i></a>
                </div>
            `;
        } else {
            listSocialHtml = `
                <div class="flex space-x-2 pt-2 border-t border-gray-100 justify-start mt-1 opacity-50" title="Básico">
                    <span class="w-7 h-7 rounded-full bg-gray-50 border border-gray-200 text-gray-400 flex items-center justify-center"><i class="fa-solid fa-lock text-[10px]"></i></span>
                </div>
            `;
        }

        const docImg = getProviderDefaultImage(prov);

        listHtml += `
            <div class="bg-white border border-gray-200 hover:border-brand-300 p-4.5 rounded-2xl cursor-pointer hover:shadow-md transition-all duration-300 flex flex-col space-y-3" onclick="selectProviderForRouting('${prov.id}')">
                <div class="flex items-start space-x-3.5">
                    <img src="${docImg}" alt="${prov.nombre_comercial}" class="w-14 h-14 rounded-full object-cover border-2 border-brand-50 shadow-sm flex-shrink-0">
                    <div class="flex-1 min-w-0">
                        <h4 class="font-bold text-gray-900 text-sm truncate flex items-center ${blurClass}">
                            ${prov.nombre_comercial} ${prov.es_premium ? '<span class="ml-1 text-amber-500">👑</span>' : ''}
                        </h4>
                        <p class="text-brand-600 font-semibold text-[11px] mt-0.5 ${blurClass}">${prov.especialidad || 'Especialista'}</p>
                        <p class="text-gray-450 text-[10px] mt-1 flex items-center ${blurClass}"><i class="fa-solid fa-location-dot text-brand-500 mr-1.5 flex-shrink-0 w-3.5 text-center"></i> ${[prov.ciudad, prov.sector].filter(Boolean).join(', ') || 'Ubicación no especificada'}</p>
                    </div>
                </div>
                <div class="flex items-center justify-between pt-1 text-[10px]">
                    <span class="text-amber-500 font-bold flex items-center"><i class="fa-solid fa-star mr-1"></i> ${prov.ratingVal > 0 ? prov.ratingVal.toFixed(1) : 'Nuevo'}</span>
                    <span class="px-2 py-0.5 rounded-lg border border-brand-100 bg-brand-50 text-brand-700 font-bold ${blurClass}">Consulta: $${parseFloat(prov.precio_consulta).toFixed(2)}</span>
                </div>
                ${listSocialHtml}
            </div>
        `;
    }
    
    listContainer.innerHTML = listHtml;
}

// Clic al botón de contactar (Registra lead y abre WhatsApp con el mensaje personalizado de cotización)
async function contactProviderWithQuote(id, name, phone, quoteMessage) {
    const token = localStorage.getItem('token');
    if (!token) {
        alert("Para concretar tu cita y cotización, por favor regístrate primero.");
        openRegisterModal();
        return;
    }
    
    try {
        const response = await fetch(`/api/proveedores/${id}/contactar`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const data = await response.json();
        
        if (!response.ok) throw new Error(data.detail || "Error al contactar");
        
        alert(`¡Cotización registrada en Medic YA!\nTe redirigiremos a WhatsApp.`);
        
        // Redirigir a WhatsApp con el texto codificado
        const cleanPhone = (phone || '593987654321').replace(/[^0-9]/g, '');
        window.open(`https://wa.me/${cleanPhone}?text=${encodeURIComponent(quoteMessage)}`, '_blank');
        
    } catch(err) {
        alert(err.message);
    }
}

function focusOnProvider(lat, lng, providerId) {
    map.setView([lat, lng], 16);
    markerCluster.eachLayer((layer) => {
        if (layer.getLatLng().lat === lat && layer.getLatLng().lng === lng) {
            layer.openPopup();
        }
    });
}

function filterCategory(category) {
    currentCategory = category;
    
    // Cambiar clases activas del botón de filtro
    const buttons = document.querySelectorAll('.cat-btn');
    buttons.forEach(btn => {
        btn.classList.remove('active', 'bg-brand-600', 'text-white', 'border-brand-600');
        btn.classList.add('bg-white', 'text-gray-600', 'border-gray-200', 'shadow-sm');
    });
    
    event.currentTarget.classList.add('active', 'bg-brand-600', 'text-white', 'border-brand-600');
    event.currentTarget.classList.remove('bg-white', 'text-gray-600', 'border-gray-200', 'shadow-sm');
    
    loadProviders();
}

// --- COTIZADOR DE SERVICIOS Y PANEL DETALLADO (GOOGLE MAPS STYLE) ---

function selectProviderForRouting(id) {
    // Si estamos en móvil y en vista de mapa, regresar a la vista de lista/detalle automáticamente
    if (window.innerWidth < 768 && activeMobileView === 'map') {
        toggleMobileView();
    }
    
    const token = localStorage.getItem('token');
    if (!token) {
        alert("Favor inicie sesión para que conozca todas nuestras promociones o regístrese y obtenga un cupón de descuento para cualquier servicio de nuestros médicos especialistas.");
        openRegisterModal("Favor inicie sesión para que conozca todas nuestras promociones o regístrese y obtenga un cupón de descuento para cualquier servicio de nuestros médicos especialistas.");
        return;
    }
    const prov = loadedProviders[id];
    if (!prov) return;
    
    // Centrar en el mapa
    focusOnProvider(prov.latitud, prov.longitud, prov.id);
    
    // Swapear paneles de la barra lateral
    document.getElementById('sidebar-main-content').classList.add('hidden');
    document.getElementById('sidebar-detail-content').classList.remove('hidden');
    
    const premiumBadge = prov.es_premium ? "<span class='ml-1.5 text-amber-500 font-bold'>👑 Premium</span>" : "";
    
    // Generar listado de servicios con checkboxes
    let services = [];
    
    // 1. Determinar el servicio base por categoría
    const baseNames = {
        'Doctores': 'Consulta Médica General',
        'Spas y Estética': 'Masaje Relajante Corporal',
        'Clínicas': 'Atención de Emergencia 24/7',
        'Farmacias': 'Atención Farmacéutica Base',
        'Laboratorios': 'Toma de Muestra a Domicilio'
    };
    const baseName = baseNames[prov.categoria] || 'Servicio General';
    services.push({ id: 'base-service', name: baseName, price: parseFloat(prov.precio_consulta) });
    
    // 2. Cargar servicios adicionales personalizados o predefinidos
    if (prov.servicios_adicionales && Array.isArray(prov.servicios_adicionales) && prov.servicios_adicionales.length > 0) {
        prov.servicios_adicionales.forEach((s, idx) => {
            services.push({ id: 'custom-' + idx, name: s.name, price: parseFloat(s.price) });
        });
    } else {
        const catServices = CATEGORY_SERVICES[prov.categoria] || CATEGORY_SERVICES['Doctores'];
        // Omitir el primer servicio predefinido ya que representaba la consulta general (precio 0)
        catServices.slice(1).forEach(s => {
            services.push({ id: s.id, name: s.name, price: parseFloat(s.price) });
        });
    }
    
    let servicesHtml = services.map((s, index) => {
        const checked = index === 0 ? 'checked disabled' : '';
        return `
            <label class="flex items-center space-x-3 bg-white p-2.5 rounded-xl border border-gray-150 hover:border-gray-300 cursor-pointer select-none transition-colors shadow-sm">
                <input type="checkbox" id="svc-${s.id}" data-name="${s.name}" data-price="${s.price}" ${checked} onchange="recalculateQuote('${prov.id}')" class="w-4 h-4 text-brand-600 bg-white border-gray-250 rounded focus:ring-brand-500 cursor-pointer">
                <div class="flex-1 flex justify-between text-[11px]">
                    <span class="text-gray-600 font-medium">${s.name}</span>
                    <strong class="text-gray-900">$${s.price.toFixed(2)}</strong>
                </div>
            </label>
        `;
    }).join('');

    let socialHtml = "";
    if (prov.es_premium && (prov.link_instagram || prov.link_tiktok || prov.link_facebook)) {
        socialHtml = `
            <div class="flex items-center space-x-2 mt-3 pt-2.5 border-t border-gray-100">
                <span class="text-[10px] text-gray-400 font-bold uppercase tracking-wider mr-1">Redes Sociales:</span>
                ${prov.link_instagram ? `<a href="${prov.link_instagram}" target="_blank" class="w-6 h-6 rounded-lg bg-purple-50 text-purple-650 hover:bg-purple-100 flex items-center justify-center transition-all shadow-sm" title="Instagram"><i class="fa-brands fa-instagram text-xs"></i></a>` : ''}
                ${prov.link_tiktok ? `<a href="${prov.link_tiktok}" target="_blank" class="w-6 h-6 rounded-lg bg-pink-50 text-pink-650 hover:bg-pink-100 flex items-center justify-center transition-all shadow-sm" title="TikTok"><i class="fa-brands fa-tiktok text-xs"></i></a>` : ''}
                ${prov.link_facebook ? `<a href="${prov.link_facebook}" target="_blank" class="w-6 h-6 rounded-lg bg-blue-50 text-blue-650 hover:bg-blue-100 flex items-center justify-center transition-all shadow-sm" title="Facebook"><i class="fa-brands fa-facebook-f text-xs"></i></a>` : ''}
            </div>
        `;
    }

    document.getElementById('detail-card-body').innerHTML = `
        <div class="space-y-4">
            <!-- Header Card -->
            <div class="border-b border-gray-100 pb-3">
                <div class="flex justify-between items-start gap-1">
                    <h3 class="text-sm font-bold text-gray-900 leading-snug">${prov.nombre_comercial} ${premiumBadge}</h3>
                    <span class="text-[9px] px-2 py-0.5 rounded bg-brand-50 text-brand-600 border border-brand-500/15 shrink-0">${prov.categoria}</span>
                </div>
                <p class="text-xs text-sky-600 font-semibold mt-1"><i class="fa-solid fa-graduation-cap mr-1"></i> ${prov.especialidad || 'General'}</p>
                <div class="flex items-center space-x-2 mt-2 text-xs">
                    <span class="text-amber-500 font-bold"><i class="fa-solid fa-star mr-1"></i> ${prov.ratingText}</span>
                </div>
                ${socialHtml}
            </div>
            
            <!-- Cotizador de servicios -->
            <div class="space-y-3">
                <h4 class="text-xs font-bold text-gray-900 uppercase tracking-wider flex items-center">
                    <i class="fa-solid fa-calculator text-brand-500 mr-2"></i> Servicios y Presupuesto
                </h4>
                <div class="space-y-2">
                    ${servicesHtml}
                </div>
            </div>

            <!-- Resumen de cotización -->
            <div class="bg-gradient-to-br from-brand-50/50 to-white border border-brand-500/10 p-4 rounded-2xl flex justify-between items-center text-xs shadow-sm">
                <div>
                    <span class="text-gray-500 font-semibold">Total Estimado:</span>
                    <p class="text-[10px] text-gray-400 mt-0.5">Incluye impuestos locales</p>
                </div>
                <strong class="text-brand-600 text-base" id="quote-total">$0.00 USD</strong>
            </div>
            
            <!-- Actions -->
            <div class="space-y-2 pt-1">
                <button onclick="triggerWhatsAppQuote('${prov.id}')" class="w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-2.5 rounded-xl text-xs transition-colors flex items-center justify-center space-x-2 shadow">
                    <i class="fa-brands fa-whatsapp text-sm"></i> <span>Agendar Cita en WhatsApp</span>
                </button>
                <button onclick="openReviewsModal('${prov.id}', '${prov.nombre_comercial}')" class="w-full bg-white hover:bg-gray-50 text-gray-600 border border-gray-200 py-2.5 rounded-xl text-xs transition-colors flex items-center justify-center space-x-2 shadow-sm">
                    <i class="fa-solid fa-comments text-brand-500"></i> <span>Ver Comentarios de Pacientes</span>
                </button>
            </div>
        </div>
    `;

    // Calcular cotización inicial
    recalculateQuote(prov.id);
}

// Recalcula el precio total sumando los checkboxes marcados
function recalculateQuote(providerId) {
    const prov = loadedProviders[providerId];
    if (!prov) return;
    
    const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="svc-"]');
    let total = 0;
    
    checkboxes.forEach(cb => {
        if (cb.checked) {
            total += parseFloat(cb.getAttribute('data-price'));
        }
    });
    
    document.getElementById('quote-total').textContent = `$${total.toFixed(2)} USD`;
}

// Recopila los servicios y genera el trigger de WhatsApp con la cotización formateada
function triggerWhatsAppQuote(providerId) {
    const prov = loadedProviders[providerId];
    if (!prov) return;
    
    const checkboxes = document.querySelectorAll('input[type="checkbox"][id^="svc-"]');
    let selected = [];
    let total = 0;
    
    checkboxes.forEach(cb => {
        if (cb.checked) {
            const name = cb.getAttribute('data-name');
            const price = parseFloat(cb.getAttribute('data-price'));
            selected.push({ name, price });
            total += price;
        }
    });
    
    // Formatear el mensaje
    let message = `¡Hola! Vi tu perfil en *Medic YA* y me gustaría agendar una cita en *${prov.nombre_comercial}*.\n\n`;
    message += `📋 *SERVICIOS COTIZADOS:*\n`;
    selected.forEach(s => {
        message += `• ${s.name}: $${s.price.toFixed(2)} USD\n`;
    });
    message += `\n💰 *TOTAL ESTIMADO:* $${total.toFixed(2)} USD\n\n`;
    message += `Por favor, confírmame tu disponibilidad para agendar. ¡Muchas gracias!`;
    
    contactProviderWithQuote(prov.id, prov.nombre_comercial, prov.celular_whatsapp, message);
}

function goBackToList() {
    document.getElementById('sidebar-main-content').classList.remove('hidden');
    document.getElementById('sidebar-detail-content').classList.add('hidden');
    map.setView(userCoords, 14);
}

function toggleMobileView() {
    const aside = document.querySelector('aside');
    const mapSec = document.getElementById('map');
    const btn = document.getElementById('mobile-toggle-btn');
    
    if (activeMobileView === 'list') {
        activeMobileView = 'map';
        aside.classList.add('hidden');
        aside.classList.remove('flex');
        
        mapSec.classList.remove('hidden');
        mapSec.classList.add('flex');
        
        if (map) {
            setTimeout(() => {
                map.invalidateSize();
            }, 100);
        }
        
        btn.innerHTML = `<i class="fa-solid fa-list"></i> <span>Ver Lista</span>`;
    } else {
        activeMobileView = 'list';
        aside.classList.remove('hidden');
        aside.classList.add('flex');
        
        mapSec.classList.add('hidden');
        mapSec.classList.remove('flex');
        
        btn.innerHTML = `<i class="fa-solid fa-map-location-dot"></i> <span>Ver Mapa</span>`;
    }
}
