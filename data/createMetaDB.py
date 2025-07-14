import sqlite3

def init_meta_db():
    """Initialize or update the meta database with configuration values"""
    try:
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

        # Example: Add number ranges/pools
        trib_numbers = list(range(125, 151))  # Range 125-150
        trib_specific = [160, 165, 170]       # Specific numbers
        
        # Combine all tribune numbers
        all_trib_numbers = trib_numbers + trib_specific
        
        # Add numbers to pool
        for num in all_trib_numbers:
            cursor.execute("""
            INSERT OR IGNORE INTO number_pools (pool_name, number)
            VALUES ('TRIB_START', ?)
            """, (num,))

        conn.commit()
        return conn
    except Exception as e:
        logging.error(f"Error initializing meta database: {e}")
        raise

init_meta_db()