import time
import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import configparser
from tempfile import mkdtemp  # Add at top with other imports
from import_send import import_tickets
from bs4 import BeautifulSoup
import csv
import shutil
from logger_config import setup_logger

# Setup logging
logger = setup_logger()

# Variables
LAST_TICKET_COUNT_FILE = "last_ticket_count.txt"
TICKETS_PROCESSED_COUNT = 0
MAX_TICKETS_PER_PAGE = 20
MAX_PAGES_TO_CHECK = 5

# Load configuration ini
config = configparser.ConfigParser()
config.read("config.ini")

#Get url from configuration ini
BASE_ATTENDEES_URL = config.get("wordpress", "base_url")

def setup_driver():
    """Configure and initialize Chrome WebDriver"""
    try:
        options = Options()
        options.headless = True

        # Generate a unique user data dir per session
        temp_profile = mkdtemp(prefix="chrome-profile-")
        options.add_argument(f'--user-data-dir={temp_profile}')


        service = Service("/usr/bin/chromedriver")  # Specify the path to the ChromeDriver binary

        
        # Set download preferences
        download_dir = os.getcwd()
        prefs = {
            'download.default_directory': download_dir,
            'download.prompt_for_download': False,
            'download.directory_upgrade': True,
            'safebrowsing.enabled': True
        }
        options.add_experimental_option('prefs', prefs)
        
        return webdriver.Chrome(service=service, options=options)
    except Exception as e:
        logger.error(f"Failed to setup WebDriver: {e}")
        raise


def parse_table_from_page(driver, page_number):
    """Parse tickets table from a specific page"""
    try:
        url = f"{BASE_ATTENDEES_URL}{page_number}"
        driver.get(url)
        time.sleep(2)  # Wait for table to load
        return parse_table_to_csv(driver)
    except Exception as e:
        logger.error(f"Error parsing page {page_number}: {e}")
        return None

