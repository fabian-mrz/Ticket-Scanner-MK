import csv
import sqlite3

def create_tables(conn):
    cursor = conn.cursor()
    # Define common table schema with created_at
    table_schema = """(
        TicketNumber TEXT PRIMARY KEY,  
        qrcode TEXT NOT NULL,
        Ticket TEXT,
        Einchecken TEXT,
        Bestell_ID TEXT,             
        Bestellstatus TEXT,
        Ticket_ID TEXT UNIQUE,       
        Name_Ticketinhaber TEXT,
        Email_Ticketinhaber TEXT,
        Name_Kaeufer TEXT,
        Email_Kaeufer TEXT,
        Discounted INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    
    # Create both tables with the same schema
    cursor.execute(f"CREATE TABLE IF NOT EXISTS trib {table_schema}")
    cursor.execute(f"CREATE TABLE IF NOT EXISTS sitz {table_schema}")
    conn.commit()


# Create database and tables
conn = sqlite3.connect("tickets.db")
create_tables(conn)
conn.close()
