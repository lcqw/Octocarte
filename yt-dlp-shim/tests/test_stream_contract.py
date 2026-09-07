"""Octocarte: range passthrough and no permanent YouTube acquisition."""
import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import pytest


@pytest.mark.parametrize("status,content_range", [(200, None), (206, "bytes 0-1/100"), (416, "bytes */100")])
def test_stream_passthrough(monkeypatch, status, content_range):
    upstream = Mock()
    upstream.status_code = status
    upstream.headers = {"Content-Type": "audio/mp4", "Content-Length": "2"}
    if content_range:
        upstream.headers["Content-Range"] = content_range
    upstream.iter_content.return_value = [b"ab"]
    monkeypatch.setattr(app, "_resolve_url", lambda *a, **kw: "https://fixture.invalid/audio")
    opened = Mock(return_value=upstream)
    monkeypatch.setattr(app, "_open_upstream", opened)
    with app.app.test_client() as client:
        response = client.get("/stream?id=video", headers={"Range": "bytes=0-1"})
        assert response.status_code == status
        assert response.data == b"ab"
        assert response.headers.get("Content-Range") == content_range
        assert response.headers["Content-Type"] == "audio/mp4"
    assert opened.call_args.args[1]["Range"] == "bytes=0-1"
    upstream.close.assert_called()


def test_no_permanent_download_endpoint():
    with app.app.test_client() as client:
        assert client.get("/download?id=video&dest=/music/track").status_code == 404


def test_format_cannot_fallback_to_webm():
    assert "webm" not in app._AUDIO_FORMAT
    assert not app._AUDIO_FORMAT.endswith("/bestaudio")
