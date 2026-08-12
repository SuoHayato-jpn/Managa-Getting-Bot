"""
PDF generation worker.
Handles image downloading, compression, and PDF creation.
"""

import os
import asyncio
from uuid import uuid4
import httpx
import img2pdf
from PIL import Image
from io import BytesIO
from typing import List, Optional, Callable, Awaitable

from config import (
    IMAGE_COMPRESSION_QUALITY,
    MAX_IMAGE_SIZE,
    TEMP_DIR,
    REQUEST_TIMEOUT,
    MAX_FILE_SIZE_MB,
)
from utils.logger import logger


class PDFWorker:
    """PDF generation with memory optimization for Render Free Tier."""

    def __init__(self):
        self.temp_dir = TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info("PDFWorker initialized. Temp dir: %s", self.temp_dir)

    async def download_image(
        self, url: str, session: httpx.AsyncClient
    ) -> Optional[bytes]:
        """Download one image."""
        try:
            response = await session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.content
        except Exception as exc:
            logger.error("Error downloading image %s: %s", url, exc)
            return None

    def compress_image(self, image_data: bytes) -> bytes:
        """Resize/compress an image into JPEG bytes."""
        try:
            with Image.open(BytesIO(image_data)) as source:
                img = source.convert("RGB")

                if img.width > MAX_IMAGE_SIZE[0] or img.height > MAX_IMAGE_SIZE[1]:
                    img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

                output = BytesIO()
                img.save(
                    output,
                    format="JPEG",
                    quality=IMAGE_COMPRESSION_QUALITY,
                    optimize=True,
                )
                return output.getvalue()
        except Exception as exc:
            logger.error("Error compressing image: %s", exc)
            return image_data

    async def create_pdf(
        self,
        image_urls: List[str],
        output_filename: str,
        progress_callback: Optional[Callable[[int], Awaitable[None]]] = None,
    ) -> Optional[str]:
        """
        Download images, compress them, and create a PDF.
        Returns the PDF path or None on failure.
        """
        if not image_urls:
            logger.warning("No image URLs supplied.")
            return None

        # Prevent accidental path traversal through a caller-supplied filename.
        output_filename = os.path.basename(output_filename)
        if not output_filename.lower().endswith(".pdf"):
            output_filename += ".pdf"

        output_path = os.path.join(
            self.temp_dir, f"{uuid4().hex}_{output_filename}"
        )
        temp_images: List[str] = []

        try:
            logger.info("Starting PDF creation: %s", output_filename)

            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
            ) as session:
                total = len(image_urls)

                for idx, url in enumerate(image_urls, 1):
                    image_data = await self.download_image(url, session)
                    if not image_data:
                        logger.warning("Skipping failed download: %s", url)
                        continue

                    compressed_data = self.compress_image(image_data)
                    temp_path = os.path.join(
                        self.temp_dir, f"temp_{uuid4().hex}_{idx}.jpg"
                    )

                    with open(temp_path, "wb") as file:
                        file.write(compressed_data)

                    temp_images.append(temp_path)

                    if progress_callback:
                        progress = int((idx / total) * 100)
                        try:
                            await progress_callback(progress)
                        except Exception:
                            logger.debug("Progress callback failed.", exc_info=True)

                    del image_data
                    del compressed_data
                    await asyncio.sleep(0)

            if not temp_images:
                logger.error("No images downloaded; cannot create PDF.")
                return None

            logger.info("Creating PDF with %d pages", len(temp_images))
            with open(output_path, "wb") as file:
                file.write(img2pdf.convert(temp_images))

            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                logger.error(
                    "PDF too large: %.2f MB (limit: %s MB)",
                    file_size_mb,
                    MAX_FILE_SIZE_MB,
                )
                os.remove(output_path)
                return None

            logger.info(
                "PDF created successfully: %s (%.2f MB)",
                output_path,
                file_size_mb,
            )
            return output_path

        except Exception as exc:
            logger.error("Error creating PDF: %s", exc, exc_info=True)
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            return None

        finally:
            for temp_path in temp_images:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except OSError:
                    logger.warning("Could not remove temp image: %s", temp_path)

    def cleanup_old_files(self, max_age_hours: float = 24) -> int:
        """Delete temporary files older than max_age_hours."""
        import time

        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0

        if not os.path.isdir(self.temp_dir):
            return 0

        for filename in os.listdir(self.temp_dir):
            path = os.path.join(self.temp_dir, filename)
            if not os.path.isfile(path):
                continue
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
                    removed += 1
            except OSError as exc:
                logger.warning("Could not remove old temp file %s: %s", path, exc)

        if removed:
            logger.info("Removed %d old temporary files.", removed)
        return removed


# Global PDF worker instance
pdf_worker = PDFWorker()
