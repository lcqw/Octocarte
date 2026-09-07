# Octocarte

Private Navidrome/OpenSubsonic proxy built on Octo-Fiesta. Apple catalog metadata
comes from the separate ALACarte service. Unowned tracks play temporary YouTube
AAC/M4A while ALACarte acquires their whole parent album using its saved settings.
Once Navidrome indexes the files, local results and streams take precedence.

**Status:** the full backend workflow passed with real services, including native
ALAC acquisition, an ALACarte-initiated local Navidrome scan, local replacement
and subsequent native playback/seeking. Wavio phone acceptance passed, including
artist photos/top songs and unowned playback. Entergalactic completed as a full
15-track native ALAC album. Temporary local validation services were cleaned up.
NAS deployment requires shared music storage. See [validation](docs/octocarte/VALIDATION.md).

## Start

1. Keep your existing ALACarte and Navidrome services running. ALACarte owns all
   Apple settings, credentials, library management and Navidrome scans. Its music
   output must be visible to Navidrome: use the same shared storage when they run
   on different machines. A scan cannot transfer files between hosts.
2. Copy `.env.octocarte.example` to `.env.octocarte` and set the three connection
   values. A container cannot reach host ALACarte using `127.0.0.1`; use
   `http://host.docker.internal:7373` on this Linux host.
3. Put only the `alacarte_session` cookie **value** in the secret file referenced
   by `ALACARTE_COOKIE_FILE`; use mode `600`. For this installation the file is
   `/home/lqw/.config/octocarte/alacarte-session-cookie`. Octocarte reads it when
   constructing ALACarte clients. After rotating the file, recreate the service
   with `docker compose --env-file .env.octocarte -f compose.octocarte.yml up -d --force-recreate octocarte`
   so an atomically replaced file is remounted. Never commit its contents.
   Never use ALACarte's master `.secret`. An empty file works only when ALACarte
   already uses its own externally managed authentication configuration.
4. Run:

   ```sh
   docker compose --env-file .env.octocarte -f compose.octocarte.yml up -d --build
   ```

5. Point Wavio at port `5880` on the Octocarte host, using your normal Navidrome
   client credentials. The default bind is loopback. Set `OCTOCARTE_BIND` to your
   private LAN interface address if Wavio runs on another device.

The shim has no published host port or music-library mount. Octocarte mounts
only its own state volume, not ALACarte's music or configuration directories.
No Navidrome administrator credentials are needed in Compose; the chassis
validates client credentials with Navidrome and uses them for local lookups.

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
Ranked artist top songs are available through the [optional ALACarte extension](integrations/alacarte/README.md), installed in this local validation setup.
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

## Sources

See [NOTICE.OCTOCARTE.md](NOTICE.OCTOCARTE.md), [LICENSE](LICENSE), and the original
[Octo-Fiesta README](README.md). `origin` is the private Octocarte repository;
`upstream` is V1ck3s/octo-fiesta. GitHub container publishing is manual-only.
