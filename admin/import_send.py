#full
# import
##create db and import once
import sqlite3
import csv
import os
import shutil
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.utils import formataddr
from email.mime.text import MIMEText
from email import encoders
from email.mime.image import MIMEImage
from PIL import Image, ImageDraw, ImageFont
import qrcode
import configparser
import random
import tempfile
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
import time  # Add this import
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from logger_config import setup_logger

# Setup logging
logger = setup_logger()

ALLOWED_TABLES = {'trib', 'sitz'}

def validate_table_name(table_name):
    """Validate table name against whitelist"""
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table_name}")
    return table_name


# Configuration for email credentials
config = configparser.ConfigParser()
config.read("config.ini")
username = config["EMAIL"]["username"]
password = config["EMAIL"]["password"]

tickets_db= "../data/tickets.db"
meta_db = "../data/meta.db"

def get_config_value(key):
    """Get a configuration value from the meta database"""
    try:
        with sqlite3.connect(meta_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config_values WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting config value for {key}: {e}")
        return None

def update_config_value(key, value):
    """Update a configuration value in the meta database"""
    try:
        with sqlite3.connect(meta_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE config_values 
            SET value = ? 
            WHERE key = ?
            """, (value, key))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating config value for {key}: {e}")
        return False

def get_next_ticket_number(conn, table_name):
    """Get next available ticket number from the pool"""
    try:
        # Validate table name
        
        pool_name = "TRIB_START" if table_name == "trib" else "SITZ_START"
        
        # Use the provided connection instead of closing it
        meta_cursor = conn.cursor()
        
        # Get next available number from pool
        meta_cursor.execute("""
            SELECT number 
            FROM number_pools 
            WHERE pool_name = ? AND used = FALSE 
            ORDER BY number ASC 
            LIMIT 1
        """, (pool_name,))
        
        result = meta_cursor.fetchone()
        if result is None:
            raise ValueError(f"No more numbers available in {pool_name} pool")
            
        number = result[0]
        
        # Mark number as used
        meta_cursor.execute("""
            UPDATE number_pools 
            SET used = TRUE 
            WHERE pool_name = ? AND number = ?
        """, (pool_name, number))
        
        conn.commit()
        
        return number
        
    except Exception as e:
        logger.error(f"Error getting next ticket number: {e}")
        raise
    
def decrease_ticket_limit(ticket_type, discounted):
    """Decrease the appropriate ticket limit in meta database"""
    limit_key = None
    if ticket_type == "trib":
        limit_key = "trib_discount_max" if discounted else "trib_normal_max"
    else:
        limit_key = "sitz_discount_max" if discounted else "sitz_normal_max"
    
    current_limit = get_config_value(limit_key)
    if current_limit and current_limit > 0:
        update_config_value(limit_key, current_limit - 1)
        logger.info(f"Decreased {limit_key} to {current_limit - 1}")
        if current_limit <= 3:
            logger.warning(f"Warning: {limit_key} is now at 2, consider restocking")
    else:
        logger.warning(f"Cannot decrease {limit_key} as it's already at 0")

def parse_ticket_line(row):
    ticket_type = row["Ticket"]
    discounted = "ermäßigt" in ticket_type
    if "Tribüne" in ticket_type:
        table_name = "trib"
    else:
        table_name = "sitz"
    return discounted, table_name

def create_ticket(qr_text, ticket_type, ticket_number, output_path):
    try:
        # Create QR code with smaller size
        qr = qrcode.QRCode(
            version=1, 
            error_correction=qrcode.constants.ERROR_CORRECT_L, 
            box_size=int(20 * 0.4),  # Reduced box size
            border=4  # Reduced border
        )
        qr.add_data(qr_text)
        qr.make(fit=True)
        qr_img = qr.make_image(fill='black', back_color='white')

        # Load and prepare ticket image with reduced size
        if "Tribüne" in ticket_type:
            ticket_img = Image.open("./trib.jpg")
        else:
            ticket_img = Image.open("./sitz.jpg")

        # Resize the base ticket image
        original_size = ticket_img.size
        ticket_img = ticket_img.resize((int(original_size[0] * 0.7), int(original_size[1] * 0.7)), Image.Resampling.LANCZOS)

        # Adjust QR position for new size
        qr_position = (int(920 * 0.7), int(470 * 0.7))
        ticket_img.paste(qr_img, qr_position)

        # Create text layer with adjusted size
        txt_img = Image.new('RGBA', ticket_img.size, (255, 255, 255, 0))
        txt_draw = ImageDraw.Draw(txt_img)
        
        # Adjust font size for smaller image
        font_path = "./arial.ttf"
        font_size = 25  # Reduced font size
        font = ImageFont.truetype(font_path, font_size)

        # Adjust text positions for new size
        text_positions = {
            'qr_text1': (int(320 * 0.7), int(930 * 0.7)),
            'qr_text2': (int(320 * 0.7), int(1120 * 0.7))
        }
        
        for position in text_positions.values():
            txt_draw.text(
                position, 
                qr_text,
                font=font, 
                fill="black"
            )

        # Rotate and composite text layer
        rotated_txt = txt_img.rotate(90, expand=False)
        ticket_img = Image.alpha_composite(ticket_img.convert('RGBA'), rotated_txt)

        # Save as JPEG with optimization
        ticket_img = ticket_img.convert('RGB')
        ticket_img.save(
            output_path, 
            "JPEG",
            optimize=True,
            quality=85  # Reduced quality for JPEG
        )
        logger.info(f"Optimized ticket saved to {output_path}")
        
        # Log file size
        file_size = os.path.getsize(output_path) / 1024  # Size in KB
        logger.info(f"Ticket file size: {file_size:.2f} KB")

        return True  # Return True on successful creation
        
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        return False  # Return False on failure

def send_email_with_attachments(email_kaufer, bestell_id, attachments_folder):
    try:
        msg = MIMEMultipart('related')
        msgAlternative = MIMEMultipart('alternative')
        msg.attach(msgAlternative)
        msg['From'] = formataddr(("Ticket System", username))
        msg['To'] = email_kaufer
        msg['Subject'] = f"Ihre Tickets für das Tattoo 2025"

        # Add logo image
        with open("./logo.png", "rb") as logo_file:
            logo_img = MIMEImage(logo_file.read())
            logo_img.add_header('Content-ID', '<logo_image>')
            logo_img.add_header('Content-Disposition', 'inline', filename="logo.png")
            logo_img.add_header('X-Attachment-Id', 'logo_image')
            logo_img.add_header('Content-Type', 'image/png; name="logo.png"')
            msg.attach(logo_img)

        # Add sponsors image
        with open("./sponsors.jpg", "rb") as sponsors_file:
            sponsors_img = MIMEImage(sponsors_file.read())
            sponsors_img.add_header('Content-ID', '<sponsors_image>')
            sponsors_img.add_header('Content-Disposition', 'inline', filename="sponsors.jpg")
            sponsors_img.add_header('X-Attachment-Id', 'sponsors_image')
            sponsors_img.add_header('Content-Type', 'image/jpeg; name="sponsors.jpg"')
            msg.attach(sponsors_img)


        # HTML Email Template matching website style with improved styling
        html = f"""
        <html>
            <head>
            <style>
                body {{
                font-family: 'Open Sans', Arial, sans-serif;
                line-height: 1.6;
                color: #333333;
                background-color: #f0f0f0;
                margin: 0;
                padding: 0;
                }}
                .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                }}
                .header {{
                background-color: #303030;
                padding: 25px;
                text-align: center;
                border-bottom: 3px solid #4CA64C; /* Green accent line */
                }}
                .header img {{
                max-width: 150px;
                height: auto;
                }}
                .content {{
                padding: 40px 25px;
                background-color: #ffffff;
                }}
                h1 {{
                color: #303030;
                font-size: 26px;
                margin-bottom: 25px;
                font-weight: bold;
                text-align: center;
                border-bottom: 1px solid #eaeaea;
                padding-bottom: 15px;
                }}
                .info-box {{
                background-color: #f8f8f8;
                border-left: 4px solid #4CA64C; /* Green accent */
                padding: 20px;
                margin: 25px 0;
                border-radius: 0 4px 4px 0;
                }}
                .discount-alert {{
                background-color: #ffe8e0;
                border-left: 4px solid #ff6b4a;
                padding: 15px;
                margin: 20px 0;
                border-radius: 0 4px 4px 0;
                font-weight: bold;
                }}
                .footer {{
                background-color: #303030;
                color: #ffffff;
                text-align: center;
                padding: 25px;
                font-size: 13px;
                }}
                .footer a {{
                color: #8cd98c; /* Light green */
                text-decoration: none;
                font-weight: bold;
                }}
                .footer a:hover {{
                text-decoration: underline;
                }}
                .sponsors {{
                margin-top: 20px;
                text-align: center;
                padding: 20px;
                background-color: #f5f5f5;
                border-top: 1px solid #eaeaea;
                }}
                .sponsors img {{
                max-width: 100%;
                height: auto;
                border-radius: 4px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                ul {{
                padding-left: 20px;
                }}
                li {{
                margin-bottom: 8px;
                }}
                .signature {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px dashed #eaeaea;
                }}
                @media (prefers-color-scheme: dark) {{
                body {{
                    background-color: #222222;
                    color: #e0e0e0;
                }}
                .container {{
                    background-color: #303030;
                    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
                }}
                .content {{
                    background-color: #303030;
                    color: #e0e0e0;
                }}
                h1 {{
                    color: #ffffff;
                    border-bottom: 1px solid #444444;
                }}
                .info-box {{
                    background-color: #393939;
                    border-left: 4px solid #5db85d;
                }}
                .discount-alert {{
                    background-color: #482c26;
                    border-left: 4px solid #ff6b4a;
                }}
                .sponsors {{
                    background-color: #2a2a2a;
                    border-top: 1px solid #444444;
                }}
                .signature {{
                    border-top: 1px dashed #444444;
                }}
                }}
            </style>
            </head>
            <body>
            <div class="container">
                <div class="header">
                    <img src="cid:logo_image" data-outlook-trace="F:1|T:1" style="max-width: 150px; height: auto;">
                </div>

                <div class="content">
                <h1>Ihre Tickets sind da!</h1>
                <p>Sehr geehrte/r Konzertbesucher/in,</p>
                <p>vielen Dank für Ihre Bestellung (Bestell-ID: <strong>{bestell_id}</strong>). 
                   Im Anhang finden Sie Ihre Tickets für das Tattoo 2025.</p>
                
                <div class="info-box">
                    <strong>Wichtige Informationen:</strong>
                    <ul>
                    <li>Bitte bringen Sie die Tickets ausgedruckt mit oder zeigen Sie sie auf Ihrem Mobilgerät vor</li>
                    <li>Jedes Ticket enthält einen einzigartigen QR-Code</li>
                    <li>Ein Ticket ist nur für eine Person gültig</li>
                    <li>Der QR-Code wird beim Einlass gescannt</li>
                    </ul>
                </div>

                <div class="discount-alert">
                    <strong>⚠️ Wichtiger Hinweis für ermäßigte Tickets:</strong><br>
                    Für Ihr ermäßigtes Ticket halten Sie bitte beim Einlass einen entsprechenden Nachweis bereit.
                </div>

                <p>Wir freuen uns auf Ihren Besuch und eine wundervolle gemeinsame Zeit!</p>
                
                <div class="signature">
                    <p>Mit musikalischen Grüßen<br>
                    <strong>Ihr Musikverein Waldburg</strong></p>
                </div>
                </div>
             <div class="sponsors">
                    <img src="cid:sponsors_image" data-outlook-trace="F:1|T:1" style="width: 100%; max-width: 600px; height: auto;">
                </div>
                <div class="footer">
                <p>Dies ist eine automatisch generierte E-Mail. Bitte antworten Sie nicht darauf.</p>
                <p>© 2025 Musikverein Waldburg e.V.<br>
                <a href="https://www.mk-waldburg-hannober.de">www.mk-waldburg-hannober.de</a></p>
                </div>
            </div>
            </body>
        </html>
        """

        # Plain text alternative
        text = f"""
        Ihre Tickets sind da!
        
        Sehr geehrte/r Konzertbesucher/in,
        
        vielen Dank für Ihre Bestellung (Bestell-ID: {bestell_id}). Im Anhang finden Sie Ihre Tickets.
        
        Wichtige Informationen:
        - Bitte bringen Sie die Tickets ausgedruckt mit oder zeigen Sie sie auf Ihrem Mobilgerät vor
        - Jedes Ticket enthält einen einzigartigen QR-Code
        - Ein Ticket ist nur für eine Person gültig
        - Der QR-Code wird beim Einlass gescannt
        
        WICHTIGER HINWEIS:
        Für Ihr ermäßigtes Ticket halten Sie bitte beim Einlass einen entsprechenden Nachweis bereit.
        
        Wir freuen uns auf Ihren Besuch!
        
        Mit musikalischen Grüßen
        Ihr Musikverein Waldburg
        
        www.mk-waldburg-hannober.de
        
        Dies ist eine automatisch generierte E-Mail. Bitte antworten Sie nicht darauf.
        © 2025 Musikverein Waldburg e.V.
        """

        # Attach both versions
        part1 = MIMEText(text, 'plain', 'utf-8')
        part2 = MIMEText(html, 'html', 'utf-8')
        msgAlternative.attach(part1)
        msgAlternative.attach(part2)

        for filename in os.listdir(attachments_folder):
            path = os.path.join(attachments_folder, filename)
            if os.path.isfile(path):
                # Use application/pdf for better handling in email clients
                part = MIMEBase('application', 'jpeg')
                with open(path, 'rb') as file:
                    part.set_payload(file.read())
                encoders.encode_base64(part)
                
                # Add proper filename and content disposition
                part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=('utf-8', '', f"{filename}")  # Nice formatted name
                )
                # Add content type header
                part.add_header('Content-Type', 'image/jpeg', name=f"{filename}")
                msg.attach(part)

        try:
            with smtplib.SMTP("smtp.office365.com", 587) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {email_kaufer} for order {bestell_id}")
        except Exception as e:
            logger.error(f"SMTP Error: {e}")
            raise

        shutil.rmtree(attachments_folder)  # Remove folder after sending
        logger.info(f"Temp directory '{attachments_folder}' removed")

    except Exception as e:
        logger.error(f"Error sending email: {e}")
        if os.path.exists(attachments_folder):
            logger.warning(f"Email failed, Temp directory '{attachments_folder}' not removed")


def import_tickets(csv_path, db_path, expected_count=None):
    tickets_created = 0  # Initialize counter at the start
    try:
        conn = sqlite3.connect(db_path)
        logger.info(f"Successfully connected to the database: {db_path}")

        conn2 = sqlite3.connect(meta_db)
        logger.info("Connected to meta database")
        
        # First, get all existing ticket IDs
        cursor = conn.cursor()
        existing_tickets = set()
        for table in ['trib', 'sitz']:
            cursor.execute(f"SELECT Ticket_ID FROM {table}")
            existing_tickets.update(row[0] for row in cursor.fetchall())
        
        # Read and sort tickets by Bestell_ID to maintain order grouping
        all_tickets = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, fieldnames=[
                "Ticket", "Einchecken", "Bestell_ID", "Bestellstatus", "Ticket_ID",
                "Name_Ticketinhaber", "Email_Ticketinhaber", "Name_Kaeufer", "Email_Kaeufer"
            ])
            next(reader, None)  # Skip header
            all_tickets = [row for row in reader if row["Ticket_ID"] not in existing_tickets]
            
        if not all_tickets:
            logger.info("No new tickets to process")
            conn.close()
            return
            
        # Sort tickets by Bestell_ID to maintain order grouping
        all_tickets.sort(key=lambda x: x["Bestell_ID"])
        
        # Process tickets with the existing logic
        current_order = {
            'bestell_id': None,
            'folder_path': None,
            'tickets_to_import': []
        }

        for row in all_tickets:
            try:
                discounted, table_name = parse_ticket_line(row)
                ticket_id = row["Ticket_ID"]
                cursor = conn.cursor()
                cursor.execute(f"SELECT 1 FROM {table_name} WHERE Ticket_ID = ?", (ticket_id,))
                if cursor.fetchone():
                    logger.info(f"Ticket ID {ticket_id} already exists. Skipping.")
                    continue

                ticket_number = get_next_ticket_number(conn2, table_name)
                formatted_ticket = f"{'E' if discounted else ''}{'TRI0' if table_name == 'trib' else 'STEH0'}{ticket_number}"
                random_code = str(random.randint(1000000, 9999999))
                qrcode_value = f"{random_code}_{formatted_ticket}"

                # Handle new order
                bestell_id = row["Bestell_ID"]
                if bestell_id != current_order['bestell_id']:
                    # Send previous order's tickets if exists
                    if current_order['bestell_id']:
                        try:
                            send_email_with_attachments(row["Email_Kaeufer"], 
                                                      current_order['bestell_id'], 
                                                      current_order['folder_path'])
                            # Import tickets only after successful email
                            for ticket in current_order['tickets_to_import']:
                                cursor.execute(ticket['query'], ticket['params'])
                                decrease_ticket_limit(ticket['table_name'], ticket['discounted'])
                            conn.commit()
                        except Exception as e:
                            logger.error(f"Failed to send email for order {current_order['bestell_id']}: {e}")
                            if os.path.exists(current_order['folder_path']):
                                shutil.rmtree(current_order['folder_path'])
                            conn.rollback()
                            continue

                    # Setup new order
                    folder_path = os.path.join(os.getcwd(), bestell_id)
                    if not os.path.exists(folder_path):
                        os.makedirs(folder_path)
                    current_order = {
                        'bestell_id': bestell_id,
                        'folder_path': folder_path,
                        'tickets_to_import': []
                    }

                # Generate ticket image
                ticket_filename = f"{formatted_ticket}.jpg"
                ticket_filepath = os.path.join(current_order['folder_path'], ticket_filename)


                if create_ticket(qrcode_value, row["Ticket"], str(ticket_number), ticket_filepath):
                    tickets_created += 1
                    # Store ticket data for later import
                    current_order['tickets_to_import'].append({
                        'query': f"""INSERT INTO {table_name} (
                            TicketNumber, qrcode, Ticket, Einchecken, Bestell_ID, Bestellstatus,
                            Ticket_ID, Name_Ticketinhaber, Email_Ticketinhaber,
                            Name_Kaeufer, Email_Kaeufer, Discounted
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        'params': (
                            ticket_number, qrcode_value, row["Ticket"], row["Einchecken"],
                            bestell_id, row["Bestellstatus"], ticket_id,
                            row["Name_Ticketinhaber"], row["Email_Ticketinhaber"],
                            row["Name_Kaeufer"], row["Email_Kaeufer"], discounted
                        ),
                        'table_name': table_name,
                        'discounted': discounted
                    })
                else:
                    logger.error(f"Failed to create ticket for ID {ticket_id}")

            except Exception as e:
                logger.error(f"Error processing row: {row}. Error: {e}")
                if current_order['folder_path'] and os.path.exists(current_order['folder_path']):
                    shutil.rmtree(current_order['folder_path'])
                conn.rollback()

        # Process last order if exists
        if current_order['bestell_id']:
            try:
                send_email_with_attachments(row["Email_Kaeufer"], 
                                          current_order['bestell_id'], 
                                          current_order['folder_path'])
                # Import tickets only after successful email
                for ticket in current_order['tickets_to_import']:
                    cursor.execute(ticket['query'], ticket['params'])
                    decrease_ticket_limit(ticket['table_name'], ticket['discounted'])
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to send email for final order {current_order['bestell_id']}: {e}")
                if os.path.exists(current_order['folder_path']):
                    shutil.rmtree(current_order['folder_path'])
                conn.rollback()

        conn.close()
        logger.info("Database connection closed.")


        # At the end, verify counts
        if expected_count is not None:
            if tickets_created == expected_count:
                logger.info(f"Successfully created all {expected_count} expected tickets")
            else:
                logger.warning(f"Mismatch in ticket count! Expected: {expected_count}, Created: {tickets_created}")
        
        return tickets_created
        
    except Exception as e:
        logger.error(f"Error importing tickets: {e}")
        if 'conn' in locals():
            conn.close()
        return tickets_created