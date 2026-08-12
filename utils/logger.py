"""
Logging configuration for the bot
"""

import logging
import sys
from config import MEMORY_EFFICIENT_MODE

def setup_logger():
    """
    Configure logging with appropriate level and format
    """
    # Set log level based on memory efficiency mode
    log_level = logging.INFO if MEMORY_EFFICIENT_MODE else logging.DEBUG
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
    
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logger()