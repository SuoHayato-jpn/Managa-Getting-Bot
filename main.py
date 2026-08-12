"""
Main entry point for Manga Downloader Bot
Initializes bot, registers handlers, and starts scheduler
"""

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)
from config import BOT_TOKEN
from handlers.commands import (
    start_command,
    help_command,
    manga_search_command,
    my_subscriptions_command,
    stats_command,
    admin_command
)
from handlers.callbacks import (
    manga_details_callback,
    chapters_list_callback,
    download_chapter_callback,
    navigate_chapter_callback,
    subscribe_callback,
    unsubscribe_callback
)
from scheduler.update_checker import start_scheduler, stop_scheduler
from data.database import db
from utils.logger import logger

async def post_init(application: Application):
    """
    Called after bot is initialized
    """
    logger.info("Bot initialized successfully")
    
    # Start the update checker scheduler
    start_scheduler(application)
    logger.info("Scheduler started")

async def post_shutdown(application: Application):
    """
    Called when bot is shutting down
    """
    logger.info("Bot shutting down...")
    
    # Stop scheduler
    stop_scheduler()
    
    # Close database connection
    db.client.close()
    logger.info("Database connection closed")

def main():
    """
    Main function to start the bot
    """
    logger.info("Starting Manga Downloader Bot...")
    
    # Create application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # ============================================
    # REGISTER COMMAND HANDLERS
    # ============================================
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("manga", manga_search_command))
    application.add_handler(CommandHandler("mysubscriptions", my_subscriptions_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("admin", admin_command))
    
    # ============================================
    # REGISTER CALLBACK QUERY HANDLERS
    # ============================================
    application.add_handler(CallbackQueryHandler(manga_details_callback, pattern=r"^manga_"))
    application.add_handler(CallbackQueryHandler(chapters_list_callback, pattern=r"^chapters_"))
    application.add_handler(CallbackQueryHandler(download_chapter_callback, pattern=r"^download_"))
    application.add_handler(CallbackQueryHandler(navigate_chapter_callback, pattern=r"^navigate_"))
    application.add_handler(CallbackQueryHandler(subscribe_callback, pattern=r"^subscribe_"))
    application.add_handler(CallbackQueryHandler(unsubscribe_callback, pattern=r"^unsubscribe_"))
    
    # ============================================
    # START BOT
    # ============================================
    logger.info("Bot is running...")
    application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()