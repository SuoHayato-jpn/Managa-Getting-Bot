"""
Scheduler for checking new chapter updates.
Runs periodically and notifies subscribers when a new chapter is detected.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import UPDATE_CHECK_INTERVAL
from core.scraper import scraper
from data.database import db
from utils.logger import logger


scheduler = AsyncIOScheduler()
_application = None


def set_application(application):
    """Store the running Telegram application for scheduled notifications."""
    global _application
    _application = application


async def check_for_updates():
    """Check subscribed manga and notify users only when a new chapter is detected."""
    logger.info("Starting update check...")

    if _application is None:
        logger.warning("Update check skipped: Telegram application is not set.")
        return

    try:
        subscriptions = await db.subscriptions_collection.distinct(
            "manga_slug", {"active": True}
        )

        for slug in subscriptions:
            try:
                sub = await db.subscriptions_collection.find_one(
                    {"manga_slug": slug, "active": True}
                )
                if not sub:
                    continue

                source = sub.get("source", "mangak")
                manga = await scraper.get_manga_details(slug, source)

                if not manga or not manga.get("chapters"):
                    continue

                latest_chapter = str(manga["chapters"][0]["number"])
                state_key = f"{source}:{slug}"

                state = await db.update_state_collection.find_one(
                    {"state_key": state_key}
                )
                previous_chapter = str(state["latest_chapter"]) if state else None

                # First check establishes a baseline and does not spam subscribers.
                if previous_chapter is None:
                    await db.update_state_collection.update_one(
                        {"state_key": state_key},
                        {
                            "$set": {
                                "state_key": state_key,
                                "source": source,
                                "manga_slug": slug,
                                "latest_chapter": latest_chapter,
                            }
                        },
                        upsert=True,
                    )
                    continue

                if previous_chapter == latest_chapter:
                    continue

                await db.update_state_collection.update_one(
                    {"state_key": state_key},
                    {"$set": {"latest_chapter": latest_chapter}},
                    upsert=True,
                )

                subscribers = await db.get_subscribers(slug)
                if not subscribers:
                    continue

                notification_text = (
                    "🆕 *New Chapter Alert!*\n\n"
                    f"📚 {manga['title']}\n"
                    f"📄 Chapter {latest_chapter} is now available!\n\n"
                    f"Use /manga {manga['title']} to download."
                )

                for user_id in subscribers:
                    try:
                        await _application.bot.send_message(
                            chat_id=user_id,
                            text=notification_text,
                            parse_mode="Markdown",
                        )
                    except Exception as exc:
                        logger.error(
                            "Error notifying user %s: %s", user_id, exc
                        )

                logger.info(
                    "Notified %d subscribers about %s chapter %s",
                    len(subscribers),
                    slug,
                    latest_chapter,
                )

            except Exception as exc:
                logger.error("Error checking updates for %s: %s", slug, exc)

    except Exception as exc:
        logger.error("Error in update check: %s", exc, exc_info=True)


def start_scheduler(application):
    """Start the update checker scheduler."""
    set_application(application)
    scheduler.add_job(
        check_for_updates,
        "interval",
        minutes=UPDATE_CHECK_INTERVAL,
        id="update_checker",
        name="Check for new manga chapters",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started (interval: %s minutes)",
        UPDATE_CHECK_INTERVAL,
    )


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
