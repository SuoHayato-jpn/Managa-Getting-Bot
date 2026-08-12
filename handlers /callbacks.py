"""
Callback query handlers for inline buttons
Handles manga details, chapter downloads, navigation, and subscriptions
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.scraper import scraper
from core.pdf_worker import pdf_worker
from data.database import db
from utils.queue_manager import task_queue
from utils.logger import logger
import os

async def manga_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle manga details button click
    Shows manga info with chapters list and subscribe button
    """
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: manga_{source}_{slug}
    _, source, slug = query.data.split("_", 2)
    
    # Show loading message
    await query.edit_message_text("📖 Loading manga details...")
    
    # Get manga details (queued)
    async def fetch_details():
        return await scraper.get_manga_details(slug, source)
    
    try:
        manga = await task_queue.add_task(fetch_details)
        
        if not manga:
            await query.edit_message_text("❌ Error loading manga details. Please try again.")
            return
        
        # Format manga info
        text = f"📚 *{manga['title']}*\n\n"
        text += f"📖 Status: {manga['status']}\n"
        text += f"🏷 Genres: {', '.join(manga['genres'][:5])}\n"
        text += f"📄 Chapters: {len(manga['chapters'])}\n\n"
        text += f"📝 {manga['description'][:300]}...\n"
        
        if not manga.get("chapters"):
            await query.edit_message_text(
                text + "\n\n❌ No chapters are currently available."
            )
            return

        # Create buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    "📋 Chapters List",
                    callback_data=f"chapters_{source}_{slug}"
                )
            ],
            [
                InlineKeyboardButton(
                    "⬇️ Download Latest",
                    callback_data=f"download_{source}_{slug}_{manga['chapters'][0]['number']}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔔 Subscribe for Updates",
                    callback_data=f"subscribe_{source}_{slug}"
                )
            ]
        ]
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in manga_details_callback: {e}")
        await query.edit_message_text("❌ Error loading manga. Please try again.")

