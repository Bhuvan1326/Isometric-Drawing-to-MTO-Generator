"""File handling: validation, storage, and PDF->image rendering.

Server-side validation is mandatory — never trust the client. We check both
the declared content-type and the file signature (magic bytes), because a
malicious or buggy client can lie about either.
"""

from __future__ import annotations

import io
import shutil
import uuid
from pathlib import Path
from typing import Optional

from app.config import settings


# (extension, mime, magic-bytes prefix)
# Magic bytes are checked against the first bytes of the file content.
_ALLOWED: tuple[tuple[str, str, tuple[int, ...]], ...] = (
    ("png", "image/png", (0x89, 0x50, 0x4E, 0x47)),
    ("jpg", "image/jpeg", (0xFF, 0xD8, 0xFF)),
    ("jpeg", "image/jpeg", (0xFF, 0xD8, 0xFF)),
    ("pdf", "application/pdf", (0x25, 0x50, 0x44, 0x46)),
)

_ALLOWED_MIMES = {m for _, m, _ in _ALLOWED}
_ALLOWED_EXT = {e for e, _, _ in _ALLOWED}


class FileValidationError(ValueError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


class FileService:
    def __init__(self, upload_dir: Optional[Path] = None) -> None:
        self.upload_dir = upload_dir or settings.upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def validate(self, *, filename: str, content_type: str, size: int) -> None:
        """Raise FileValidationError if the file is rejected."""
        if size > settings.max_file_size_bytes:
            raise FileValidationError(
                f"File exceeds {settings.max_file_size_mb}MB limit", "OVERSIZED"
            )
        if size == 0:
            raise FileValidationError("File is empty", "BAD_FILE")

        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in _ALLOWED_EXT:
            raise FileValidationError(
                f"Unsupported file type '.{ext}'. Allowed: png, jpg, jpeg, pdf",
                "BAD_FILE",
            )
        # content_type may include parameters like 'image/png; charset=...'
        ct = content_type.split(";")[0].strip().lower()
        if ct not in _ALLOWED_MIMES:
            raise FileValidationError(
                f"Unsupported content-type '{ct}'", "BAD_FILE"
            )

    def save(self, *, filename: str, content: bytes) -> Path:
        """Persist the uploaded file under a unique name. Returns the path."""
        ext = Path(filename).suffix.lower()
        unique = f"{uuid.uuid4().hex}{ext}"
        path = self.upload_dir / unique
        path.write_bytes(content)
        return path

    def read_image_bytes(self, path: Path) -> tuple[bytes, str]:
        """Return (image_bytes, mime_type) suitable for a vision LLM.

        For PNG/JPG we pass the bytes through. For PDF we render the first
        page to a PNG using pdf2image (which wraps poppler). If poppler isn't
        installed, we fall back to PyMuPDF (fitz) — see requirements.txt.
        """
        ext = path.suffix.lower().lstrip(".")
        if ext in ("png", "jpg", "jpeg"):
            mime = "image/png" if ext == "png" else "image/jpeg"
            return path.read_bytes(), mime
        if ext == "pdf":
            return self._render_pdf_first_page(path), "image/png"
        raise FileValidationError(f"Cannot read image from .{ext}", "BAD_FILE")

    def _render_pdf_first_page(self, path: Path) -> bytes:
        # Prefer pdf2image (poppler) — better quality. Fall back to PyMuPDF.
        try:
            from pdf2image import convert_from_path  # type: ignore

            images = convert_from_path(str(path), dpi=200, first_page=1, last_page=1)
            if not images:
                raise FileValidationError("PDF has no pages", "BAD_FILE")
            buf = io.BytesIO()
            images[0].save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            pass
        try:
            import fitz  # type: ignore  # PyMuPDF

            doc = fitz.open(str(path))
            if doc.page_count == 0:
                raise FileValidationError("PDF has no pages", "BAD_FILE")
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=200)
            return pix.tobytes("png")
        except ImportError:
            raise FileValidationError(
                "No PDF rendering backend available (install pdf2image or PyMuPDF)",
                "BAD_FILE",
            )

    def delete(self, path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def verify_magic_bytes(content: bytes) -> None:
    """Sanity-check the first bytes of the file against known signatures.

    Catches the case where a client sends a .png content-type but the body is
    actually a .exe. We don't reject unknown signatures for PDFs rendered
    server-side, only for uploaded content.
    """
    if not content:
        raise FileValidationError("Empty file", "BAD_FILE")
    head = content[:8]
    for _, _, magic in _ALLOWED:
        if head.startswith(bytes(magic)):
            return
    raise FileValidationError("File signature does not match allowed types", "BAD_FILE")


# Module-level singleton used by routes.
file_service = FileService()
