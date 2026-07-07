"""Pytest config — force mock provider so tests never need an API key."""

import os
import sys
from pathlib import Path

# Make 'app' importable when running from the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force mock mode for the test suite. Tests should never hit the network.
os.environ["VISION_PROVIDER"] = "mock"
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ["UPLOAD_DIR"] = str(Path(__file__).resolve().parent / "_uploads")

import pytest  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
