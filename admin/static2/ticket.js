function getHeaders(includeContentType = true) {
    const headers = {
        'Authorization': `Bearer ${localStorage.getItem('authToken')}`
    };
    if (includeContentType) {
        headers['Content-Type'] = 'application/json';
    }
    return headers;
}


async function searchTickets() {
    const searchCriteria = {
        orderId: document.getElementById('orderSearch').value.trim(),
        ticketNumber: document.getElementById('ticketSearch').value.trim().toUpperCase(),
        name: document.getElementById('nameSearch').value.trim(),
        email: document.getElementById('emailSearch').value.trim(),
        ticketType: document.getElementById('typeFilter').value,
        discounted: document.getElementById('discountFilter').value
    };

    try {
        const response = await fetch('/tickets', {
            headers: getHeaders()
        });

        if (response.status === 401) {
            window.location.href = '/static2/login.html';
            return;
        }

        const data = await response.json();

        const filteredTickets = data.tickets.filter(ticket => {
            const matchesOrderId = !searchCriteria.orderId ||
                ticket.bestell_id.toString().includes(searchCriteria.orderId);

            const matchesTicketNumber = !searchCriteria.ticketNumber ||
                ticket.ticket_number.includes(searchCriteria.ticketNumber);

            const matchesName = !searchCriteria.name ||
                ticket.name_ticketinhaber.toLowerCase().includes(searchCriteria.name.toLowerCase());

            const matchesEmail = !searchCriteria.email ||
                ticket.email_ticketinhaber.toLowerCase().includes(searchCriteria.email.toLowerCase()) ||
                ticket.email_kaeufer.toLowerCase().includes(searchCriteria.email.toLowerCase());

            const matchesType = !searchCriteria.ticketType ||
                ticket.ticket_type.includes(searchCriteria.ticketType);

            const matchesDiscount = searchCriteria.discounted === '' ||
                ticket.discounted === (searchCriteria.discounted === 'true');

            return matchesOrderId && matchesTicketNumber && matchesName &&
                matchesEmail && matchesType && matchesDiscount;
        });

        renderTickets(filteredTickets);
        updateSearchStatus(filteredTickets.length);
    } catch (error) {
        console.error('Error searching tickets:', error);
        updateSearchStatus(0);
    }
}

function logout() {
    localStorage.removeItem('authToken');
    window.location.href = '/static2/login.html';
}


function resetSearch() {
    // Reset all search inputs
    document.getElementById('orderSearch').value = '';
    document.getElementById('ticketSearch').value = '';
    document.getElementById('nameSearch').value = '';
    document.getElementById('emailSearch').value = '';
    document.getElementById('typeFilter').value = '';
    document.getElementById('discountFilter').value = '';

    // Reload all tickets
    loadTickets();
}

function updateSearchStatus(count) {
    const status = document.getElementById('search-status');
    if (status) {
        status.textContent = `${count} Ticket${count !== 1 ? 's' : ''} gefunden`;
        status.style.display = 'block';
    }
}

// Add event listeners for real-time search
document.querySelectorAll('.search-section input, .search-section select').forEach(element => {
    element.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            searchTickets();
        }
    });
});


// Update loadTickets function
async function loadTickets() {
    try {
        const response = await fetch('/tickets', {
            headers: getHeaders()
        });
        if (response.status === 401) {
            window.location.href = '/static2/login.html';
            return;
        }
        const data = await response.json();
        renderTickets(data.tickets);
    } catch (error) {
        console.error('Error loading tickets:', error);
    }
}

// Separate render function for better organization
function renderTickets(tickets) {
    const grid = document.getElementById('ticketGrid');

    grid.innerHTML = tickets.map(ticket => `
    <div class="ticket-card${ticket.einchecken ? ' checked-in' : ''}" data-ticket-id="${ticket.ticket_id}">
            <div class="ticket-header">
                <h3>${ticket.ticket_type} - ${ticket.ticket_number}</h3>
                <span class="ticket-badge ${ticket.discounted ? 'discounted' : ''}">${ticket.discounted ? 'Ermäßigt' : 'Normal'}</span>
            </div>
            
            <div class="ticket-info">
                <div class="info-group">
                    <span class="info-label">Created:</span>
                    <span class="info-value">${formatDate(ticket.created_at)}</span>
                </div>
                <div class="info-group">
                    <span class="info-label">Ticket ID:</span>
                    <span class="info-value">${ticket.ticket_id}</span>
                </div>
                <div class="info-group">
                    <span class="info-label">Bestell-ID:</span>
                    <span class="info-value">${ticket.bestell_id}</span>
                </div>
                <div class="info-group">
                    <span class="info-label">QR Code:</span>
                    <span class="info-value">${ticket.qrcode}</span>
                </div>
                <div class="info-group">
                    <span class="info-label">Status:</span>
                    <span class="info-value">${ticket.bestellstatus || 'N/A'}</span>
                </div>
            </div>

            <div class="form-section">
                <div class="input-group">
                    <label>Name:</label>
                    <input type="text" class="name" value="${ticket.name_ticketinhaber}">
                </div>
                <div class="input-group">
                    <label>Email Ticketinhaber:</label>
                    <input type="email" class="email-ticket" value="${ticket.email_ticketinhaber}">
                </div>
                <div class="input-group">
                    <label>Email Käufer:</label>
                    <input type="email" class="email-buyer" value="${ticket.email_kaeufer}">
                </div>
            </div>

            <div class="button-group">
                <button class="save-btn" onclick="saveTicket('${ticket.ticket_id}')">
                    <i class="fas fa-save"></i> Save
                </button>
                <button class="resend-btn" onclick="resendTicket('${ticket.ticket_id}')">
                    <i class="fas fa-envelope"></i> Resend Ticket
                </button>
            </div>
            <div class="status" id="status-${ticket.ticket_id}"></div>
        </div>
    `).join('');
}

