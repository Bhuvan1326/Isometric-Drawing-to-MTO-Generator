"""Gemini vision pipeline.

Uses Google's `google-genai` SDK (the unified SDK for Gemini) with structured
JSON output constrained by our JSON schema. We pass the schema as
response_schema, which forces the model to emit valid JSON matching it — we
never hand-parse free text.

The prompt and schema live in app/pipeline/prompts/ as standalone files so
they can be reviewed and versioned independently of the code.

Timeout: the SDK doesn't expose a clean per-request timeout, so we wrap the
call in a thread with a deadline. On timeout we raise PipelineTimeoutError,
which the route layer maps to a typed 504.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.config import settings
from app.models.mto import MTO
from app.pipeline.base import Pipeline, PipelineError, PipelineTimeoutError
from app.pipeline.validate import parse_and_validate


_PROMPT_PATH = Path(__file__).parent / "prompts" / "extraction_prompt.txt"
_SCHEMA_PATH = Path(__file__).parent / "prompts" / "mto_schema.json"

# 60s is generous for a single image. Gemini Flash usually returns in 5-15s.
_LLM_TIMEOUT_S = 60.0


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


class _LLMResult:
    """Holder for the worker thread's outcome — value or exception."""

    def __init__(self) -> None:
        self.value: Any = None
        self.error: BaseException | None = None


class GeminiPipeline:
    @property
    def name(self) -> str:
        return "gemini"

    def extract(self, image_path: Path, *, filename: str) -> MTO:
        if not settings.gemini_api_key:
            # Should never happen — config.py forces mock when no key — but
            # guard anyway so a misconfiguration doesn't crash silently.
            raise PipelineError(
                "GEMINI_API_KEY not set but Gemini pipeline selected",
                code="INTERNAL",
            )

        image_bytes, mime = _read_image(image_path)
        raw = self._call_gemini(image_bytes, mime)
        return parse_and_validate(raw, source="gemini")

    def _call_gemini(self, image_bytes: bytes, mime: str) -> dict[str, Any]:
        """Call the Gemini API with a hard timeout. Returns parsed JSON."""
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore

        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = _load_prompt()
        schema = _load_schema()

        # The SDK accepts a list of parts: text + inline image.
        parts = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime),
            prompt,
        ]

        result = _LLMResult()

        def _worker() -> None:
            try:
                response = client.models.generate_content(
                    model=settings.gemini_model,
                    contents=parts,
                    config=types.GenerateContentConfig(
                        # Constrained generation: the model must emit JSON
                        # matching our schema. This is the structured-output
                        # mode — we never hand-parse free text.
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.1,  # low temp for extraction
                        max_output_tokens=8192,
                    ),
                )
                # response.text raises if the model refused; we want the raw
                # text so we can surface a useful error.
                text = getattr(response, "text", None)
                if not text:
                    # Check for blocked / refusal feedback.
                    feedback = getattr(response, "prompt_feedback", None)
                    block_reason = getattr(feedback, "block_reason", None) if feedback else None
                    raise PipelineError(
                        f"Gemini returned no content (block_reason={block_reason})",
                        code="LLM_FAILURE",
                    )
                result.value = json.loads(text)
            except PipelineError as e:
                result.error = e
            except Exception as e:  # noqa: BLE001 — surface any SDK failure
                result.error = PipelineError(
                    f"Gemini API call failed: {e}", code="LLM_FAILURE"
                )

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(_LLM_TIMEOUT_S)
        if t.is_alive():
            # Thread is still running — we can't kill it cleanly in Python,
            # but it's daemon so it won't block process exit. We raise and
            # let the route layer return 504.
            raise PipelineTimeoutError(
                f"Gemini did not respond within {_LLM_TIMEOUT_S}s"
            )
        if result.error is not None:
            raise result.error
        return result.value


def _read_image(path: Path) -> tuple[bytes, str]:
    """Read the file as image bytes. Delegates to FileService for PDFs."""
    from app.services.file_service import FileService

    return FileService().read_image_bytes(path)
