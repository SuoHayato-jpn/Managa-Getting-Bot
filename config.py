"""
Configuration file for Manga Downloader Bot
Loads environment variables and defines bot settings
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================
# BOT CONFIGURATION
# ============================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

# ============================================
# DATABASE CONFIGURATION
# ============================================
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "manga_bot_db")

# ============================================
# SCRAPING CONFIGURATION
# ============================================
# Request headers with rotating User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# Maximum concurrent downloads
MAX_CONCURRENT_DOWNLOADS = 3

# ============================================
# PDF CONFIGURATION
# ============================================
# Image compression quality (0-100)
IMAGE_COMPRESSION_QUALITY = 75

# Maximum image dimensions (width, height)
MAX_IMAGE_SIZE = (1200, 1800)

# Temporary directory for PDF generation
TEMP_DIR = "temp_pdfs"

# ============================================
# SCHEDULER CONFIGURATION
# ============================================
# Check for new chapters every 45 minutes (in minutes)
UPDATE_CHECK_INTERVAL = 45

# ============================================
# CACHE CONFIGURATION
# ============================================
# Cache TTL in seconds (7 days)
CACHE_TTL = 7 * 24 * 60 * 60

# ============================================
# RENDER OPTIMIZATION
# ============================================
# Enable memory-efficient mode for Render Free Tier
MEMORY_EFFICIENT_MODE = True

# Maximum file size in MB (Telegram limit is 50MB)
MAX_FILE_SIZE_MB = 45