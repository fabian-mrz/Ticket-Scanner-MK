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

<img width="1055" height="1902" alt="image" src="https://github.com/user-attachments/assets/50fb45e7-bcee-4479-8d76-10f4fc29382e" />

### 2. **Admin Dashboard** (admin)
- `tickets.html` + `ticket.js`
- Search, edit, import, and print tickets
- Category and format-based printing

<img width="938" height="930" alt="Bildschirmfoto 2025-07-14 um 21 50 16" src="https://github.com/user-attachments/assets/6420687f-caa8-4af2-a681-201802e5ac72" />
<img width="2010" height="718" alt="image" src="https://github.com/user-attachments/assets/21f2b085-e15f-4137-9d9f-db0258c25388" />


### 3. **Seat Management** (admin)
- `seats.html`
- Manage ticket number pools and allocations

<img width="3158" height="1674" alt="image" src="https://github.com/user-attachments/assets/23e467b3-f90b-41af-94bf-d3f1358bc04a" />


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

##  Deployment & Security

This system is intended to be deployed on a **Linux host** with each component running in a **Python virtual environment** and served by **Uvicorn** (except for the backend). The deployment follows the principle of least privilege for enhanced security.

###  Components

Each service should run under a **dedicated system user** with **minimal privileges** to isolate responsibilities and reduce potential attack surfaces:

1. **Admin Service**

   * Command: `uvicorn api:app`
   * User: `admin_service`

2. **Scanner API** *(publicly exposed)*

   * Command: `uvicorn main:app`
   * User: `scanner_service`
   * **Exposed via NGINX reverse proxy**

3. **Backend Service** *(headless)*

   * Command: `xvfb-run -a python3 final.py`
   * User: `backend_service`

###  Security Guidelines

* **Service Isolation**: Each service must run under a separate Linux user. For example:

  ```bash
  sudo adduser --system --no-create-home admin_service
  sudo adduser --system --no-create-home scanner_service
  sudo adduser --system --no-create-home backend_service
  ```

  Adjust file permissions and ownership accordingly.

* **Least Privilege Principle**: Ensure each user only has access to the files and environment variables necessary for its service.

* **Public Exposure**:
  ⚠️ **The Scanner API was the only service publicly exposed**.
  It should be routed through a hardened **NGINX** reverse proxy with:

  * TLS enabled
  * Rate limiting
  * IP whitelisting (if feasible)
  * Basic auth or other authentication if appropriate
  * Example config is availble under scanner

* **Virtual Environments**:
  Use a separate Python virtual environment per service to avoid dependency conflicts and improve isolation:

  ```bash
  python3 -m venv /opt/envs/admin_env
  python3 -m venv /opt/envs/scanner_env
  python3 -m venv /opt/envs/backend_env
  ```

* **Process Management**:
  Use **`systemd`** service files to manage startup, shutdown, logging, and restarts for each component. For example:

  ```ini
  [Unit]
  Description=Scanner API Service
  After=network.target

  [Service]
  User=scanner_service
  Group=scanner_service
  WorkingDirectory=/opt/scanner
  ExecStart=/opt/envs/scanner_env/bin/uvicorn main:app --host 127.0.0.1 --port 8000
  Restart=on-failure

  [Install]
  WantedBy=multi-user.target
  ```

### ⚠️ Disclaimer

> This system is **experimental** and comes with **no guarantees or warranties**.
> You are responsible for securing, auditing, and maintaining the deployment. Use **at your own risk**.

