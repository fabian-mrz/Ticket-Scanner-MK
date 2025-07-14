from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
import logging
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import secrets
import bcrypt
from typing import Optional
from jose import jwt  
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import re
import sqlite3
from datetime import datetime

ALLOWED_TABLES = {"trib", "sitz"}


db_path = "../data/tickets.db"

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://domain.net", "http://domain.net"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],  # Only necessary methods
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

app.mount("/static", StaticFiles(directory="./static"), name="static")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TicketScan(BaseModel):
    qr_code: str

# Add these constants
SECRET_KEY = "asdfahwaertasgfasdgasdf"  # Change this to a secure random key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# Define users (in production, store these in a database with hashed passwords)
USERS = {
    "ticket1": bcrypt.hashpw("admin-password".encode(), bcrypt.gensalt()),
    "ticket2": bcrypt.hashpw("user-password".encode(), bcrypt.gensalt()),
    "ticket3": bcrypt.hashpw("user-password".encode(), bcrypt.gensalt()),
    "ticket4": bcrypt.hashpw("user-password".encode(), bcrypt.gensalt()),
    "ticket5": bcrypt.hashpw("user-password".encode(), bcrypt.gensalt()),
    "ticket6": bcrypt.hashpw("user-password".encode(), bcrypt.gensalt()),
}

class LoginRequest(BaseModel):
    username: str
    password: str

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return username
    except jwt.JWTError:  
        raise HTTPException(status_code=401, detail="Invalid authentication token")


def get_ticket_info(qr_code: str):
    try:
        # Eingabe validieren (nur erlaubte Zeichen)
        if not re.match(r"^[a-zA-Z0-9_-]+_[a-zA-Z0-9]+$", qr_code):
            logger.info(f"Invalid ticket format: {qr_code}")
            return {"status": "error", "detail": "Ungültiges Ticket-Format"}, 400

        # QR-Code in Teile zerlegen
        random_code, ticket_number = qr_code.split('_')

        # Tabelle bestimmen
        table = "trib" if ticket_number.lstrip('E').startswith('TRI0') else "sitz"
        if table not in ALLOWED_TABLES:
            return {"status": "error", "detail": "Ungültiger Ticket-Typ"}, 400#
    
        
        # Check if database exists and is accessible
        if not Path(db_path).exists():
            logger.error(f"Database not found at {db_path}")
            return {"status": "error", "detail": "Database not found"}, 500
            
        if not os.access(db_path, os.R_OK | os.W_OK):
            logger.error(f"Insufficient permissions for database at {db_path}")
            return {"status": "error", "detail": "Database access error"}, 500
        

        # Verbindung zur Datenbank herstellen und Ticket-Informationen abrufen
        print(f"Connecting to database at {db_path}")
        print(f"Using table: {table}")
        # qr code
        print(f"QR Code: {qr_code}")

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Ticket, Einchecken, TicketNumber, Discounted, Name_Ticketinhaber 
                FROM {} WHERE qrcode = ?""".format(table), (qr_code,))
            result = cursor.fetchone()

            if not result:
                return {"status": "error", "detail": "Ticket nicht gefunden"}, 404

            ticket_type, checked_in, ticket_number, discounted, name = result

            # Wenn schon eingecheckt
            if checked_in:
                berlin_time = datetime.fromisoformat(checked_in).astimezone(ZoneInfo("Europe/Berlin"))
                print(f"Checked in time: {berlin_time}")
                return {
                    "status": "already_used",
                    "ticket_type": ticket_type,
                    "ticket_number": ticket_number,
                    "discounted": bool(discounted),
                    "name": name,
                    "checked_in": berlin_time.isoformat()  # This will include timezone info
                }, 200


            berlin_time = datetime.now(ZoneInfo("Europe/Berlin"))
            cursor.execute(f"UPDATE {table} SET Einchecken = ? WHERE qrcode = ?", 
                (berlin_time.isoformat(), qr_code))  # Store with timezone info            
            
            return {
                "status": "success",
                "ticket_type": ticket_type,
                "ticket_number": ticket_number,
                "discounted": bool(discounted),
                "name": name,
                "checked_in": None
            }, 200

    except Exception as e:
        logger.error(f"Error checking ticket: {str(e)}")
        return {"status": "error", "detail": "Fehler bei der Ticket-Überprüfung"}, 500
    
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/static/login.html")

@app.get("/api/check-token")
async def check_token(current_user: str = Depends(get_current_user)):
    return {"status": "valid"}

# Update the login endpoint
@app.post("/api/login")
@limiter.limit("5/minute")
async def login(login_data: LoginRequest, request: Request):
    if login_data.username not in USERS:
        logger.warning(f"Failed login attempt for username: {login_data.username} from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    stored_password_hash = USERS[login_data.username]
    if not bcrypt.checkpw(login_data.password.encode(), stored_password_hash):
        logger.warning(f"Failed login attempt (wrong password) for username: {login_data.username} from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    logger.info(f"Successful login for user: {login_data.username} from IP: {request.client.host}")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {"sub": login_data.username, "exp": datetime.utcnow() + access_token_expires},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Permissions-Policy"] = "camera=(self)"
    
    # Beispiel für eine strenge CSP
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self';"
    )
    
    return response


# Update the check-ticket endpoint
@app.post("/api/check-ticket")
async def check_ticket(
    ticket: TicketScan,
    request: Request,
    current_user: str = Depends(get_current_user)
):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{current_time}] User '{current_user}' scanning ticket: {ticket.qr_code}")
    
    try:
        result, status_code = get_ticket_info(ticket.qr_code)
        
        if status_code != 200:
            logger.warning(f"[{current_time}] Failed scan by user '{current_user}': {result['detail']}")
            return JSONResponse(
                status_code=status_code,
                content=result
            )
        
        logger.info(f"[{current_time}] Successful scan by user '{current_user}': {result['status']} for ticket {ticket.qr_code}")
        return result
        
    except Exception as e:
        logger.error(f"[{current_time}] Error for user '{current_user}' processing ticket: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": "Fehler bei der Ticket-Überprüfung"
            }
        )