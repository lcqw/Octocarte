# Octocarte MVP validation

## Automated

- 680 .NET tests pass (including the upstream suite).
- 22 shim tests pass.
- Both container images build; Compose validates and starts.
- Running-container HTTP fixtures verify Apple result IDs, temporary AAC/M4A
  metadata, nonblocking album submission, matching POST Origin, in-memory burst
  deduplication, HTTP ranges, local-result replacement and old-ID local playback.
- Local search still succeeds when ALACarte returns HTTP 503.
- GitHub CI passed at bd9055c. Later commits must also pass CI.

## Live evidence (2026-09-07)

ALACarte and Navidrome authenticate using local secret files; their contents are
not included here or in Git. Octocarte runs on loopback port 5880.

1. Apple catalog search through Octocarte returned external song
   `ext-apple-song-1696819855`, album `ext-apple-album-1696819852`:
   Billie Eilish — What Was I Made For? (From The Motion Picture "Barbie") - Single.
2. Playback through Octocarte returned HTTP 206 in 2.906 seconds with
   `Content-Type: audio/mp4`, `Content-Range: bytes 0-65535/3599395`.
   A warm replay took 0.033 seconds. A separate real YouTube sample was verified
   as AAC stereo with ffprobe.
3. Authenticated ALACarte writes require Origin to match Host; this requirement
   was added to the client and regression fixtures after live validation.
4. ALACarte received one whole-album job, ID
   `e37d029c-ea24-4ee5-976d-960587fe9eb8`, album `1696819852`. It completed with
   quality `alac`, without any quality/storefront overrides from Octocarte.
5. The new file is native ALAC, 24-bit / 48 kHz stereo. ALACarte also produced
   artwork and an LRC file. No downloader, tagging or lyrics implementation was
   added to Octocarte.
6. Resubmitting the completed album returned HTTP 409 and left one matching job,
   confirming ALACarte's library-aware no-op. Octocarte treats that as success.

## Remaining acceptance

The current ALACarte instance reports `navidromeEnabled: false`, the default
Navidrome URL and no configured scan credentials. Therefore no automatic scan
occurred and the selected track is not yet returned by the user's Navidrome.
The user must configure this in ALACarte's own UI and ensure that its music
output is visible to Navidrome. Octocarte must not take ownership of scanning.

After that, validate the real scan/local handoff and Wavio playback/seeking.
Fixture verification of the handoff is not a substitute for that live test.
This MVP is not yet declared production-ready.
