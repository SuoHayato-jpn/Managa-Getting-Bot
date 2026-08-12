"""
MongoDB database operations
Handles user management, file caching, and subscription tracking
"""

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from config import MONGODB_URI, DATABASE_NAME, CACHE_TTL
from utils.logger import logger

class Database:
    """
    MongoDB database manager
    """
    
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        
        # Collections
        self.users_collection = self.db["users"]
        self.cache_collection = self.db["file_cache"]
        self.subscriptions_collection = self.db["subscriptions"]
        self.update_state_collection = self.db["update_state"]
        
        logger.info("Database connection established")
    
    # ============================================
    # USER MANAGEMENT
    # ============================================
    
    async def add_user(self, user_id: int, username: str, first_name: str):
        """
        Add or update user in database
        """
        try:
            await self.users_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "username": username,
                        "first_name": first_name,
                        "last_seen": datetime.now(timezone.utc)
                    },
                    "$setOnInsert": {
                        "user_id": user_id,
                        "joined_at": datetime.now(timezone.utc),
                        "total_downloads": 0
                    }
                },
                upsert=True
            )
            logger.debug(f"User {user_id} added/updated")
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
    
    async def increment_download_count(self, user_id: int):
        """
        Increment user's download counter
        """
        try:
            await self.users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"total_downloads": 1}}
            )
        except Exception as e:
            logger.error(f"Error incrementing download count for {user_id}: {e}")
    
    # ============================================
    # FILE CACHING
    # ============================================
    
    async def get_cached_file(self, manga_slug: str, chapter_number: str) -> Optional[str]:
        """
        Get cached file_id for a chapter
        Returns None if not found or expired
        """
        try:
            cache_key = f"{manga_slug}_{chapter_number}"
            result = await self.cache_collection.find_one(
                {"cache_key": cache_key}
            )
            
            if result:
                # Check if cache is expired. Normalize legacy naive datetimes.
                created_at = result.get("created_at")
                if created_at is None:
                    await self.cache_collection.delete_one({"cache_key": cache_key})
                    return None
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)

                if created_at + timedelta(seconds=CACHE_TTL) > datetime.now(timezone.utc):
                    logger.debug(f"Cache hit for {cache_key}")
                    return result["file_id"]
                else:
                    # Cache expired, delete it
                    await self.cache_collection.delete_one({"cache_key": cache_key})
                    logger.debug(f"Cache expired for {cache_key}")
            
            return None
        except Exception as e:
            logger.error(f"Error getting cached file: {e}")
            return None
    
    async def cache_file(self, manga_slug: str, chapter_number: str, file_id: str, file_size: int):
        """
        Cache a file_id for future use
        """
        try:
            cache_key = f"{manga_slug}_{chapter_number}"
            await self.cache_collection.update_one(
                {"cache_key": cache_key},
                {
                    "$set": {
                        "cache_key": cache_key,
                        "file_id": file_id,
                        "file_size": file_size,
                        "created_at": datetime.now(timezone.utc),
                        "manga_slug": manga_slug,
                        "chapter_number": chapter_number
                    }
                },
                upsert=True
            )
            logger.info(f"Cached file for {cache_key}")
        except Exception as e:
            logger.error(f"Error caching file: {e}")
    
    # ============================================
    # SUBSCRIPTION MANAGEMENT
    # ============================================
    
    async def subscribe_user(self, user_id: int, manga_slug: str, manga_title: str, source: str = "mangak"):
        """
        Subscribe user to manga updates
        """
        try:
            await self.subscriptions_collection.update_one(
                {"user_id": user_id, "manga_slug": manga_slug},
                {
                    "$set": {
                        "user_id": user_id,
                        "manga_slug": manga_slug,
                        "manga_title": manga_title,
                        "source": source,
                        "subscribed_at": datetime.now(timezone.utc),
                        "active": True
                    }
                },
                upsert=True
            )
            logger.info(f"User {user_id} subscribed to {manga_slug}")
        except Exception as e:
            logger.error(f"Error subscribing user: {e}")
    
    async def unsubscribe_user(self, user_id: int, manga_slug: str):
        """
        Unsubscribe user from manga updates
        """
        try:
            await self.subscriptions_collection.update_one(
                {"user_id": user_id, "manga_slug": manga_slug},
                {"$set": {"active": False}}
            )
            logger.info(f"User {user_id} unsubscribed from {manga_slug}")
        except Exception as e:
            logger.error(f"Error unsubscribing user: {e}")
    
    async def get_subscribers(self, manga_slug: str) -> List[int]:
        """
        Get all active subscribers for a manga
        """
        try:
            cursor = self.subscriptions_collection.find(
                {"manga_slug": manga_slug, "active": True}
            )
            subscribers = [doc["user_id"] async for doc in cursor]
            return subscribers
        except Exception as e:
            logger.error(f"Error getting subscribers: {e}")
            return []
    
    async def get_user_subscriptions(self, user_id: int) -> List[Dict]:
        """
        Get all subscriptions for a user
        """
        try:
            cursor = self.subscriptions_collection.find(
                {"user_id": user_id, "active": True}
            )
            subscriptions = [
                {
                    "manga_slug": doc["manga_slug"],
                    "manga_title": doc["manga_title"]
                }
                async for doc in cursor
            ]
            return subscriptions
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {e}")
            return []
    
    # ============================================
    # CLEANUP
    # ============================================
    
    async def cleanup_expired_cache(self):
        """
        Remove expired cache entries
        """
        try:
            expiry_time = datetime.now(timezone.utc) - timedelta(seconds=CACHE_TTL)
            result = await self.cache_collection.delete_many(
                {"created_at": {"$lt": expiry_time}}
            )
            logger.info(f"Cleaned up {result.deleted_count} expired cache entries")
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")

# Global database instance
db = Database()