async def chapters_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle chapters list button click
    Shows list of chapters with download buttons
    """
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: chapters_{source}_{slug}
    _, source, slug = query.data.split("_", 2)
    
    await query.edit_message_text("📋 Loading chapters...")
    
    # Get manga details
    async def fetch_details():
        return await scraper.get_manga_details(slug, source)
    
    try:
        manga = await task_queue.add_task(fetch_details)
        
        if not manga:
            await query.edit_message_text("❌ Error loading chapters. Please try again.")
            return
        
        # Show first 10 chapters
        chapters = manga['chapters'][:10]
        
        text = f"📋 *Chapters - {manga['title']}*\n\n"
        
        keyboard = []
        for ch in chapters:
            keyboard.append([
                InlineKeyboardButton(
                    f"📄 Chapter {ch['number']}",
                    callback_data=f"download_{source}_{slug}_{ch['number']}"
                )
            ])
        
        if len(manga['chapters']) > 10:
            text += f"_Showing first 10 of {len(manga['chapters'])} chapters_\n"
        
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in chapters_list_callback: {e}")
        await query.edit_message_text("❌ Error loading chapters. Please try again.")

async def download_chapter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle chapter download button click
    Downloads chapter, creates PDF, and sends to user
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Parse callback data: download_{source}_{slug}_{chapter_number}
    parts = query.data.split("_", 3)
    source = parts[1]
    slug = parts[2]
    chapter_number = parts[3]
    
    # Check cache first
    cached_file_id = await db.get_cached_file(slug, chapter_number)
    
    if cached_file_id:
        # Send cached file instantly
        await query.answer("✅ Sending from cache...")
        await query.message.reply_text(f"📄 Chapter {chapter_number} (Cached)")
        
        try:
            await context.bot.send_document(
                chat_id=user_id,
                document=cached_file_id,
                caption=f"📚 Chapter {chapter_number}\n\n@YourBotUsername"
            )
            await db.increment_download_count(user_id)
        except Exception as e:
            logger.error(f"Error sending cached file: {e}")
            await query.message.reply_text("❌ Error sending file. Please try again.")
        return
    
    # Not cached, need to download
    await query.answer("⏳ Downloading chapter...")
    
    # Send progress message
    progress_msg = await query.message.reply_text(
        f"⏳ Downloading Chapter {chapter_number}...\n\n"
        "Progress: 0%"
    )
    
    # Define progress callback
    async def update_progress(progress):
        try:
            await progress_msg.edit_text(
                f"⏳ Downloading Chapter {chapter_number}...\n\n"
                f"Progress: {progress}%"
            )
        except Exception:
            pass  # Ignore if message can't be edited
    
    # Download and create PDF (queued)
    async def download_task():
        # Get chapter images
        image_urls = await scraper.get_chapter_images(slug, chapter_number, source)
        
        if not image_urls:
            return None, None
        
        # Create PDF
        filename = f"{slug}_ch{chapter_number}.pdf"
        pdf_path = await pdf_worker.create_pdf(
            image_urls,
            filename,
            progress_callback=update_progress
        )
        
        return pdf_path, filename
    
    try:
        pdf_path, filename = await task_queue.add_task(download_task)
        
        if not pdf_path:
            await progress_msg.edit_text("❌ Error downloading chapter. Please try again.")
            return
        
        # Send PDF
        await progress_msg.edit_text("📤 Uploading PDF...")
        
        with open(pdf_path, 'rb') as pdf_file:
            sent_msg = await context.bot.send_document(
                chat_id=user_id,
                document=pdf_file,
                caption=f"📚 Chapter {chapter_number}\n\n@YourBotUsername",
                filename=filename
            )
        
        # Cache the file_id
        file_size = os.path.getsize(pdf_path)
        await db.cache_file(slug, chapter_number, sent_msg.document.file_id, file_size)
        await db.increment_download_count(user_id)
        
        # Delete temp file
        os.remove(pdf_path)
        
        # Show navigation buttons
        keyboard = [
            [
                InlineKeyboardButton(
                    "⬅️ Previous",
                    callback_data=f"navigate_{source}_{slug}_{chapter_number}_prev"
                ),
                InlineKeyboardButton(
                    "Next ➡️",
                    callback_data=f"navigate_{source}_{slug}_{chapter_number}_next"
                )
            ]
        ]
        
        await progress_msg.edit_text(
            f"✅ Chapter {chapter_number} downloaded!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error in download_chapter_callback: {e}")
        await progress_msg.edit_text("❌ Error downloading chapter. Please try again.")

async def navigate_chapter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle chapter navigation (previous/next)
    """
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: navigate_{source}_{slug}_{chapter_number}_{direction}
    parts = query.data.split("_", 4)
    source = parts[1]
    slug = parts[2]
    current_chapter = parts[3]
    direction = parts[4]
    
    # Get manga details to find adjacent chapters
    async def fetch_details():
        return await scraper.get_manga_details(slug, source)
    
    try:
        manga = await task_queue.add_task(fetch_details)
        
        if not manga:
            await query.message.reply_text("❌ Error navigating. Please try again.")
            return
        
        # Find current chapter index
        chapters = manga['chapters']
        current_idx = next((i for i, ch in enumerate(chapters) if ch['number'] == current_chapter), None)
        
        if current_idx is None:
            await query.message.reply_text("❌ Chapter not found.")
            return
        
        # Get adjacent chapter
        if direction == "prev" and current_idx > 0:
            prev_chapter = chapters[current_idx - 1]
            await query.message.reply_text(
                f"⬅️ Loading Chapter {prev_chapter['number']}..."
            )
            # Trigger download for previous chapter
            context.user_data['pending_download'] = f"download_{source}_{slug}_{prev_chapter['number']}"
        elif direction == "next" and current_idx < len(chapters) - 1:
            next_chapter = chapters[current_idx + 1]
            await query.message.reply_text(
                f"➡️ Loading Chapter {next_chapter['number']}..."
            )
            # Trigger download for next chapter
            context.user_data['pending_download'] = f"download_{source}_{slug}_{next_chapter['number']}"
        else:
            await query.message.reply_text(
                "❌ No more chapters in that direction."
            )
        
    except Exception as e:
        logger.error(f"Error in navigate_chapter_callback: {e}")
        await query.message.reply_text("❌ Error navigating. Please try again.")

async def subscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle subscribe button click
    Subscribes user to manga updates
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Parse callback data: subscribe_{source}_{slug}
    _, source, slug = query.data.split("_", 2)
    
    # Get manga title
    async def fetch_details():
        return await scraper.get_manga_details(slug, source)
    
    try:
        manga = await task_queue.add_task(fetch_details)
        
        if not manga:
            await query.answer("❌ Error subscribing. Please try again.")
            return
        
        # Subscribe user
        await db.subscribe_user(user_id, slug, manga['title'], source)
        
        await query.answer("✅ Subscribed successfully!")
        await query.message.reply_text(
            f"🔔 You're now subscribed to *{manga['title']}*\n\n"
            "You'll receive notifications when new chapters are released!",
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in subscribe_callback: {e}")
        await query.answer("❌ Error subscribing. Please try again.")

async def unsubscribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle unsubscribe button click
    Unsubscribes user from manga updates
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    # Parse callback data: unsubscribe_{source}_{slug}
    _, source, slug = query.data.split("_", 2)
    
    try:
        await db.unsubscribe_user(user_id, slug)
        
        await query.answer("✅ Unsubscribed successfully!")
        await query.message.reply_text(
            "🔕 You've been unsubscribed from this manga."
        )
        
    except Exception as e:
        logger.error(f"Error in unsubscribe_callback: {e}")
        await query.answer("❌ Error unsubscribing. Please try again.")
