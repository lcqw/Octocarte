# Octocarte

Navidrome/OpenSubsonic proxy built on Octo-Fiesta. Apple catalog metadata
comes from the separate ALACarte service. Unowned tracks play temporary YouTube
AAC/M4A while ALACarte acquires their whole parent album using its saved settings.
Once Navidrome indexes the files, local results and streams take precedence.

**Status:** the full backend workflow passed with real services, including native
ALAC acquisition, an ALACarte-initiated local Navidrome scan, local replacement
and subsequent native playback/seeking. Wavio phone acceptance passed, including
artist photos/top songs and unowned playback. Entergalactic completed as a full
15-track native ALAC album. Temporary local validation services were cleaned up.
NAS deployment requires shared music storage. See [validation](docs/octocarte/VALIDATION.md).

## Install

The [complete Compose package](deploy/README.md) is the standard installation.
It includes Octocarte, Navidrome, the YouTube shim, and ALACarte with its wrapper.
**Artist photos, Apple-ranked top songs, and unattended service authentication
are included.** No manual extension installation or browser-cookie copying is
required. The package generates a private integration token during initialization.

For the private NAS preview, a build helper prepares the images and a transferable
bundle. Install that bundle on the Docker host, choose the shared music folder,
and complete the normal Navidrome and ALACarte account setup in their UIs.
Public container images are not published yet. See the [installation steps](deploy/README.md).

ALACarte remains a separate service inside the same Compose project and owns
Apple credentials, preferences, acquisition, library management and scans.
Its music output and Navidrome's library mount point to the same host folder.
Clients connect to Octocarte using their Navidrome account.

Already running both services? The [external-service setup](docs/octocarte/EXTERNAL_SERVICES.md)
is retained for that use case; stock ALACarte has fewer integration capabilities.

## Behavior and boundaries

- Requests to `POST /api/download` contain only `albumId`. No quality, lyrics,
  storefront, artwork or other preference overrides are sent.
- ALACarte owns persistent deduplication and partial-album completion. HTTP 409
  is a normal no-op. Octocarte only coalesces in-flight song requests and debounces
  albums for 30 seconds in memory. Restarting clears this guard; ALACarte still
  decides whether work is needed.
- Album work runs in a bounded hosted queue independently of client disconnects.
  Failed submissions can retry on a later play. There is no new durable job store.
- Temporary metadata is `m4a` / `audio/mp4`, codec AAC, with unknown bitrate/size
  represented as zero in song metadata. It does not claim ALAC or Hi-Res quality.
  Navidrome's real metadata is preserved when local tracks replace placeholders.
- Range, 206, 416 and Content-Range pass through the resolver and stream response.
- Soulseek/slskd and the shim's permanent `/download` endpoint are not included.
  External playlist acquisition and starring-to-download are outside this MVP.
- The original chassis supports other providers, but Octocarte selects ALACarte
  by default. Its legacy download implementations are not used for Apple tracks.

Artist photos use ALACarte artist detail and standard Subsonic image responses.
Ranked artist top songs are included through the prepared ALACarte image.
The [integration notes](integrations/alacarte/README.md) describe the small maintained patches for contributors.
Apple ranking is retained while matching native Navidrome tracks take precedence.

## Verify

```sh
dotnet test octo-fiesta.sln
python -m pytest yt-dlp-shim/tests -q
docker build -t octocarte:mvp .
python3 tests/http_mvp.py
```

The Python suite needs Flask, requests and pytest. The .NET suite needs an
ASP.NET 9 runtime, available in the SDK container if missing on the host.
`http_mvp.py` uses disposable containers and controlled fixtures. It does not
prove real Apple downloads, scanning, codecs on disk, or Wavio seeking.

Live acceptance: search in Wavio → play an unowned result → observe prompt
YouTube playback and one whole-album ALACarte job → let ALACarte finish and scan
→ repeat search/play and verify the real Navidrome ID and native metadata.
Do not change the already validated ALACarte preferences for this test.

If using Caddy, point the reverse proxy at Octocarte's address and published port,
rather than Navidrome. On a shared Docker network, its address is `octocarte:8080`.

## Provider scope

The supported Octocarte workflow is ALACarte catalog/acquisition with YouTube
playback until Navidrome indexes the native files. Deezer, Qobuz, Tidal, Yandex
and SquidWTF implementations remain from Octo-Fiesta, but have not received
Octocarte end-to-end acceptance testing. Their presence is not a compatibility
guarantee. External playlists and legacy acquisition behavior are outside the
validated Octocarte workflow.

## Development

Changes use focused branches and pull requests against `dev`. The validated
baseline is tagged `mvp-validated-2026-09-07`. See [CONTRIBUTING.md](CONTRIBUTING.md)
for validation and release expectations. The repository remains private during
NAS stabilization; public release and image publication are separate decisions.

## Sources

See [NOTICE.OCTOCARTE.md](NOTICE.OCTOCARTE.md), [LICENSE](LICENSE), and the original
[Octo-Fiesta README](README.UPSTREAM.md). `origin` is the private Octocarte repository;
`upstream` is V1ck3s/octo-fiesta. GitHub container publishing is manual-only.
