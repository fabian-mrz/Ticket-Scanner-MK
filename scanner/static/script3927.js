let lastScannedCode = null;
let scanTimeout = null;
let breatheTimeout = null;
let fadeTimeout = null;
let resetTimeout = null;

// Check authentication status and token validity
async function checkAuth() {
    const authToken = localStorage.getItem('authToken');
    if (!authToken) {
        window.location.href = '/static/login.html';
        return false;
    }

    try {
        const response = await fetch('/api/check-token', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            localStorage.removeItem('authToken');
            window.location.href = '/static/login.html';
            return false;
        }
        return true;
    } catch (error) {
        localStorage.removeItem('authToken');
        window.location.href = '/static/login.html';
        return false;
    }
}

// Initialize app after checking auth
async function initializeApp() {
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        return; // Exit without throwing error
    }

    // Initialize scanner only if authenticated
    const html5QrcodeScanner = new Html5QrcodeScanner(
        "reader", { fps: 10, qrbox: 250 });

    // ...existing code for scanner initialization...
    html5QrcodeScanner.render(onScanSuccess);

    // Add periodic token check (every 5 minutes)
    setInterval(checkAuth, 300000);
}

// Start the app
initializeApp().catch(console.error);

function formatDateTime(isoString) {
    try {
        const date = new Date(isoString);
        const options = {
            timeZone: 'Europe/Berlin',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        };
        return date.toLocaleString('de-DE', options);
    } catch (error) {
        console.error('Error formatting date:', error);
        return 'Ungültiges Datum';
    }
}

async function processTicketCode(qrCodeMessage) {
    const authToken = localStorage.getItem('authToken');
    try {
        const response = await fetch('/api/check-ticket', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                qr_code: qrCodeMessage
            })
        });
        const data = await response.json();

        if (response.status === 401) {
            localStorage.removeItem('authToken');
            window.location.href = '/static/login.html';
            return;
        }

        updateTicketDisplay(response.ok, data);
    } catch (error) {
        updateTicketDisplay(false, { detail: 'Fehler bei der Überprüfung des Tickets' });
    }
}

function updateTicketDisplay(isSuccess, data) {
    const ticketInfoDiv = document.querySelector('.ticket-info');
    const ticketTypeEl = document.getElementById('ticket-type');
    const ticketNumberEl = document.getElementById('ticket-number');
    const ticketNameEl = document.getElementById('ticket-name');
    const ticketStatusEl = document.getElementById('ticket-status');
    const checkInTimeEl = document.getElementById('check-in-time');
    const lastScanEl = document.getElementById('last-scan');

    // Clear previous timers and animations
    clearTimeout(breatheTimeout);
    clearTimeout(fadeTimeout);
    clearTimeout(resetTimeout);
    ticketInfoDiv.classList.remove('fading', 'breathing');
    ticketInfoDiv.style.opacity = '';

    // Remove all state classes
    ticketInfoDiv.classList.remove('success', 'error', 'already-used', 'neutral', 'discounted');

    if (!isSuccess) {
        ticketTypeEl.textContent = '-';
        ticketNumberEl.textContent = '-';
        ticketNameEl.textContent = '-';
        ticketStatusEl.className = 'status-badge error';
        ticketStatusEl.textContent = data.detail || 'Ungültiges Ticket';
        checkInTimeEl && checkInTimeEl.classList.add('hidden');
        ticketInfoDiv.classList.add('error');
        ticketInfoDiv.style.animation = null;
        ticketInfoDiv.style.animation = 'shake 0.8s ease-in-out';
        return;
    }

    // Set ticket type text and class with emoji
    let ticketTypeText = data.ticket_type || '';
    if (ticketTypeText.toLowerCase().includes('trib')) {
        ticketTypeText += ' 🎫';
    } else if (ticketTypeText.toLowerCase().includes('sitz')) {
        ticketTypeText += ' 🪑';
    }

    if (data.discounted) {
        ticketTypeEl.className = 'discounted-text';
        ticketTypeEl.textContent = `${ticketTypeText} 🔵`;
        ticketInfoDiv.classList.add('discounted');
    } else {
        ticketTypeEl.className = '';
        ticketTypeEl.textContent = ticketTypeText;
    }

    ticketNumberEl.textContent = data.ticket_number || '-';
    ticketNameEl.textContent = data.name || '-';

    if (data.status === 'success') {
        ticketStatusEl.className = 'status-badge success';
        ticketStatusEl.textContent = 'Gültig - Erfolgreich eingescannt';
        checkInTimeEl && checkInTimeEl.classList.add('hidden');
        ticketInfoDiv.classList.add('success');
    } else if (data.status === 'already_used') {
        ticketStatusEl.className = 'status-badge already-used';
        ticketStatusEl.textContent = 'Ticket bereits verwendet';
        checkInTimeEl && checkInTimeEl.classList.remove('hidden');
        lastScanEl && (lastScanEl.textContent = formatDateTime(data.checked_in));
        ticketInfoDiv.classList.add('already-used');
    }

    // Trigger animation by removing and adding the class
    ticketInfoDiv.style.animation = null;
    if (data.status === 'success') {
        ticketInfoDiv.style.animation = 'slideIn 0.7s ease-out';
    } else if (data.status === 'already_used') {
        ticketInfoDiv.style.animation = 'pulse 0.6s ease-out';
    }

    // --- Breathing and fade-out logic ---
    // After 3s, start heartbeat animation
    breatheTimeout = setTimeout(() => {
        ticketInfoDiv.style.animation = 'heartbeat 1.1s infinite';
    }, 3000);

    // After 8s, fade out and reset
    fadeTimeout = setTimeout(() => {
        ticketInfoDiv.classList.add('fading');
        // After fade animation (1.5s), reset fields
        resetTimeout = setTimeout(() => {
            ticketInfoDiv.classList.remove('fading', 'success', 'error', 'already-used', 'neutral', 'discounted');
            ticketInfoDiv.style.animation = '';
            ticketTypeEl.className = '';
            ticketTypeEl.textContent = '-';
            ticketNumberEl.textContent = '-';
            ticketNameEl.textContent = '-';
            ticketStatusEl.className = 'status-badge neutral';
            ticketStatusEl.textContent = 'Bereit zum Scannen';
            checkInTimeEl && checkInTimeEl.classList.add('hidden');
            lastScanEl && (lastScanEl.textContent = '');
            ticketInfoDiv.style.opacity = '';
        }, 1500); // match fadeOut duration
    }, 8000);
}


