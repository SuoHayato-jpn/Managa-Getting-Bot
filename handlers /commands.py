"""
Command handlers for the Telegram bot
Handles /start, /help, /manga, /mysubscriptions, /stats commands
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.scraper import scraper
from data.database import db
from utils.queue_manager import task_queue
from utils.logger import logger

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command
    Welcomes user and shows basic instructions
    """
    user = update.effective_user
    
    # Add user to database
    await db.add_user(user.id, user.username, user.first_name)
    
    # Welcome message
    welcome_text = (
        f"👋 Hey {user.first_name}!\n\n"
        "🤖 I'm your Manga/Manhwa Downloader Bot!\n\n"
        "📚 *What I can do:*\n"
        "• Search manga/manhwa from multiple sources\n"
        "• Download chapters as PDF\n"
        "• Send you updates when new chapters release\n"
        "• Cache downloads for instant access\n\n"
        "🔍 *Commands:*\n"
        "/manga `[name]` - Search for manga\n"
        "/mysubscriptions - View your subscriptions\n"
        "/stats - View your download statistics\n"
        "/help - Show detailed help\n\n"
        "Try it now: `/manga one piece`"
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown"
    )
    
    logger.info(f"User {user.id} ({user.username}) started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command
    Shows detailed help message with all commands
    """
    help_text = (
        "📖 *Bot Help*\n\n"
        "🔍 *Search & Download:*\n"
        "`/manga [name]` - Search for manga/manhwa\n"
        "Example: `/manga one piece`\n\n"
        "📬 *Subscriptions:*\n"
        "`/mysubscriptions` - View your active subscriptions\n"
        "Subscribe via inline button after searching manga\n\n"
        "ℹ️ *Info:*\n"
        "`/stats` - View your download statistics\n"
        "`/help` - Show this help message\n\n"
        "💡 *Tips:*\n"
        "• Downloaded chapters are cached for 7 days\n"
        "• Use inline buttons to navigate chapters\n"
        "• Subscribe to get notified about new chapters\n"
        "• Cached downloads are instant!\n\n"
        "🌐 *Supported Sources:*\n"
        "• mangak.io\n"
        "• mangahub.io\n\n"
        "❓ Need help? Contact @YourSupportUsername"
    )
    
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown"
    )
    
    logger.debug(f"User {update.effective_user.id} viewed help")

async def manga_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /manga command - search for manga
    Usage: /manga [name]
    """
    # Check if query is provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a manga name!\n\n"
            "Usage: `/manga [name]`\n"
            "Example: `/manga one piece`",
            parse_mode="Markdown"
        )
        return
    
    query = " ".join(context.args)
    
    # Send searching message
    searching_msg = await update.message.reply_text(
        f"🔍 Searching for '*{query}*'\n\n"
        "⏳ Please wait...",
        parse_mode="Markdown"
    )
    
    # Search manga (queued to prevent overload)
    async def search_task():
        return await scraper.search(query)
    
    try:
        results = await task_queue.add_task(search_task)
        
        if not results:
            await searching_msg.edit_text(
                f"❌ No results found for '*{query}*'\n\n"
                "Try:\n"
                "• Different spelling\n"
                "• English name\n"
                "• Shorter search term",
                parse_mode="Markdown"
            )
            return
        
        # Display results with inline buttons
        await _display_search_results(searching_msg, results)
        
        logger.info(f"User {update.effective_user.id} searched for '{query}' - found {len(results)} results")
        
    except Exception as e:
        logger.error(f"Error in manga search: {e}", exc_info=True)
        await searching_msg.edit_text(
            "❌ Error searching manga. Please try again later.\n\n"
            "If the problem persists, contact support."
        )

