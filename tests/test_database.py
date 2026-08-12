"""
Tests for data/database.py
"""

import pytest
from datetime import datetime, timezone
from data.database import db

@pytest.mark.asyncio
async def test_add_user():
    """Test adding a user to database"""
    test_user_id = 999999999
    await db.add_user(test_user_id, "testuser", "Test")
    
    # Verify user was added
    user = await db.users_collection.find_one({"user_id": test_user_id})
    assert user is not None
    assert user['username'] == "testuser"
    
    # Clean up
    await db.users_collection.delete_one({"user_id": test_user_id})

@pytest.mark.asyncio
async def test_file_caching():
    """Test file caching functionality"""
    test_slug = "test-manga"
    test_chapter = "1"
    test_file_id = "test_file_id_12345"
    test_file_size = 1024000
    
    # Cache file
    await db.cache_file(test_slug, test_chapter, test_file_id, test_file_size)
    
    # Retrieve cached file
    cached = await db.get_cached_file(test_slug, test_chapter)
    assert cached == test_file_id
    
    # Clean up
    await db.cache_collection.delete_one({
        "cache_key": f"{test_slug}_{test_chapter}"
    })

@pytest.mark.asyncio
async def test_subscription_management():
    """Test subscription add/remove"""
    test_user_id = 999999999
    test_slug = "test-manga"
    test_title = "Test Manga"
    
    # Subscribe
    await db.subscribe_user(test_user_id, test_slug, test_title)
    
    # Get subscribers
    subscribers = await db.get_subscribers(test_slug)
    assert test_user_id in subscribers
    
    # Get user subscriptions
    user_subs = await db.get_user_subscriptions(test_user_id)
    assert any(sub['manga_slug'] == test_slug for sub in user_subs)
    
    # Unsubscribe
    await db.unsubscribe_user(test_user_id, test_slug)
    
    # Verify unsubscribed
    subscribers = await db.get_subscribers(test_slug)
    assert test_user_id not in subscribers
    
    # Clean up
    await db.subscriptions_collection.delete_many({
        "user_id": test_user_id,
        "manga_slug": test_slug
    })

@pytest.mark.asyncio
async def test_increment_download_count():
    """Test download count increment"""
    test_user_id = 999999999
    
    # Add user first
    await db.add_user(test_user_id, "testuser", "Test")
    
    # Get initial count
    user = await db.users_collection.find_one({"user_id": test_user_id})
    initial_count = user.get('total_downloads', 0)
    
    # Increment
    await db.increment_download_count(test_user_id)
    
    # Verify
    user = await db.users_collection.find_one({"user_id": test_user_id})
    assert user['total_downloads'] == initial_count + 1
    
    # Clean up
    await db.users_collection.delete_one({"user_id": test_user_id})

@pytest.mark.asyncio
async def test_cleanup_expired_cache():
    """Test cleanup of expired cache entries"""
    # Add an expired cache entry
    test_slug = "expired-manga"
    test_chapter = "1"
    
    await db.cache_collection.insert_one({
        "cache_key": f"{test_slug}_{test_chapter}",
        "file_id": "test_id",
        "file_size": 1000,
        "created_at": datetime(2020, 1, 1, tzinfo=timezone.utc),  # Very old date
        "manga_slug": test_slug,
        "chapter_number": test_chapter
    })
    
    # Run cleanup
    await db.cleanup_expired_cache()
    
    # Verify it was deleted
    cached = await db.cache_collection.find_one({
        "cache_key": f"{test_slug}_{test_chapter}"
    })
    assert cached is None