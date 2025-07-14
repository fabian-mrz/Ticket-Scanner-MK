import sqlite3
import random

first_names = [
    "Julius", "Lea", "Tim", "Sophie", "Jonas", "Mia", "Lukas", "Emma", "Paul", "Anna",
    "Max", "Marie", "Ben", "Laura", "Finn", "Lina", "Noah", "Clara", "Leon", "Sarah"
]
last_names = [
    "Berger", "Wagner", "Becker", "Keller", "Fischer", "Schneider", "Müller", "Schmidt", "Schulz", "Bauer",
    "Weber", "Koch", "Richter", "Wolf", "Neumann", "Schröder", "Krüger", "Meier", "Lehmann", "Krause"
]
domains = [
    "example.com", "test.de", "demo.local", "sample.org", "fakedomain.de"
]

def random_person():
    fn = random.choice(first_names)
    ln = random.choice(last_names)
    email = f"{fn.lower()}.{ln.lower()}@{random.choice(domains)}"
    return fn + " " + ln, email

def init_meta_db():
    conn = sqlite3.connect('meta.db')
    cursor = conn.cursor()

    # Create tables for configuration values and number pools
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS config_values (
        key TEXT PRIMARY KEY,
        value INTEGER,
        description TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS number_pools (
        pool_name TEXT NOT NULL,
        number INTEGER NOT NULL,
        used BOOLEAN DEFAULT FALSE,
        PRIMARY KEY (pool_name, number)
    )
    """)

    # Default configuration values
    default_config = {
        'trib_discount_max': (50, 'Maximum discounted tribune tickets'),
        'trib_normal_max': (200, 'Maximum normal tribune tickets'),
        'sitz_discount_max': (50, 'Maximum discounted seating tickets'),
        'sitz_normal_max': (200, 'Maximum normal seating tickets')
    }

    # Insert default config values
    for key, (value, description) in default_config.items():
        cursor.execute("""
        INSERT OR REPLACE INTO config_values (key, value, description)
        VALUES (?, ?, ?)
        """, (key, value, description))

    # Tribune pool numbers
    trib_numbers = list(range(125, 151)) + [160, 165, 170]
    # Sitz/Steh pool numbers
    sitz_numbers = list(range(250, 301))

    # Add numbers to pool (tribune)
    for num in trib_numbers:
        cursor.execute("""
        INSERT OR IGNORE INTO number_pools (pool_name, number, used)
        VALUES ('TRIB_START', ?, 0)
        """, (num,))

    # Add numbers to pool (sitz/steh)
    for num in sitz_numbers:
        cursor.execute("""
        INSERT OR IGNORE INTO number_pools (pool_name, number, used)
        VALUES ('SITZ_START', ?, 0)
        """, (num,))

    conn.commit()
    conn.close()

def allocate_and_create_test_tickets():
    meta_conn = sqlite3.connect('meta.db')
    meta_cursor = meta_conn.cursor()
    ticket_conn = sqlite3.connect('tickets.db')
    ticket_cursor = ticket_conn.cursor()

    # Create tables in tickets.db if not exist
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
    ticket_cursor.execute(f"CREATE TABLE IF NOT EXISTS trib {table_schema}")
    ticket_cursor.execute(f"CREATE TABLE IF NOT EXISTS sitz {table_schema}")

    # Allocate and create tickets for trib seats: allocated 125-151, 160, 165, 170, but only tickets for 125-131
    trib_allocated = list(range(125, 151)) + [160, 165, 170]
    trib_with_tickets = trib_allocated[:-20]  # leave last 20 numbers free (no ticket)
    for num in trib_allocated:
        used = num in trib_with_tickets
        meta_cursor.execute("UPDATE number_pools SET used=? WHERE pool_name='TRIB_START' AND number=?", (1 if used else 0, num))
        if used:
            name, email = random_person()
            discounted = random.randint(0, 1)
            ticket_type = "Tribüne ermäßigt" if discounted else "Tribüne"
            qrcode = f"{random.randint(1000000,9999999)}_{'ETRIB' if discounted else 'TRIB'}0{num}"
            einchecken = "" if random.random() > 0.5 else f"2025-07-05T18:{random.randint(10,59)}:{random.randint(10,59)}.821242+02:00"
            bestell_id = str(1200 + num)
            ticket_id = str(1300 + num)
            created_at = f"2025-04-27 {random.randint(8,13):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
            ticket_cursor.execute("""
                INSERT OR IGNORE INTO trib (
                    TicketNumber, qrcode, Ticket, Einchecken, Bestell_ID, Bestellstatus, Ticket_ID,
                    Name_Ticketinhaber, Email_Ticketinhaber, Name_Kaeufer, Email_Kaeufer, Discounted, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(num), qrcode, ticket_type, einchecken, bestell_id, "Abgeschlossen", ticket_id,
                name, email, name, email, discounted, created_at
            ))

    # Allocate and create tickets for sitz/steh seats: allocated 250-300, but only tickets for 250-280
    sitz_allocated = list(range(250, 301))
    sitz_with_tickets = sitz_allocated[:-20]  # leave last 20 numbers free (no ticket)
    for num in sitz_allocated:
        used = num in sitz_with_tickets
        meta_cursor.execute("UPDATE number_pools SET used=? WHERE pool_name='SITZ_START' AND number=?", (1 if used else 0, num))
        if used:
            name, email = random_person()
            discounted = random.randint(0, 1)
            ticket_type = "Sitz-/ Stehplatz ermäßigt" if discounted else "Sitz-/ Stehplatz"
            qrcode = f"{random.randint(1000000,9999999)}_{'ESTEH' if discounted else 'STEH'}0{num}"
            einchecken = "" if random.random() > 0.5 else f"2025-07-05T18:{random.randint(10,59)}:{random.randint(10,59)}.821242+02:00"
            bestell_id = str(3899 + num)
            ticket_id = str(3900 + num)
            created_at = f"2025-04-27 {random.randint(8,13):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
            ticket_cursor.execute("""
                INSERT OR IGNORE INTO sitz (
                    TicketNumber, qrcode, Ticket, Einchecken, Bestell_ID, Bestellstatus, Ticket_ID,
                    Name_Ticketinhaber, Email_Ticketinhaber, Name_Kaeufer, Email_Kaeufer, Discounted, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(num), qrcode, ticket_type, einchecken, bestell_id, "Abgeschlossen", ticket_id,
                name, email, name, email, discounted, created_at
            ))

    meta_conn.commit()
    ticket_conn.commit()
    meta_conn.close()
    ticket_conn.close()

if __name__ == "__main__":
    init_meta_db()
    allocate_and_create_test_tickets()
    print("Test data created successfully.")