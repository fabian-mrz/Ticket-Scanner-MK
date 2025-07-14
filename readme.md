# Ticket Scanner System for Waldburg-Tattoo 2025

This project provides a **fully free and modular ticketing system**, including both **frontend and backend**, specifically built for the **Waldburg-Tattoo 2025** event. It integrates with the **Events Tickets WordPress plugin**, offering a streamlined QR code-based check-in process, customizable seat management, secure admin tools, and full automation capabilities.

> ⚠️ This repository is a **new version** (since commits from the original repo contained private domain information). Use at your own risk.

---

## Purpose

This system was built to:

- Automate ticket import from WordPress (via Selenium)
- Provide an easy QR code check-in interface
- Allow modular management of seats, formats, and ticket types
- Support CSV import from the Events Tickets WordPress plugin, Excel export, and printing of sold tickets

---

## Main Components

### Ticket Import from WordPress (`final.py`)

Automates the ticket retrieval process from a WordPress site using Selenium:
- Logs into the WordPress admin
- Extracts ticket data from tables provided by the Events Tickets management plugin
- Imports data into SQLite

**Key functions:**
  - `setup_driver`
  - `parse_table_to_csv`
  - `check_for_new_tickets`
  - `process_tickets`

---

### API Server (`api.py`)

A FastAPI-based backend that handles:
- Ticket listing, editing, and validation
- QR code generation and printing
- Log management
- File uploads

**Example API Endpoints:**
- `GET /tickets`
- `POST /tickets/upload`
- `GET /api/logs`
- `POST /tickets/print`

---

## 💻 Frontend

### 1. **Scanner Interface** (scanner)
- `index.html` + `script.js`
- Real-time QR code scanning using [`html5-qrcode`](https://github.com/mebjas/html5-qrcode)
- Manual ticket ID entry as a fallback

### 2. **Admin Dashboard** (admin)
- `tickets.html` + `ticket.js`
- Search, edit, import, and print tickets
- Category and format-based printing

### 3. **Seat Management** (admin)
- `seats.html`
- Manage ticket number pools and allocations

### 4. **System Logs** (admin)
- `logs.html`
- View log entries from `ticket_system.log` in-browser

---

## Database

- `tickets.db`: Main ticket data (IDs, names, seat numbers, scanned status)
- `meta.db`: Auxiliary info such as ticket number ranges

---

## Technologies Used

**Backend:**
- Python
- FastAPI / Uvicorn
- SQLite
- Selenium

**Frontend:**
- HTML/CSS
- Vanilla JavaScript
- [`html5-qrcode`](https://github.com/mebjas/html5-qrcode)

---

## Notable Features

- Automated WordPress ticket import via Selenium
- Live QR code scanning with fallback manual entry
- Admin dashboard for editing and printing
- Secure login system for admin access
- Categorized printing of ticket PDFs
- Web-based log viewer

---

## Key Files

| File/Folder        | Purpose                                 |
|--------------------|------------------------------------------|
| `final.py`         | WordPress automation and ticket import   |
| `api.py`           | FastAPI backend for administration       |
| `script.js`        | Frontend ticket scanner logic            |
| `ticket.js`        | Admin panel logic                        |
| `index.html`       | Check-in UI                              |
| `tickets.html`     | Ticket management UI                     |
| `logs.html`        | Log viewer UI                            |
| `seats.html`       | Number/seat pool editor                  |
| `tickets.db`       | SQLite DB for ticket data                |
| `meta.db`          | SQLite DB for metadata                   |

---

## Development Notes

- Written with the assistance of **GitHub Copilot** (GPT-4.1) and **Claude Sonnet 3.5**
- Can be adapted for other small/medium event use cases

---

## Deployment & Security

> ⚠️ The **only publicly exposed component** was the scanner API via NGINX.  
> Use this system **at your own risk**. No guarantees or warranties are provided.
