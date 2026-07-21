import importlib.util
import io
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_release_gates.py"
SPEC = importlib.util.spec_from_file_location("verify_release_gates_limits", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeHeaders:
    def __init__(self, *, content_type="application/json", content_length=None):
        self.content_type = content_type
        self.content_length = content_length

    def get_content_type(self):
        return self.content_type

    def get(self, name):
        if name.lower() == "content-length":
            return self.content_length
        return None


class FakeResponse(io.BytesIO):
    def __init__(self, body, *, content_length=None):
        super().__init__(body)
        self.headers = FakeHeaders(content_length=content_length)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False


def test_declared_oversized_response_is_rejected_before_read(monkeypatch):
    response = FakeResponse(
        b"{}",
        content_length=str(MODULE.MAX_RESPONSE_BYTES + 1),
    )
    monkeypatch.setattr(MODULE, "urlopen", lambda request, timeout: response)

    with pytest.raises(RuntimeError, match="exceeded the .*byte limit"):
        MODULE._fetch_page("owner/repository", "a" * 40, "token", 1)


def test_streamed_oversized_response_is_rejected(monkeypatch):
    response = FakeResponse(b"x" * (MODULE.MAX_RESPONSE_BYTES + 1))
    monkeypatch.setattr(MODULE, "urlopen", lambda request, timeout: response)

    with pytest.raises(RuntimeError, match="exceeded the .*byte limit"):
        MODULE._fetch_page("owner/repository", "a" * 40, "token", 1)


def test_invalid_content_length_is_rejected(monkeypatch):
    response = FakeResponse(b"{}", content_length="not-a-number")
    monkeypatch.setattr(MODULE, "urlopen", lambda request, timeout: response)

    with pytest.raises(RuntimeError, match="invalid Content-Length"):
        MODULE._fetch_page("owner/repository", "a" * 40, "token", 1)


def test_negative_content_length_is_rejected(monkeypatch):
    response = FakeResponse(b"{}", content_length="-1")
    monkeypatch.setattr(MODULE, "urlopen", lambda request, timeout: response)

    with pytest.raises(RuntimeError, match="invalid Content-Length"):
        MODULE._fetch_page("owner/repository", "a" * 40, "token", 1)


def test_truncated_response_body_is_rejected(monkeypatch):
    response = FakeResponse(b"{}", content_length="10")
    monkeypatch.setattr(MODULE, "urlopen", lambda request, timeout: response)

    with pytest.raises(RuntimeError, match="did not match Content-Length"):
        MODULE._fetch_page("owner/repository", "a" * 40, "token", 1)


def test_non_bytes_response_body_is_rejected():
    class NonBytesResponse:
        headers = FakeHeaders()

        def read(self, limit):
            return "{}"

    with pytest.raises(RuntimeError, match="body was not bytes"):
        MODULE._read_json_payload(NonBytesResponse())
