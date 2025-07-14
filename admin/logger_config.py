import logging

def setup_logger():
    """Configure shared logger for the ticket system"""
    logger = logging.getLogger('ticket_system')
    logger.setLevel(logging.INFO)
    
    # Create handlers if they don't exist
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler('ticket_system.log')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger