"""
Tests for core/scraper.py
"""

import pytest
import asyncio
from core.scraper import scraper

@pytest.mark.asyncio
async def test_search_mangak():
    """Test manga search on mangak.io"""
    results = await scraper.search_mangak("one piece")
    assert isinstance(results, list)
    if results:
        assert 'title' in results[0]
        assert 'slug' in results[0]
        assert 'source' in results[0]
        assert results[0]['source'] == 'mangak'

@pytest.mark.asyncio
async def test_search_mangahub():
    """Test manga search on mangahub.io"""
    results = await scraper.search_mangahub("naruto")
    assert isinstance(results, list)
    if results:
        assert 'title' in results[0]
        assert 'slug' in results[0]
        assert 'source' in results[0]
        assert results[0]['source'] == 'mangahub'

@pytest.mark.asyncio
async def test_get_manga_details_mangak():
    """Test getting manga details from mangak.io"""
    # First search to get a valid slug
    results = await scraper.search_mangak("one piece")
    if results:
        slug = results[0]['slug']
        details = await scraper.get_manga_details_mangak(slug)
        assert details is not None
        assert 'title' in details
        assert 'chapters' in details
        assert 'genres' in details

@pytest.mark.asyncio
async def test_get_chapter_images_mangak():
    """Test getting chapter images from mangak.io"""
    # First search and get details
    results = await scraper.search_mangak("one piece")
    if results:
        slug = results[0]['slug']
        details = await scraper.get_manga_details_mangak(slug)
        if details and details['chapters']:
            chapter_num = details['chapters'][0]['number']
            images = await scraper.get_chapter_images_mangak(slug, chapter_num)
            assert isinstance(images, list)
            if images:
                assert images[0].startswith('http')

@pytest.mark.asyncio
async def test_search_all_sources():
    """Test searching from all sources"""
    results = await scraper.search("dragon ball", source="all")
    assert isinstance(results, list)
    # Should have results from both sources
    sources = set(r['source'] for r in results)
    assert len(sources) >= 1  # At least one source should return results
