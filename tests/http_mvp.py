#!/usr/bin/env python3
"""Container-level MVP contract, with controlled ALACarte/Navidrome/shim fixtures.
No real credentials, Apple jobs, YouTube calls or user-library writes.
Usage: python3 tests/http_mvp.py (requires docker image octocarte:mvp).
"""
import xml.etree.ElementTree as ET
import json
import os
import secrets
import tempfile
from pathlib import Path
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

service_auth = os.environ.get("OCTOCARTE_TEST_SERVICE_AUTH") == "1"
auth_token = secrets.token_urlsafe(32)
image_name = os.environ.get("OCTOCARTE_TEST_IMAGE", "octocarte:mvp")

state = {"local": False, "catalog_down": False, "posts": [], "youtube": 0, "local_streams": 0, "artist_calls": 0, "top_calls": 0}
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
        if path.startswith("/api/") and service_auth:
            if self.headers.get("Authorization") != "Bearer " + auth_token:
                return self.reply({}, 401)
            assert not self.headers.get("Cookie")
        if path == "/api/search":
            if state["catalog_down"]:
                return self.reply({}, 503)
            return self.reply({"songs": [{"id": "42", "name": "Song", "artistName": "Artist", "albumName": "Album", "albumId": "7", "durationMs": 120000}], "albums": [], "artists": [{"id": "9", "name": "Artist"}]})
        if path == "/api/artist/9/top-songs":
            state["top_calls"] += 1
            return self.reply({"songs": [{"id": "43", "name": "Other", "artistName": "Artist", "albumId": "8"}, {"id": "42", "name": "Song", "artistName": "Artist", "albumId": "7"}]})
        if path == "/api/artist/10/top-songs":
            return self.reply({}, 404)
        if path == "/api/artist/10":
            return self.reply({"artist": {"id": "10", "name": "Stock ALACarte Artist"}, "albums": []})
        if path == "/api/artist/9":
            state["artist_calls"] += 1
            return self.reply({"artist": {"id": "9", "name": "Artist", "artworkTemplate": "https://images.example/{w}x{h}bb.jpg"}, "albums": [{"id": "7", "name": "Album"}]})
        if path in ("/rest/getArtistInfo", "/rest/getArtistInfo2"):
            return self.reply({"subsonic-response": {"status": "ok", path.rsplit("/get", 1)[1][0].lower() + path.rsplit("/get", 1)[1][1:]: {"biography": "local passthrough"}}})
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
        if path == "/rest/getArtist":
            response["artist"] = {"id": "local-artist", "name": "Artist", "coverArt": "ar-local-artist_0", "artistImageUrl": "http://navidrome:4533/broken-photo", "album": [{"id": "local-7", "name": "Album"}] if state["local"] else []}
        if path == "/rest/getTopSongs":
            response["topSongs"] = {"song": [local_song]}
        if path == "/rest/getOpenSubsonicExtensions":
            response["openSubsonicExtensions"] = [{"name": "songLyrics", "versions": [1]}]
        if path == "/rest/search3" and urllib.parse.parse_qs(parsed.query).get("f") == ["xml"]:
            root = ET.Element("subsonic-response", {"xmlns": "http://subsonic.org/restapi", "status": "ok"})
            results = ET.SubElement(root, "searchResult3")
            if state["local"]: ET.SubElement(results, "song", {k: str(v) for k, v in local_song.items()})
            body = ET.tostring(root)
            self.send_response(200)
            self.send_header("Content-Type", "application/xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/rest/getSong":
            response["song"] = local_song
        return self.reply({"subsonic-response": response})

    def do_POST(self):
        assert self.path == "/api/download"
        if service_auth:
            assert self.headers.get("Authorization") == "Bearer " + auth_token
            assert not self.headers.get("Cookie")
        assert self.headers.get("Origin") == "http://" + self.headers["Host"]
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
secret_dir = tempfile.TemporaryDirectory(prefix="octocarte-http-auth-")
token_path = Path(secret_dir.name) / "service-token"
token_path.write_text(auth_token)
token_path.chmod(0o600)
auth_args = ["-v", str(token_path) + ":/run/secrets/alacarte-token:ro", "-e", "Alacarte__ServiceTokenFile=/run/secrets/alacarte-token"] if service_auth else []
try:
    subprocess.run(["docker", "run", "--rm", "-d", "--name", name, "--network", "host",
                    "-e", f"ASPNETCORE_URLS={base}", "-e", f"Subsonic__Url={fixture_url}",
                    "-e", "Subsonic__MusicService=Alacarte", "-e", f"Alacarte__Url={fixture_url}",
                    "-e", f"YouTube__ShimUrl={fixture_url}", *auth_args, image_name], check=True, stdout=subprocess.DEVNULL)
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
    for endpoint, key in [("getArtistInfo", "artistInfo"), ("getArtistInfo2.view", "artistInfo2")]:
        with get("/rest/" + endpoint, id="ext-apple-artist-9") as response:
            info = json.load(response)["subsonic-response"][key]
        assert info["largeImageUrl"] == "https://images.example/600x600bb.jpg"
        with get("/rest/" + endpoint, id="local-artist") as response:
            assert json.load(response)["subsonic-response"][key]["biography"] == "local passthrough"
    with get("/rest/getArtist", id="ext-apple-artist-9") as response:
        artist = json.load(response)["subsonic-response"]["artist"]
    assert artist["albumCount"] == 1 and len(artist["album"]) == 1
    assert artist["artistImageUrl"] == "https://images.example/600x600bb.jpg"
    assert state["artist_calls"] == 1
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
    # After indexing, both generations of artist-info must retain Apple's photo.
    # The server's same-name biography and internal image URL must not replace it.
    for _ in range(2):
        with get("/rest/getArtist", id="local-artist") as response:
            profile = json.load(response)["subsonic-response"]["artist"]
        assert profile["id"] == "local-artist"
        assert profile["coverArt"] == "ext-apple-artist-9"
        assert profile["artistImageUrl"] == "https://images.example/600x600bb.jpg"
        assert profile["album"][0]["id"] == "local-7"
        for endpoint, key in [("getArtistInfo", "artistInfo"), ("getArtistInfo2.view", "artistInfo2")]:
            with get("/rest/" + endpoint, id="local-artist") as response:
                info = json.load(response)["subsonic-response"][key]
            assert info["largeImageUrl"] == profile["artistImageUrl"] and "biography" not in info
            with get("/rest/" + endpoint, id="local-artist", f="xml") as response:
                info_xml = ET.fromstring(response.read()).find("{*}" + key)
            assert info_xml.find("{*}largeImageUrl").text == profile["artistImageUrl"]
            assert info_xml.find("{*}biography") is None
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
    for lookup in [{"artist": "Artist"}, {"id": "ext-apple-artist-9", "artist": "ignored"}, {"id": "local-artist"}]:
        with get("/rest/getTopSongs.view", **lookup) as response:
            top = json.load(response)["subsonic-response"]["topSongs"]["song"]
        assert [x["id"] for x in top] == ["ext-apple-song-43", "local-42"]
        assert top[0]["suffix"] == "m4a" and top[1]["bitDepth"] == 24
    assert state["top_calls"] == 1
    with get("/rest/getTopSongs", id="ext-apple-artist-9", f="xml") as response:
        top = ET.fromstring(response.read()).findall("{*}topSongs/{*}song")
    assert [x.attrib["id"] for x in top] == ["ext-apple-song-43", "local-42"]
    assert top[1].attrib["bitDepth"] == "24"
    with get("/rest/getTopSongs", id="ext-apple-artist-9", count=1) as response:
        assert len(json.load(response)["subsonic-response"]["topSongs"]["song"]) == 1
    with get("/rest/getTopSongs", id="ext-apple-artist-10") as response:
        assert json.load(response)["subsonic-response"]["topSongs"]["song"][0]["id"] == "local-42"
    with get("/rest/getTopSongs", artist="Artist", count=-1) as response:
        assert json.load(response)["subsonic-response"]["error"]["code"] == 10
    with get("/rest/getOpenSubsonicExtensions") as response:
        extensions = json.load(response)["subsonic-response"]["openSubsonicExtensions"]
    assert {e["name"] for e in extensions} == {"songLyrics", "topSongsByArtistId"}
    with get("/rest/getOpenSubsonicExtensions", f="xml") as response:
        extensions = ET.fromstring(response.read()).findall("{*}openSubsonicExtensions")
    assert {e.attrib["name"] for e in extensions} == {"songLyrics", "topSongsByArtistId"}
    if service_auth:
        token_path.write_text("")  # Invalid credentials must not break local search.
    state["catalog_down"] = True
    with get("/rest/search3", query="Song") as response:
        songs = json.load(response)["subsonic-response"]["searchResult3"]["song"]
    assert len(songs) == 1 and songs[0]["id"] == "local-42"
    print("PASS: artist images, ranked top songs, local replacement, XML/JSON, extension advertising, fallback, HTTP catalog, external IDs, AAC metadata, nonblocking album POST, burst guard, ranges, local search replacement and old-ID Navidrome playback")
finally:
    release_post.set()
    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    server.shutdown()
    secret_dir.cleanup()