// Add helper function for date formatting
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Update saveTicket function
async function saveTicket(ticketId) {
    const card = document.querySelector(`[data-ticket-id="${ticketId}"]`);
    const data = {
        ticket_id: ticketId,
        name_ticketinhaber: card.querySelector('.name').value,
        email_ticketinhaber: card.querySelector('.email-ticket').value,
        email_kaeufer: card.querySelector('.email-buyer').value,
        // Add required fields with default values
        ticket_number: "",
        bestell_id: "",
        ticket_type: "",
        discounted: false
    };

    try {
        const response = await fetch(`/tickets/${ticketId}`, {
            method: 'PUT',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error saving ticket');
        }

        showStatus(ticketId, 'success', 'Saved successfully');
    } catch (e) {
        showStatus(ticketId, 'error', e.message);
    }
}

// Update resendTicket function
async function resendTicket(ticketId) {
    try {
        const response = await fetch(`/tickets/resend/${ticketId}`, {
            method: 'POST',
            headers: getHeaders()
        });

        if (response.ok) {
            showStatus(ticketId, 'success', 'Ticket resent successfully');
            alert('Ticket was successfully resent!');  // Add alert for success
        } else {
            showStatus(ticketId, 'error', 'Error resending ticket');
            alert('Error resending ticket');  // Add alert for error
        }
    } catch (e) {
        showStatus(ticketId, 'error', 'Error resending ticket');
    }
}


function showStatus(ticketId, type, message) {
    const status = document.getElementById(`status-${ticketId}`);
    status.className = `status ${type}`;
    status.textContent = message;
    status.style.display = 'block';
    setTimeout(() => status.style.display = 'none', 3000);
}

// CSV file upload handling
document.getElementById('csvFile').addEventListener('change', function (event) {
    const file = event.target.files[0];
    if (file) {
        document.getElementById('selected-file').textContent = file.name;
        document.querySelector('.import-btn').disabled = false;
    }
});

// Update uploadCSV function
async function uploadCSV() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    if (!file) {
        showUploadStatus('error', 'Please select a file first');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/tickets/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('authToken')}`
            },
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            showUploadStatus('success', result.message);
            // Reset file input
            fileInput.value = '';
            document.getElementById('selected-file').textContent = '';
            document.querySelector('.import-btn').disabled = true;
            // Reload tickets after successful import
            await loadTickets();
        } else {
            showUploadStatus('error', result.detail || 'Error importing tickets');
        }
    } catch (e) {
        showUploadStatus('error', 'Error uploading file');
    }
}

function showUploadStatus(type, message) {
    const status = document.getElementById('upload-status');
    status.className = `status ${type}`;
    status.textContent = message;
    status.style.display = 'block';
    if (type === 'success') {
        setTimeout(() => status.style.display = 'none', 3000);
    }
}


// Update ticket creation
document.getElementById('createTicketForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const data = {
        ticket_type: formData.get('ticket_type'),
        discounted: formData.get('discounted') === 'on',
        name_ticketinhaber: formData.get('name_ticketinhaber'),
        email_ticketinhaber: formData.get('email_ticketinhaber'),
        email_kaeufer: formData.get('email_kaeufer'),
        bestell_id: formData.get('bestell_id')
    };

    try {
        const response = await fetch('/tickets/create', {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            showCreateStatus('success', `Ticket created successfully! Number: ${result.ticket_number}`);
            e.target.reset();
            await loadTickets();  // Reload ticket list
        } else {
            showCreateStatus('error', result.detail || 'Error creating ticket');
        }
    } catch (e) {
        showCreateStatus('error', 'Error creating ticket');
    }
});

function showCreateStatus(type, message) {
    const status = document.getElementById('create-status');
    status.className = `status ${type}`;
    status.textContent = message;
    status.style.display = 'block';
    if (type === 'success') {
        setTimeout(() => status.style.display = 'none', 3000);
    }
}


// Update VVK export function
async function exportToVVK() {
    try {
        const response = await fetch('/tickets/convert-to-vvk', {
            method: 'POST',
            headers: getHeaders()
        });

        if (response.ok) {
            // Convert response to blob and trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'VVK_2025.xlsx';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showVVKStatus('success', 'VVK Excel file generated successfully');
        } else {
            const error = await response.json();
            showVVKStatus('error', error.detail || 'Error generating VVK file');
        }
    } catch (e) {
        showVVKStatus('error', 'Error generating VVK file');
    }
}

function showVVKStatus(type, message) {
    const status = document.getElementById('vvk-status');
    status.className = `status ${type}`;
    status.textContent = message;
    status.style.display = 'block';
    if (type === 'success') {
        setTimeout(() => status.style.display = 'none', 3000);
    }
}

// Add error handler for 401 responses
async function handleResponse(response) {
    if (response.status === 401) {
        localStorage.removeItem('authToken');
        window.location.href = '/static2/login.html';
        return null;
    }
    return response;
}

//print
async function printTickets() {
    try {
        const response = await fetch('/tickets/print', {
            headers: getHeaders()
        });

        if (!response.ok) throw new Error('Failed to fetch tickets');

        const tickets = await response.json();

        // Sort tickets by name in each category
        Object.keys(tickets).forEach(category => {
            tickets[category].sort((a, b) => a.name.localeCompare(b.name));
        });

        let printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
            <head>
                <title>Tickets Overview</title>
                <style>
                    @media print {
                        @page { 
                            margin: 1cm;
                            size: portrait;
                        }
                    }
                    body { 
                        font-family: Arial, sans-serif;
                        line-height: 1.4;
                        color: #000;
                    }
                    .page { 
                        page-break-after: always; 
                        padding: 15px;
                        position: relative;
                    }
                    .page-header {
                        text-align: center;
                        margin-bottom: 20px;
                        border-bottom: 2px solid #333;
                        padding-bottom: 10px;
                    }
                    .page-number {
                        position: absolute;
                        bottom: 20px;
                        right: 20px;
                        font-size: 11px;
                        color: #666;
                    }
                    table { 
                        width: 100%; 
                        border-collapse: collapse; 
                        margin-top: 15px;
                    }
                    th, td { 
                        border: 0.5px solid #999;
                        padding: 8px; 
                        text-align: left;
                        font-size: 11px;
                    }
                    th { 
                        border-bottom: 2px solid #666;
                        font-weight: bold;
                        text-transform: uppercase;
                        font-size: 10px;
                    }
                    tr:nth-child(even) {
                        background-color: #f9f9f9;
                    }
                    .trib-normal .page-header { 
                        border-bottom: 2px solid #333;
                    }
                    .trib-discounted .page-header {
                        border-bottom: 2px dashed #333;
                    }
                    .sitz-normal .page-header {
                        border-bottom: 2px dotted #333;
                    }
                    .sitz-discounted .page-header {
                        border-bottom: 2px double #333;
                    }
                    h2 { 
                        margin: 0;
                        font-size: 20px;
                        font-weight: bold;
                    }
                    .total-count {
                        font-size: 12px;
                        color: #666;
                        margin-top: 3px;
                    }
                    .qr-code {
                        font-family: monospace;
                        font-size: 9px;
                        word-break: break-all;
                    }
                    .footer {
                        position: fixed;
                        bottom: 10px;
                        left: 0;
                        right: 0;
                        text-align: center;
                        font-size: 9px;
                        color: #999;
                    }
                </style>
            </head>
            <body>
        `);

        const pageTemplates = [
            {
                className: 'trib-normal',
                title: 'Tribüne - Normal',
                icon: '🎫'
            },
            {
                className: 'trib-discounted',
                title: 'Tribüne - Ermäßigt',
                icon: '🎟️'
            },
            {
                className: 'sitz-normal',
                title: 'Sitz-/Stehplatz - Normal',
                icon: '💺'
            },
            {
                className: 'sitz-discounted',
                title: 'Sitz-/Stehplatz - Ermäßigt',
                icon: '🪑'
            }
        ];

        pageTemplates.forEach((template, index) => {
            const categoryKey = template.className.replace('-', '_');
            printWindow.document.write(`
                <div class="page ${template.className}">
                    <div class="page-header">
                        <h2>${template.icon} ${template.title}</h2>
                        <div class="total-count">Anzahl: ${tickets[categoryKey].length} Tickets</div>
                    </div>
                    <table>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Bestell-ID</th>
                            <th>QR Code</th>
                        </tr>
                        ${tickets[categoryKey].map(t => `
                            <tr>
                                <td>${t.name}</td>
                                <td>${t.email}</td>
                                <td>${t.order_id}</td>
                                <td class="qr-code">${t.qrcode || 'N/A'}</td>
                            </tr>
                        `).join('')}
                    </table>
                    <div class="page-number">Seite ${index + 1}/4</div>
                    <div class="footer">Waldburg-Tattoo 2025 - Erstellt am ${new Date().toLocaleDateString('de-DE')}</div>
                </div>
            `);
        });

        printWindow.document.write('</body></html>');
        printWindow.document.close();

        setTimeout(() => {
            printWindow.print();
        }, 500);
    } catch (error) {
        console.error('Error printing tickets:', error);
        alert('Error printing tickets. Please try again.');
    }
}