function onScanSuccess(qrCodeMessage) {
    // Ignore if it's the same code within 5 seconds
    if (qrCodeMessage === lastScannedCode) {
        return;
    }

    // Clear any existing timeout
    if (scanTimeout) {
        clearTimeout(scanTimeout);
    }

    // Process the new code
    lastScannedCode = qrCodeMessage;
    processTicketCode(qrCodeMessage);

    // Reset lastScannedCode after 3 seconds
    scanTimeout = setTimeout(() => {
        lastScannedCode = null;
    }, 5000); // 5 seconds cooldown
}



// Handle manual form submission
const manualForm = document.getElementById('manual-form');
if (manualForm) {
    manualForm.addEventListener('submit', function (e) {
        e.preventDefault();
        const mainCode = document.getElementById('main-code').value.trim();
        const ticketType = document.getElementById('ticket-type-selector').value;
        const ticketNumberRaw = document.getElementById('ticket-number-in').value.trim();

        // Always prepend '0' to the ticket number, no client-side validation
        const ticketNumber = '0' + ticketNumberRaw;
        const composedCode = `${mainCode}_${ticketType}${ticketNumber}`;
        console.log('Composed Code:', composedCode);
        processTicketCode(composedCode);

        // Reset fields
        document.getElementById('main-code').value = '';
        document.getElementById('ticket-number-in').value = '';
        document.getElementById('main-code').focus();
    });
}

document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.getElementById('manual-toggle');
    const manualInput = document.querySelector('.manual-input');
    const logoutBtn = document.getElementById('logout-btn');
    if (toggle && manualInput) {
        // Hide manual input by default
        manualInput.classList.add('hidden');
        toggle.checked = false;

        toggle.addEventListener('change', function () {
            if (toggle.checked) {
                manualInput.classList.remove('hidden');
            } else {
                manualInput.classList.add('hidden');
            }
        });
    }
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function () {
            localStorage.removeItem('authToken');
            // Optionally clear cookies if you use them for auth
            document.cookie.split(";").forEach(function (c) {
                document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
            });
            window.location.href = '/static/login.html';
        });
    }
});
