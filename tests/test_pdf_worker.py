"""
Tests for core/pdf_worker.py
"""

import os
from io import BytesIO

import pytest
from PIL import Image

from core.pdf_worker import pdf_worker


def make_test_image() -> bytes:
    """Create a small valid JPEG image in memory."""
    image = Image.new("RGB", (200, 300), color="white")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_create_pdf(monkeypatch):
    """Test PDF creation without depending on an external image host."""
    image_data = make_test_image()

    async def fake_download_image(url, session):
        return image_data

    monkeypatch.setattr(pdf_worker, "download_image", fake_download_image)

    pdf_path = await pdf_worker.create_pdf(
        ["https://example.com/1.jpg", "https://example.com/2.jpg"],
        "test_chapter.pdf",
    )

    assert pdf_path is not None
    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")

    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_compress_image():
    """Test image compression."""
    image_data = make_test_image()
    compressed = pdf_worker.compress_image(image_data)

    assert compressed
    assert compressed != image_data


def test_cleanup_old_files():
    """Test cleanup of old temporary files."""
    test_file = os.path.join(pdf_worker.temp_dir, "test_old_file.tmp")

    with open(test_file, "w", encoding="utf-8") as file:
        file.write("test")

    pdf_worker.cleanup_old_files(max_age_hours=0)

    assert not os.path.exists(test_file)