async def _display_search_results(message, results: list):
    """
    Display search results with inline buttons
    Shows first 5 results with navigation
    """
    # Show first 5 results
    display_results = results[:5]
    
    text = "🔍 *Search Results:*\n\n"
    
    keyboard = []
    for idx, manga in enumerate(display_results, 1):
        # Format title (truncate if too long)
        title = manga['title']
        if len(title) > 40:
            title = title[:37] + "..."
        
        text += f"{idx}. *{title}*\n"
        text += f"   Source: `{manga['source']}`\n\n"
        
        # Create button for each result
        keyboard.append([
            InlineKeyboardButton(
                f"📖 {title}",
                callback_data=f"manga_{manga['source']}_{manga['slug']}"
            )
        ])
    
    # Add note if more results available
    if len(results) > 5:
        text += f"\n_...and {len(results) - 5} more results_\n"
        text += "_Refine your search for better results_"
    
    await message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def my_subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /mysubscriptions command
    Shows all active subscriptions for the user
    """
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Send loading message
    loading_msg = await update.message.reply_text("📬 Loading your subscriptions...")
    
    try:
        subscriptions = await db.get_user_subscriptions(user_id)
        
        if not subscriptions:
            await loading_msg.edit_text(
                f"📭 *No Active Subscriptions*\n\n"
                f"Hey {user_name}! You don't have any active subscriptions yet.\n\n"
                "🔍 Use `/manga [name]` to search and subscribe!\n"
                "Example: `/manga one piece`",
                parse_mode="Markdown"
            )
            return
        
        # Display subscriptions
        text = f"📬 *Your Subscriptions ({len(subscriptions)})*\n\n"
        
        keyboard = []
        for idx, sub in enumerate(subscriptions, 1):
            text += f"{idx}. *{sub['manga_title']}*\n"
            text += f"   Slug: `{sub['manga_slug']}`\n\n"
            
            # Add unsubscribe button
            keyboard.append([
                InlineKeyboardButton(
                    f"🔕 Unsubscribe - {sub['manga_title'][:30]}",
                    callback_data=f"unsubscribe_all_{sub['manga_slug']}"
                )
            ])
        
        text += "\n💡 You'll receive notifications when new chapters are released!"
        
        await loading_msg.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"User {user_id} viewed subscriptions ({len(subscriptions)} active)")
        
    except Exception as e:
        logger.error(f"Error in my_subscriptions: {e}", exc_info=True)
        await loading_msg.edit_text(
            "❌ Error loading subscriptions. Please try again."
        )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /stats command
    Shows user's download statistics
    """
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    try:
        # Get user data from database
        user_data = await db.users_collection.find_one({"user_id": user_id})
        
        if not user_data:
            await update.message.reply_text(
                "❌ No data found. Use /start first!"
            )
            return
        
        # Extract stats
        total_downloads = user_data.get('total_downloads', 0)
        joined_at = user_data.get('joined_at', 'Unknown')
        last_seen = user_data.get('last_seen', 'Unknown')
        
        # Format dates
        if joined_at != 'Unknown':
            joined_at = joined_at.strftime('%d %b %Y')
        if last_seen != 'Unknown':
            last_seen = last_seen.strftime('%d %b %Y, %H:%M')
        
        # Get subscription count
        subscriptions = await db.get_user_subscriptions(user_id)
        sub_count = len(subscriptions)
        
        # Get queue status
        queue_status = task_queue.get_queue_status()
        
        # Format stats message
        stats_text = (
            f"📊 *Your Statistics*\n\n"
            f"👤 *User:* {user_name}\n"
            f"🆔 *ID:* `{user_id}`\n\n"
            f"📥 *Total Downloads:* `{total_downloads}`\n"
            f"📬 *Active Subscriptions:* `{sub_count}`\n\n"
            f"📅 *Joined:* {joined_at}\n"
            f"🕐 *Last Active:* {last_seen}\n\n"
            f"⚡ *System Status:*\n"
            f"   Active Tasks: `{queue_status['active']}/{queue_status['max_concurrent']}`\n"
            f"   Queued Tasks: `{queue_status['queued']}`\n\n"
        )
        
        # Add achievement badges
        if total_downloads >= 100:
            stats_text += "🏆 *Achievement:* Manga Master (100+ downloads)\n"
        elif total_downloads >= 50:
            stats_text += "🥈 *Achievement:* avid Reader (50+ downloads)\n"
        elif total_downloads >= 10:
            stats_text += "🥉 *Achievement:* Bookworm (10+ downloads)\n"
        
        stats_text += "\n💡 Keep downloading to unlock more achievements!"
        
        await update.message.reply_text(
            stats_text,
            parse_mode="Markdown"
        )
        
        logger.debug(f"User {user_id} viewed stats")
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Error loading statistics. Please try again."
        )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /admin command (admin only)
    Shows system statistics and admin controls
    """
    user_id = update.effective_user.id
    
    # Check if user is admin (from environment variable)
    import os
    admin_id = os.getenv("ADMIN_USER_ID")
    
    if not admin_id or str(user_id) != admin_id:
        await update.message.reply_text("❌ Access denied. Admin only.")
        logger.warning(f"Unauthorized admin access attempt by user {user_id}")
        return
    
    try:
        # Get system stats
        total_users = await db.users_collection.count_documents({})
        total_downloads = await db.users_collection.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$total_downloads"}}}
        ]).to_list(1)
        total_downloads = total_downloads[0]['total'] if total_downloads else 0
        
        total_subscriptions = await db.subscriptions_collection.count_documents({"active": True})
        total_cached = await db.cache_collection.count_documents({})
        
        # Queue status
        queue_status = task_queue.get_queue_status()
        
        admin_text = (
            f"🔐 *Admin Panel*\n\n"
            f"👥 *Total Users:* `{total_users}`\n"
            f"📥 *Total Downloads:* `{total_downloads}`\n"
            f"📬 *Active Subscriptions:* `{total_subscriptions}`\n"
            f"💾 *Cached Files:* `{total_cached}`\n\n"
            f"⚡ *Queue Status:*\n"
            f"   Active: `{queue_status['active']}/{queue_status['max_concurrent']}`\n"
            f"   Queued: `{queue_status['queued']}`\n\n"
            f"🕐 *System Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await update.message.reply_text(
            admin_text,
            parse_mode="Markdown"
        )
        
        logger.info(f"Admin {user_id} accessed admin panel")
        
    except Exception as e:
        logger.error(f"Error in admin command: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Error loading admin panel."
        )

# Import datetime for admin command
from datetime import datetime