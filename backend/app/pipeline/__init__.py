"""Pipeline package — provider selection lives here.

To add a new vision provider, implement the Pipeline protocol in a new module
(e.g. app/pipeline/openai.py) and register it in _PROVIDERS below. The rest of
the app calls get_pipeline() and never knows which provider is active.
"""

from __future__ import annotations

from app.config import settings
from app.pipeline.base import Pipeline, PipelineError, PipelineTimeoutError
from app.pipeline.mock import MockPipeline


_PROVIDERS: dict[str, type[Pipeline]] = {
    "mock": MockPipeline,
    # "gemini" is registered lazily below so the import doesn't fail when the
    # google-genai SDK isn't installed (e.g. in the test environment).
}


def _get_gemini() -> type[Pipeline]:
    from app.pipeline.gemini import GeminiPipeline

    return GeminiPipeline


def get_pipeline() -> Pipeline:
    """Return the active pipeline based on settings.vision_provider."""
    provider = settings.vision_provider
    if provider == "gemini":
        return _get_gemini()()
    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise PipelineError(
            f"Unknown vision provider '{provider}'", "INTERNAL"
        )
    return cls()


__all__ = ["Pipeline", "PipelineError", "PipelineTimeoutError", "get_pipeline"]
