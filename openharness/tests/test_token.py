"""Tests for TOKEN.TXT loading and validation."""

import tempfile
import os
from pathlib import Path

from openharness.api.token import load_token, validate_token


def test_load_token_valid():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("sk-abc123testkey456")
        f.flush()
        token = load_token(f.name)
        assert token == "sk-abc123testkey456"
    os.unlink(f.name)


def test_load_token_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("")
        f.flush()
        token = load_token(f.name)
        assert token == ""
    os.unlink(f.name)


def test_load_token_unicode_rejected():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("여기에_API_키를_입력하세요")
        f.flush()
        token = load_token(f.name)
        assert token == ""
    os.unlink(f.name)


def test_load_token_missing_file():
    token = load_token("/nonexistent/TOKEN.TXT")
    assert token == ""


def test_validate_token_valid():
    is_valid, msg = validate_token("sk-abc123testkey456")
    assert is_valid is True
    assert "loaded" in msg.lower() or "chars" in msg.lower()


def test_validate_token_empty():
    is_valid, msg = validate_token("")
    assert is_valid is False


def test_validate_token_too_short():
    is_valid, msg = validate_token("abc")
    assert is_valid is False
    assert "short" in msg.lower()


def test_load_token_with_bom():
    """Test BOM-encoded file (utf-8-sig)."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
        f.write(b"\xef\xbb\xbfsk-test-bom-key")
        f.flush()
        token = load_token(f.name)
        assert token == "sk-test-bom-key"
    os.unlink(f.name)
