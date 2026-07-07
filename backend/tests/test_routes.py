"""Endpoint happy-path tests using the mock pipeline.

We use FastAPI's TestClient with the mock provider forced in conftest.py, so
these tests never touch the network. They verify the full upload -> poll ->
CSV flow end-to-end.
"""

import io
import time

from fastapi.testclient import TestClient

from app.main import create_app


client = TestClient(create_app())


def _png_bytes() -> bytes:
    # Minimal valid 1x1 PNG.
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000d49444154789c6300010000000500010d0a2db40000000049454e44"
        "ae426082"
    )


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["provider"] == "mock"


def test_upload_rejects_oversized(monkeypatch) -> None:
    from app.services import file_service as fs_mod

    # Lower the limit to 0 MB so any non-empty upload is "oversized".
    fs_mod.settings.max_file_size_mb = 0
    try:
        r = client.post(
            "/api/upload",
            files={"file": ("test.png", _png_bytes(), "image/png")},
        )
        assert r.status_code == 400
        assert r.json()["code"] == "OVERSIZED"
    finally:
        fs_mod.settings.max_file_size_mb = 20


def test_upload_rejects_bad_extension() -> None:
    r = client.post(
        "/api/upload",
        files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
    )
    assert r.status_code == 400
    assert r.json()["code"] == "BAD_FILE"


def test_upload_rejects_wrong_magic_bytes() -> None:
    # Claims to be PNG, but the body is an EXE header.
    r = client.post(
        "/api/upload",
        files={"file": ("fake.png", b"MZ\x90\x00", "image/png")},
    )
    assert r.status_code == 400
    assert r.json()["code"] == "BAD_FILE"


def test_upload_then_poll_then_csv() -> None:
    # Upload
    r = client.post(
        "/api/upload",
        files={"file": ("iso.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    # Poll until done (mock pipeline is synchronous-fast, but the route uses
    # BackgroundTasks, so we may need a couple of ticks).
    mto = None
    for _ in range(40):
        r = client.get(f"/api/mto/{job_id}")
        assert r.status_code == 200
        body = r.json()
        if body["state"] == "done":
            mto = body["mto"]
            break
        time.sleep(0.1)
    assert mto is not None, "Job never reached 'done' state"
    assert mto["source"] == "mock"
    assert len(mto["items"]) > 0
    # Mock has 8 flanges -> 4 joints -> 4 gaskets + 4 bolt sets
    assert mto["summary"]["gaskets"] == 4
    assert mto["summary"]["bolt_sets"] == 4
    assert mto["summary"]["flanges"] == 8

    # CSV
    r = client.get(f"/api/mto/{job_id}/csv")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    csv_text = r.content.decode("utf-8")
    assert "Drawing Metadata" in csv_text
    assert "Summary" in csv_text
    assert "PIPE" in csv_text


def test_get_unknown_job_404() -> None:
    r = client.get("/api/mto/does-not-exist")
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_csv_for_not_ready_job_409() -> None:
    # Create a job but don't run the pipeline — it stays in PENDING.
    from app.services.job_store import get_job_store

    job = get_job_store().create("pending.png")
    r = client.get(f"/api/mto/{job.job_id}/csv")
    assert r.status_code == 409
    assert r.json()["code"] == "NOT_READY"
