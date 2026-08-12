"""
Web scraper for manga sites
Supports mangak.io and mangahub.io
"""

import httpx
import random
import asyncio
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from config import USER_AGENTS, REQUEST_TIMEOUT
from utils.logger import logger

class MangaScraper:
    """
    Async manga scraper with HTTP/2 support and rotating User-Agents
    """
    
    def __init__(self):
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    def _get_random_headers(self) -> Dict[str, str]:
        """
        Get headers with random User-Agent
        """
        headers = self.headers.copy()
        headers["User-Agent"] = random.choice(USER_AGENTS)
        return headers
    
    async def _make_request(self, url: str) -> Optional[str]:
        """
        Make HTTP/2 request with retry logic
        """
        try:
            async with httpx.AsyncClient(
                http2=True,
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True
            ) as client:
                response = await client.get(url, headers=self._get_random_headers())
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    # ============================================
    # MANGAK.IO SCRAPER
    # ============================================
    
    async def search_mangak(self, query: str) -> List[Dict]:
        """
        Search manga on mangak.io
        """
        try:
            search_url = f"https://mangak.io/search?keyword={quote_plus(query)}"
            html = await self._make_request(search_url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, "html.parser")
            results = []
            
            # Find manga cards
            manga_cards = soup.find_all("div", class_="manga-item")
            
            for card in manga_cards[:10]:  # Limit to 10 results
                try:
                    title_elem = card.find("h3", class_="manga-title")
                    if not title_elem:
                        continue
                    
                    title = title_elem.text.strip()
                    link_elem = title_elem.find("a")
                    if not link_elem or not link_elem.get("href"):
                        continue
                    link = link_elem["href"]
                    slug = link.rstrip("/").split("/")[-1]
                    
                    # Get cover image
                    cover_elem = card.find("img")
                    cover_url = urljoin("https://mangak.io/", cover_elem.get("data-src") or cover_elem.get("src")) if cover_elem else None
                    
                    results.append({
                        "title": title,
                        "slug": slug,
                        "url": urljoin("https://mangak.io/", link),
                        "cover_url": cover_url,
                        "source": "mangak"
                    })
                except Exception as e:
                    logger.error(f"Error parsing manga card: {e}")
                    continue
            
            logger.info(f"Found {len(results)} results on mangak.io for '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching mangak.io: {e}")
            return []
    
    async def get_manga_details_mangak(self, slug: str) -> Optional[Dict]:
        """
        Get detailed information about a manga from mangak.io
        """
        try:
            url = f"https://mangak.io/manga/{slug}"
            html = await self._make_request(url)
            
            if not html:
                return None
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract details
            title_elem = soup.find("h1", class_="manga-title") or soup.find("h1")
            if not title_elem:
                return None
            title = title_elem.get_text(" ", strip=True)
            
            # Cover image
            cover_elem = soup.find("img", class_="manga-cover")
            cover_url = urljoin("https://mangak.io/", cover_elem.get("data-src") or cover_elem.get("src")) if cover_elem else None
            
            # Description
            desc_elem = soup.find("div", class_="manga-description")
            description = desc_elem.text.strip() if desc_elem else "No description available"
            
            # Genre
            genre_elems = soup.find_all("a", class_="genre-tag")
            genres = [g.text.strip() for g in genre_elems]
            
            # Status
            status_elem = soup.find("span", class_="status")
            status = status_elem.text.strip() if status_elem else "Unknown"
            
            # Chapters
            chapter_elems = soup.find_all("div", class_="chapter-item")
            chapters = []
            for ch in chapter_elems:
                try:
                    ch_title = ch.find("a").text.strip()
                    ch_link_elem = ch.find("a")
                    if not ch_link_elem or not ch_link_elem.get("href"):
                        continue
                    ch_link = ch_link_elem["href"]
                    ch_number = ch_link.rstrip("/").split("/")[-1]
                    chapters.append({
                        "number": ch_number,
                        "title": ch_title,
                        "url": urljoin("https://mangak.io/", ch_link)
                    })
                except Exception as e:
                    logger.error(f"Error parsing chapter: {e}")
                    continue
            
            return {
                "title": title,
                "slug": slug,
                "cover_url": cover_url,
                "description": description,
                "genres": genres,
                "status": status,
                "chapters": chapters,
                "source": "mangak"
            }
            
        except Exception as e:
            logger.error(f"Error getting manga details from mangak.io: {e}")
            return None
    
    async def get_chapter_images_mangak(self, manga_slug: str, chapter_number: str) -> List[str]:
        """
        Get all image URLs for a chapter from mangak.io
        """
        try:
            url = f"https://mangak.io/manga/{manga_slug}/{chapter_number}"
            html = await self._make_request(url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all chapter images
            image_elems = soup.find_all("img", class_="chapter-image")
            image_urls = []
            
            for img in image_elems:
                src = img.get("data-src") or img.get("src")
                if src:
                    image_urls.append(urljoin("https://mangak.io/", src))
            
            logger.info(f"Found {len(image_urls)} images for chapter {chapter_number}")
            return image_urls
            
        except Exception as e:
            logger.error(f"Error getting chapter images: {e}")
            return []
    
    # ============================================
    # MANGAHUB.IO SCRAPER
    # ============================================
    
    async def search_mangahub(self, query: str) -> List[Dict]:
        """
        Search manga on mangahub.io
        """
        try:
            search_url = f"https://mangahub.io/search?q={quote_plus(query)}"
            html = await self._make_request(search_url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, "html.parser")
            results = []
            
            # Find manga items
            manga_items = soup.find_all("div", class_="manga-item")
            
            for item in manga_items[:10]:
                try:
                    title_elem = item.find("h3")
                    if not title_elem:
                        continue
                    
                    title = title_elem.text.strip()
                    link_elem = title_elem.find("a")
                    if not link_elem or not link_elem.get("href"):
                        continue
                    link = link_elem["href"]
                    parts = [part for part in link.rstrip("/").split("/") if part]
                    slug = parts[-1] if parts else ""
                    if not slug:
                        continue  # mangahub uses /manga/slug/ format
                    
                    # Cover image
                    cover_elem = item.find("img")
                    cover_url = urljoin("https://mangahub.io/", cover_elem.get("data-src") or cover_elem.get("src")) if cover_elem else None
                    
                    results.append({
                        "title": title,
                        "slug": slug,
                        "url": urljoin("https://mangahub.io/", link),
                        "cover_url": cover_url,
                        "source": "mangahub"
                    })
                except Exception as e:
                    logger.error(f"Error parsing manga item: {e}")
                    continue
            
            logger.info(f"Found {len(results)} results on mangahub.io for '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching mangahub.io: {e}")
            return []
    
    async def get_manga_details_mangahub(self, slug: str) -> Optional[Dict]:
        """
        Get detailed information about a manga from mangahub.io
        """
        try:
            url = f"https://mangahub.io/manga/{slug}"
            html = await self._make_request(url)
            
            if not html:
                return None
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract details
            title_elem = soup.find("h1")
            if not title_elem:
                return None
            title = title_elem.get_text(" ", strip=True)
            
            # Cover image
            cover_elem = soup.find("img", class_="manga-cover")
            cover_url = cover_elem["src"] if cover_elem else None
            
            # Description
            desc_elem = soup.find("div", class_="summary")
            description = desc_elem.text.strip() if desc_elem else "No description available"
            
            # Genre
            genre_elems = soup.find_all("a", class_="genre")
            genres = [g.text.strip() for g in genre_elems]
            
            # Status
            status_elem = soup.find("span", class_="status")
            status = status_elem.text.strip() if status_elem else "Unknown"
            
            # Chapters
            chapter_elems = soup.find_all("li", class_="chapter-item")
            chapters = []
            for ch in chapter_elems:
                try:
                    ch_link_elem = ch.find("a")
                    if not ch_link_elem or not ch_link_elem.get("href"):
                        continue
                    ch_link = ch_link_elem["href"]
                    ch_title = ch_link_elem.get_text(" ", strip=True)
                    ch_number = ch_link.rstrip("/").split("/")[-1]
                    chapters.append({
                        "number": ch_number,
                        "title": ch_title,
                        "url": urljoin("https://mangahub.io/", ch_link)
                    })
                except Exception as e:
                    logger.error(f"Error parsing chapter: {e}")
                    continue
            
            return {
                "title": title,
                "slug": slug,
                "cover_url": cover_url,
                "description": description,
                "genres": genres,
                "status": status,
                "chapters": chapters,
                "source": "mangahub"
            }
            
        except Exception as e:
            logger.error(f"Error getting manga details from mangahub.io: {e}")
            return None
    
    async def get_chapter_images_mangahub(self, manga_slug: str, chapter_number: str) -> List[str]:
        """
        Get all image URLs for a chapter from mangahub.io
        """
        try:
            url = f"https://mangahub.io/manga/{manga_slug}/{chapter_number}"
            html = await self._make_request(url)
            
            if not html:
                return []
            
            soup = BeautifulSoup(html, "html.parser")
            
            # Find all chapter images
            image_elems = soup.find_all("img", class_="chapter-image")
            image_urls = []
            
            for img in image_elems:
                src = img.get("data-src") or img.get("src")
                if src:
                    image_urls.append(urljoin("https://mangahub.io/", src))
            
            logger.info(f"Found {len(image_urls)} images for chapter {chapter_number}")
            return image_urls
            
        except Exception as e:
            logger.error(f"Error getting chapter images: {e}")
            return []
    
    # ============================================
    # UNIFIED INTERFACE
    # ============================================
    
    async def search(self, query: str, source: str = "all") -> List[Dict]:
        """
        Search manga from specified source or all sources
        """
        if source == "mangak":
            return await self.search_mangak(query)
        elif source == "mangahub":
            return await self.search_mangahub(query)
        else:
            # Search both sources concurrently
            mangak_results, mangahub_results = await asyncio.gather(
                self.search_mangak(query),
                self.search_mangahub(query)
            )
            return mangak_results + mangahub_results
    
    async def get_manga_details(self, slug: str, source: str) -> Optional[Dict]:
        """
        Get manga details from specified source
        """
        if source == "mangak":
            return await self.get_manga_details_mangak(slug)
        elif source == "mangahub":
            return await self.get_manga_details_mangahub(slug)
        return None
    
    async def get_chapter_images(self, manga_slug: str, chapter_number: str, source: str) -> List[str]:
        """
        Get chapter images from specified source
        """
        if source == "mangak":
            return await self.get_chapter_images_mangak(manga_slug, chapter_number)
        elif source == "mangahub":
            return await self.get_chapter_images_mangahub(manga_slug, chapter_number)
        return []

# Global scraper instance
scraper = MangaScraper()