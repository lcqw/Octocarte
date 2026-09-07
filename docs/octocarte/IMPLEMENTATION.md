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

## Validation and deployment
See [VALIDATION.md](VALIDATION.md) for current automated and live evidence.

The inherited publishing workflow ran for the initial history/planning pushes.
It is now manual-only. Anonymous GHCR access returned HTTP 401; account package
listing was unavailable without read:packages scope. The repository itself was
verified private and not a fork.

Verified shim image tools: Python 3.12.14, yt-dlp 2026.08.19, Deno 2.9.6,
FFmpeg 7.1.5, Flask 3.1.3, Gunicorn 26.2.0, requests 2.34.2. Build defaults pin
yt-dlp, Deno and Python package versions to the inspected versions.

Additional upstream master and fix/deezer-private-search histories are preserved
on private `upstream-snapshot/*` branches. All initially fetched upstream commits
are reachable from private repository branches/tags.
