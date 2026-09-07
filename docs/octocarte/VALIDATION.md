# Octocarte MVP validation

## Automated

- 680 .NET tests pass (including the upstream suite).
- 22 shim tests pass.
- Both container images build; Compose validates and starts.
- Running-container HTTP fixtures verify Apple result IDs, temporary AAC/M4A
  metadata, nonblocking album submission, matching POST Origin, in-memory burst
  deduplication, HTTP ranges, local-result replacement and old-ID local playback.
- Local search still succeeds when ALACarte returns HTTP 503.
- GitHub CI passed at 6e5626a, including the authenticated POST Origin fix.

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

7. After the user enabled ALACarte's Navidrome integration, a second one-track
   album (`1498647640`, Billie Eilish — No Time To Die - Single) completed as
   ALAC in job `df1ccf81-381d-41f4-85aa-dd35cd355d70`. Temporary playback returned
   HTTP 206 in 3.503 seconds, and ALACarte logged a successful automatic scan.

## Remaining acceptance

The user's Navidrome runs on a NAS and cannot access this machine's ALACarte
output folder. No SMB/NFS share is currently mounted here. Scanning succeeds,
but the NAS cannot index files it cannot see. Shared storage or a local validation
Navidrome must be configured before the real local-track handoff can be tested.

Then validate local-ID replacement, native playback and Wavio seeking. Fixture
verification of the handoff is not a substitute for that live test. This MVP is
not yet declared production-ready. No further acquisitions should be started
until the storage setup is selected.
