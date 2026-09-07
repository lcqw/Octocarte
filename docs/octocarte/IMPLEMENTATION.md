# Octocarte MVP

## Inspected sources (2026-09-07)
- V1ck3s/octo-fiesta: c4d0f5734d1868b8f3f4c031566b705480c32efd (dev).
- winters27/octo: f9cf6f4c5eef795909335dbe52fe8e43fd739666.
- sosjalapeno/alacarte: ef9b677c21b024a0acbf4f88d47c4ebff24802fa.

Octo-Fiesta's IMusicMetadataService, SubsonicModelMapper, LocalLibraryService and
SubsonicController provide catalog injection, local-first merging, live local ID
resolution and authenticated proxying. Keep these as the chassis.

ALACarte routes: GET /api/search?q=...; GET /api/album/:id;
GET /api/artist/:id; POST /api/download with {albumId}; GET /api/queue.
Song-link search resolves a missing parent album through ALACarte. No direct
Apple API client belongs in Octocarte. Omit quality and storefront overrides;
ALACarte reads its persisted preferences. Its queue already checks running jobs
and library presence, but serialize submissions in Octocarte because that check
precedes asynchronous metadata reads. Never copy ALACarte implementation code.

Port Octo's YouTubeResolver, DirectStreamInfo contract, response ownership and
manual HTTP range forwarding, plus yt-dlp-shim and its tests. Exclude Soulseek,
slskd, permanent downloads, radio and admin features. External Apple metadata
must describe temporary AAC/M4A, without lossless/Hi-Res claims.

Milestones: preserved upstream history; catalog and streaming integration;
contract tests and container build; live client/acquisition/local handoff validation.
Do not call the MVP complete until the live chain is observed.

## Environment
Git 2.55.0; Docker 29.7.2; Compose 5.5.1; .NET SDK 9.0.120 (upstream targets
net9.0); Python 3.14.7; Node 22.23.2; ffmpeg n9.0.1; uv 0.12.10.
Host lacks pip, yt-dlp, Deno, Flask and Gunicorn. The imported shim Dockerfile
uses Python 3.12, ffmpeg, yt-dlp, Deno, Flask, Gunicorn and requests. Isolate those
in its image. .NET host lacks ASP.NET runtime; use containers for runtime tests.

GitHub identity Vixxy0w0; CLI repo/workflow scopes verified. Octocarte verified
private and not a fork. origin is private Octocarte; upstream is Octo-Fiesta.
Existing Monochrome work has dirty files and is outside this checkout.

## Duplicate ownership clarification
ALACarte remains the sole persistent duplicate authority, including queued/running
job reuse, HTTP 409 already-present handling and partial-album completion.
Octocarte uses only a bounded in-memory queue, in-flight song keys and a 30-second
album burst debounce. It has no Apple library index or duplicate database.

## Initial implementation validation
678 .NET tests and 22 Python tests passed. Both Docker images built.
`tests/http_mvp.py` passed against the running application with controlled HTTP
fixtures: search IDs and metadata, Range/206 passthrough, playback during a blocked
album POST, burst deduplication, native metadata after indexing and later local
playback using an old placeholder ID. These fixtures do not prove real Apple
acquisition or Wavio behavior.

The imported Docker publishing workflow is manual-only for Octocarte; normal
private development pushes run CI without publishing a container package.

## Live YouTube probe
The imported resolver returned HTTP 200 in 2.853 seconds. A subsequent byte
request returned HTTP 206, Content-Type audio/mp4 and Content-Range
`bytes 0-65535/3434426` in 0.084 seconds. ffprobe identified AAC, 44.1 kHz, stereo.
This verifies one real search/stream sample, not every track or client.

Verified shim image tools: Python 3.12.14, yt-dlp 2026.08.19, Deno 2.9.6,
FFmpeg 7.1.5, Flask 3.1.3, Gunicorn 26.2.0, requests 2.34.2. Build defaults pin
yt-dlp, Deno and Python package versions to the inspected versions.

Navidrome is reachable. Live ALACarte/Wavio testing still requires the user to
populate the designated session-cookie file and provide test-client credential
file access. No master secret has been read and no real Apple job has been sent.

## Final automated checks and live setup
680 .NET tests and 22 shim tests pass. The HTTP fixture test also verifies local
search survives ALACarte HTTP 503. Compose validates and both services start;
Octocarte binds only 127.0.0.1:5880 for validation. The supplied ALACarte session
works. Navidrome's supplied test credentials currently receive error 40, so live
playback/acquisition awaits refreshed credentials. No real Apple job was submitted.

The inherited publishing workflow ran for the initial history/planning pushes.
It is now manual-only. Anonymous GHCR access returned HTTP 401; account package
listing was unavailable without read:packages scope. The repository itself was
verified private and not a fork.
