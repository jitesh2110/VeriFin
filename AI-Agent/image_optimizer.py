"""
VeriFin Image Optimizer & Storage Pipeline
Mitigates storage explosion for thousands of receipts by converting
raw uploads to high-efficiency WebP images and generating thumbnails.
"""

import os
import io
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageOps
import fitz  # PyMuPDF


class ImageOptimizer:
    def __init__(self, base_upload_dir: str = "uploads"):
        self.base_dir = Path(base_upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def optimize_and_store(
        self,
        file_path: Path,
        company_id: str = "comp_default",
        max_dimension: int = 1800,
        webp_quality: int = 82
    ) -> Dict[str, Any]:
        """
        Process receipt image/PDF, optimize to WebP, generate thumbnail,
        and store in tenant-partitioned directory structure.
        """
        original_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        file_ext = file_path.suffix.lower()

        # Step 1: Extract or load PIL Image
        pil_image = None
        page_count = 1

        if file_ext == '.pdf':
            doc = fitz.open(str(file_path))
            page_count = len(doc)
            if page_count > 0:
                first_page = doc.load_page(0)
                # 150 DPI matrix is optimal balance of sharp OCR text and small size
                mat = fitz.Matrix(1.5, 1.5)
                pix = first_page.get_pixmap(matrix=mat, alpha=False)
                pil_image = Image.open(io.BytesIO(pix.tobytes("png")))
            doc.close()
        else:
            pil_image = Image.open(str(file_path))
            # Auto-rotate based on EXIF orientation if present
            pil_image = ImageOps.exif_transpose(pil_image)

        if pil_image is None:
            raise ValueError(f"Could not read image from {file_path}")

        # Convert to RGB (in case of RGBA/P/CMYK)
        if pil_image.mode not in ("RGB", "L"):
            pil_image = pil_image.convert("RGB")

        # Step 2: Resize if larger than max_dimension
        orig_width, orig_height = pil_image.size
        if max(orig_width, orig_height) > max_dimension:
            pil_image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # Step 3: Compute SHA-256 hash of image data for deduplication
        img_buffer = io.BytesIO()
        pil_image.save(img_buffer, format="WEBP", quality=webp_quality, method=6)
        optimized_bytes = img_buffer.getvalue()
        file_hash = hashlib.sha256(optimized_bytes).hexdigest()

        # Step 4: Prepare tenant directory structure uploads/{company_id}/{year}/{month}/
        now = datetime.now()
        clean_company = "".join(c for c in company_id if c.isalnum() or c in ("-", "_"))
        tenant_dir = self.base_dir / clean_company / f"{now.year}" / f"{now.month:02d}"
        tenant_dir.mkdir(parents=True, exist_ok=True)

        optimized_filename = f"{file_hash[:16]}.webp"
        thumbnail_filename = f"{file_hash[:16]}_thumb.webp"

        optimized_path = tenant_dir / optimized_filename
        thumbnail_path = tenant_dir / thumbnail_filename

        # Save optimized WebP image
        with open(optimized_path, "wb") as f:
            f.write(optimized_bytes)

        # Step 5: Generate and save low-bandwidth thumbnail (240px)
        thumb_image = pil_image.copy()
        thumb_image.thumbnail((240, 240), Image.Resampling.LANCZOS)
        thumb_image.save(str(thumbnail_path), format="WEBP", quality=75, method=4)

        optimized_size = len(optimized_bytes)
        thumbnail_size = os.path.getsize(thumbnail_path) if os.path.exists(thumbnail_path) else 0
        savings_percent = round((1 - (optimized_size / max(original_size, 1))) * 100, 1)

        # Relative URLs for frontend serving
        rel_optimized = f"/uploads/{clean_company}/{now.year}/{now.month:02d}/{optimized_filename}"
        rel_thumb = f"/uploads/{clean_company}/{now.year}/{now.month:02d}/{thumbnail_filename}"

        return {
            "file_hash": file_hash,
            "optimized_path": str(optimized_path),
            "thumbnail_path": str(thumbnail_path),
            "image_url": rel_optimized,
            "thumbnail_url": rel_thumb,
            "original_size_bytes": original_size,
            "optimized_size_bytes": optimized_size,
            "thumbnail_size_bytes": thumbnail_size,
            "savings_percent": max(0.0, savings_percent),
            "dimensions": {"width": pil_image.width, "height": pil_image.height},
            "page_count": page_count,
            "format": "WEBP"
        }


# Singleton instance
image_optimizer = ImageOptimizer()