def parse_table_to_csv(driver):
    """Parse the attendee table and create a CSV file"""
    try:
        # Wait for table to be present
        table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#event-tickets__attendees-admin-form table"))
        )

        # Create temporary CSV file
        temp_csv = f"temp_tickets_{int(time.time())}.csv"
        
        with open(temp_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Write header with exact column names
            writer.writerow([
                "Ticket",
                "Einchecken",
                "Bestell ID",
                "Bestellstatus", 
                "Ticket ID",
                "Name des Ticketinhabers",
                "E-Mail-Adresse des Ticketinhabers",
                "Name des Käufers",
                "Kunden E-Mail-Adresse"
            ])
            
            # Process each row
            rows = table.find_elements(By.CSS_SELECTOR, "#the-list tr")
            logger.info(f"Found {len(rows)} ticket rows")
            
            for row in rows:
                try:
                    # Extract ticket type
                    ticket_type_elem = row.find_element(
                        By.CSS_SELECTOR, 
                        ".tec-tickets__admin-table-attendees-ticket-name"
                    )
                    ticket_type = ticket_type_elem.text.strip()
                    
                    # Get attendee info
                    attendee_btn = row.find_element(
                        By.CSS_SELECTOR, 
                        "button.button-link.row-title"
                    )
                    
                    # Extract data from button attributes
                    ticket_id = attendee_btn.get_attribute("data-attendee-id")
                    attendee_name = attendee_btn.get_attribute("data-attendee-name")
                    attendee_email = attendee_btn.get_attribute("data-attendee-email")
                    
                    # Get order ID from link in status column
                    status_elem = row.find_element(By.CSS_SELECTOR, ".tec-tickets__admin-table-attendees-order-status a")
                    order_id = status_elem.get_attribute("href").split("post=")[1].split("&")[0]
                    
                    # Check if ticket is checked in
                    try:
                        row.find_element(By.CSS_SELECTOR, ".tickets_uncheckin")
                        check_in = ""
                    except:
                        check_in = ""  # Empty string for not checked in
                    
                    # Write row with exact column order
                    writer.writerow([
                        ticket_type,
                        check_in,
                        order_id,
                        "Abgeschlossen",
                        ticket_id,
                        attendee_name,
                        attendee_email,
                        attendee_name,  # Same as attendee name
                        attendee_email  # Same as attendee email
                    ])
                    
                except Exception as e:
                    logger.error(f"Error processing row: {e}")
                    continue
            
            logger.info(f"Successfully created CSV file: {temp_csv}")
            return temp_csv
            
    except Exception as e:
        logger.error(f"Error parsing table: {e}")
        return None
    
def get_last_ticket_count():
    try:
        with open(LAST_TICKET_COUNT_FILE, 'r') as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return 0

def save_ticket_count(count):
    with open(LAST_TICKET_COUNT_FILE, 'w') as f:
        f.write(str(count))

def cleanup_temp_files():
    """Clean up temporary CSV files"""
    try:
        for file in os.listdir(os.getcwd()):
            if file.startswith('temp_tickets_') and file.endswith('.csv'):
                os.remove(file)
                logger.info(f"Cleaned up temporary file: {file}")
    except Exception as e:
        logger.error(f"Error cleaning up temporary files: {e}")

def check_for_new_tickets(driver):
    """Check WordPress for new tickets and return the expected count of new tickets"""
    try:
        ticket_count_element = driver.find_element(
            By.XPATH, 
            '//*[@id="event-tickets__attendees-admin-form"]/div[1]/div[4]/span[1]'
        )
        # Extract only numbers from text (e.g., "35 Einträge" -> "35")
        current_count = int(''.join(filter(str.isdigit, ticket_count_element.text)))
        last_count = get_last_ticket_count()
        
        #logger.info(f"Current ticket count: {current_count}, Last count: {last_count}")
        
        if current_count > last_count:
            expected_new_tickets = current_count - last_count
            logger.info(f"New tickets detected! Count increased by {expected_new_tickets}")
            save_ticket_count(current_count)
            return expected_new_tickets
        return 0

    except Exception as e:
        logger.error(f"Error checking ticket count: {e}")
        return 0

def download_tickets(driver):
    """Download tickets from WordPress"""
    try:
        logger.info("Downloading tickets from WordPress...")
    
        # Download CSV
        download_button = driver.find_element(By.XPATH, '//*[@id="event-tickets__attendees-admin-form"]/div[1]/div[2]/a[1]')
        download_button.click()
        time.sleep(7)  # Wait for download

        # Verify download
        csv_files = [f for f in os.listdir(os.getcwd()) if f.endswith('.csv')]
        if not csv_files:
            logger.error("No CSV file downloaded")
            return False

        logger.info("Tickets downloaded successfully")
        return True

    except Exception as e:
        logger.error(f"Error downloading tickets: {e}")
        #call PD
        return False

def process_tickets():
    while True:  # Outer loop for restart functionality
        driver = None
        try:
            # Setup WebDriver
            options = Options()
            driver = webdriver.Chrome(options=options)
            
            logger.info("Checking WP for new tickets")
            driver.get(BASE_ATTENDEES_URL+"1")

            time.sleep(5)

            # Login to WordPress
            try:
                username_field = driver.find_element(By.XPATH, '//*[@id="user_login"]')
                username_field.send_keys(config["wordpress"]["username"])
                
                password_field = driver.find_element(By.XPATH, '//*[@id="user_pass"]')
                password_field.send_keys(config["wordpress"]["password"])
                password_field.send_keys(Keys.RETURN)
                time.sleep(7)
            except Exception as e:
                logger.error(f"Error logging into WordPress: {e}")
                raise

            # Inner loop for regular operations
            while True:
                tickets_created = 0
                try:
                    driver.get(f"{BASE_ATTENDEES_URL}1")  # Start with first page
                    expected_new_tickets = check_for_new_tickets(driver)
                    
                    if expected_new_tickets > 0:
                        remaining_tickets = expected_new_tickets
                        current_page = 1
                        
                        while remaining_tickets > 0 and current_page <= MAX_PAGES_TO_CHECK:
                            logger.info(f"Processing page {current_page}, remaining tickets: {remaining_tickets}")
                            
                            csv_file = parse_table_from_page(driver, current_page)
                            if csv_file:
                                logger.error(f"Failed to parse page {current_page}")
                                break
                            
                            current_page += 1
                            
                        if remaining_tickets > 0:
                            if current_page > MAX_PAGES_TO_CHECK:
                                logger.error("CRITICAL: Maximum page limit reached!")
                                logger.error(f"Still {remaining_tickets} tickets remaining. MANUAL INTERVENTION REQUIRED!")
                            else:
                                logger.error(f"Failed to import all tickets. {remaining_tickets} remaining")
                        else:
                            logger.info(f"Successfully processed all {expected_new_tickets} tickets")
                            cleanup_temp_files()
                    
                    time.sleep(15)
                
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    if "Read timed out" in str(e) or "HTTPConnectionPool" in str(e):
                        raise
                    time.sleep(60)
                    continue


                
        except KeyboardInterrupt:
            logger.info("Shutting down ticket processing...")
            break
        except Exception as e:
            logger.error(f"Critical error, restarting process: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            time.sleep(60)
            continue
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            cleanup_temp_files()

if __name__ == "__main__":
    # Load configuration
    config = configparser.ConfigParser()
    config.read("config.ini")
    
    logger.info("Starting ticket processing system...")
    process_tickets()