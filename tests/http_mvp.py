#!/usr/bin/env python3
"""Container-level MVP contract, with controlled ALACarte/Navidrome/shim fixtures.
No real credentials, Apple jobs, YouTube calls or user-library writes.
Usage: python3 tests/http_mvp.py (requires docker image octocarte:mvp).
"""
import json
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

state = {"local": False, "catalog_down": False, "posts": [], "youtube": 0, "local_streams": 0}
post_started = threading.Event()
release_post = threading.Event()
local_song = {"id": "local-42", "title": "Song", "artist": "Artist", "album": "Album",
              "albumId": "local-7", "suffix": "m4a", "contentType": "audio/mp4",
              "bitDepth": 24, "samplingRate": 96000, "bitRate": 2400, "duration": 120}


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, data, status=200, headers=None):
        body = data if isinstance(data, bytes) else json.dumps(data, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "audio/mp4" if isinstance(data, bytes) else "application/json")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/search":
            if state["catalog_down"]:
                return self.reply({}, 503)
            return self.reply({"songs": [{"id": "42", "name": "Song", "artistName": "Artist", "albumName": "Album", "albumId": "7", "durationMs": 120000}], "albums": [], "artists": []})
        if path == "/search":
            state["youtube"] += 1
            return self.reply({"video_id": "fixture"})
        if path == "/stream":
            assert self.headers.get("Range") == "bytes=0-1"
            return self.reply(b"YT", 206, {"Content-Range": "bytes 0-1/100", "Accept-Ranges": "bytes"})
        if path == "/rest/stream":
            assert urllib.parse.parse_qs(parsed.query)["id"] == ["local-42"]
            state["local_streams"] += 1
            return self.reply(b"AL", 206, {"Content-Range": "bytes 0-1/200", "Accept-Ranges": "bytes"})
        response = {"status": "ok", "version": "1.16.1"}
        if path == "/rest/search3":
            response["searchResult3"] = {"song": [local_song] if state["local"] else [], "album": [], "artist": []}
        if path == "/rest/getSong":
            response["song"] = local_song
        return self.reply({"subsonic-response": response})

    def do_POST(self):
        assert self.path == "/api/download"
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            chunks = []
            while True:
                size = int(self.rfile.readline().strip(), 16)
                if not size:
                    self.rfile.readline()
                    break
                chunks.append(self.rfile.read(size))
                self.rfile.read(2)
            raw = b"".join(chunks)
        else:
            raw = self.rfile.read(int(self.headers["Content-Length"]))
        body = json.loads(raw)
        assert body == {"albumId": "7"}, body
        state["posts"].append(body)
        post_started.set()
        release_post.wait(10)
        self.reply({"job": {"id": "job-7", "status": "queued"}}, 202)


def get(path, **kwargs):
    auth = {"u": "fixture", "p": "fixture-only", "v": "1.16.1", "c": "contract", "f": "json"}
    auth.update(kwargs)
    return urllib.request.urlopen(urllib.request.Request(base + path + "?" + urllib.parse.urlencode(auth), headers={"Range": "bytes=0-1"}), timeout=5)


server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
threading.Thread(target=server.serve_forever, daemon=True).start()
fixture_url = f"http://127.0.0.1:{server.server_port}"
# Reserve a free port before starting the isolated container.
import socket
with socket.socket() as port_socket:
    port_socket.bind(("127.0.0.1", 0))
    port = port_socket.getsockname()[1]
base = f"http://127.0.0.1:{port}"
name = "octocarte-contract-" + uuid.uuid4().hex[:8]
try:
    subprocess.run(["docker", "run", "--rm", "-d", "--name", name, "--network", "host",
                    "-e", f"ASPNETCORE_URLS={base}", "-e", f"Subsonic__Url={fixture_url}",
                    "-e", "Subsonic__MusicService=Alacarte", "-e", f"Alacarte__Url={fixture_url}",
                    "-e", f"YouTube__ShimUrl={fixture_url}", "octocarte:mvp"], check=True, stdout=subprocess.DEVNULL)
    for _ in range(100):
        try:
            urllib.request.urlopen(base, timeout=1).close()
            break
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    else:
        raise AssertionError("Octocarte failed to start")
    with get("/rest/search3", query="Song") as response:
        songs = json.load(response)["subsonic-response"]["searchResult3"]["song"]
    assert len(songs) == 1, songs
    assert songs[0]["id"] == "ext-apple-song-42"
    assert songs[0]["albumId"] == "ext-apple-album-7"
    assert songs[0]["suffix"] == "m4a" and songs[0]["contentType"] == "audio/mp4"
    assert "bitDepth" not in songs[0]
    start = time.monotonic()
    with get("/rest/stream", id="ext-apple-song-42") as response:
        assert response.status == 206
        assert response.headers["Content-Range"] == "bytes 0-1/100"
        assert response.read() == b"YT"
    assert time.monotonic() - start < 3, "Playback waited for blocked album POST"
    assert post_started.wait(2)
    for _ in range(3):
        with get("/rest/stream", id="ext-apple-song-42") as response:
            assert response.read() == b"YT"
    assert len(state["posts"]) == 1
    release_post.set()
    # Simulate ALACarte completing and Navidrome indexing the native file.
    state["local"] = True
    youtube_before = state["youtube"]
    with get("/rest/search3", query="Song") as response:
        songs = json.load(response)["subsonic-response"]["searchResult3"]["song"]
    assert len(songs) == 1 and songs[0]["id"] == "local-42", songs
    assert songs[0]["bitDepth"] == 24 and songs[0]["samplingRate"] == 96000
    # Old playlist placeholder IDs must also resolve to the real local stream.
    with get("/rest/stream", id="ext-apple-song-42") as response:
        assert response.status == 206
        assert response.headers["Content-Range"] == "bytes 0-1/200"
        assert response.read() == b"AL"
    assert state["youtube"] == youtube_before and state["local_streams"] == 1
    state["catalog_down"] = True
    with get("/rest/search3", query="Song") as response:
        songs = json.load(response)["subsonic-response"]["searchResult3"]["song"]
    assert len(songs) == 1 and songs[0]["id"] == "local-42"
    print("PASS: HTTP catalog, external IDs, AAC metadata, nonblocking album POST, burst guard, ranges, local search replacement and old-ID Navidrome playback")
finally:
    release_post.set()
    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server.shutdown()
