"""Pipeline protocol — the contract every provider implements.

Keeping this a runtime-checkable Protocol (not an ABC) means providers don't
need to inherit from anything; they just need to match the shape. That makes
adding a one-file provider even cleaner.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from app.models.mto import MTO


class PipelineError(Exception):
    """Base class for pipeline failures. Carries a stable error code."""

    def __init__(self, message: str, code: str = "LLM_FAILURE") -> None:
        super().__init__(message)
        self.code = code


class PipelineTimeoutError(PipelineError):
    def __init__(self, message: str = "Vision LLM timed out") -> None:
        super().__init__(message, code="LLM_TIMEOUT")


@runtime_checkable
class Pipeline(Protocol):
    @property
    def name(self) -> str: ...

    def extract(self, image_path: Path, *, filename: str) -> MTO: ...
