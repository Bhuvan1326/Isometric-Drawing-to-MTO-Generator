"""Application settings — read from environment, with safe defaults.

The provider is swappable: set VISION_PROVIDER to 'gemini', 'mock', or a new
provider name. Adding a new provider is a one-file change in app/pipeline/.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    # Provider selection. 'mock' is the no-API-key fallback; 'gemini' is the
    # real vision LLM. To add a provider, implement the Pipeline protocol in
    # app/pipeline/ and register it in app/pipeline/__init__.py.
    vision_provider: str
    gemini_api_key: str
    gemini_model: str
    max_file_size_mb: int
    upload_dir: Path
    cors_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("VISION_PROVIDER", "gemini").lower()
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        # If no key is set, force the mock provider so the app still runs.
        if provider == "gemini" and not api_key:
            provider = "mock"
        return cls(
            vision_provider=provider,
            gemini_api_key=api_key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "20")),
            upload_dir=Path(os.getenv("UPLOAD_DIR", "./_uploads")),
            cors_origins=tuple(
                o.strip()
                for o in os.getenv(
                    "CORS_ORIGINS",
                    "http://localhost:3000,http://127.0.0.1:3000",
                ).split(",")
                if o.strip()
            ),
        )

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


settings = Settings.from_env()
