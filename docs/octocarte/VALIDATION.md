# Octocarte MVP validation

## Automated

- 687 .NET tests pass (including the upstream suite).
- 22 shim tests pass.
- Both container images build; Compose validates and starts.
- Running-container HTTP fixtures verify Apple result IDs, temporary AAC/M4A
  metadata, nonblocking album submission, matching POST Origin, in-memory burst
  deduplication, HTTP ranges, local-result replacement and old-ID local playback.
- Local search still succeeds when ALACarte returns HTTP 503.
- GitHub CI passed at 5711203, including the complete streaming fixture and
  the optional ALACarte extension tests.

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

## Isolated local end-to-end test

The user authorized a disposable local Navidrome because the NAS cannot access
this machine's output folder. Navidrome 0.63.2 used its own data volume and a
read-only music mount. A temporary proxy instance targeted it. ALACarte's saved
NAS credentials were left untouched; only its scan URL temporarily pointed to a
test-only authentication relay. ALACarte initiated the actual scan. This relay
is not part of Octocarte or its deployment.

A fresh album (`1487502456`, Billie Eilish — everything i wanted - Single)
validated the full backend chain:

- Temporary YouTube playback: HTTP 206 in 2.907 seconds.
- ALACarte whole-album acquisition completed.
- ALACarte-initiated local Navidrome scan: HTTP 200, status ok.
- Search returned native local ID `Prb40LPFGoWHbJ3OIB6Opi`, M4A, 24-bit,
  44.1 kHz, bitrate 2117 kbps, replacing the corresponding placeholder.
- Playback through both the old external ID and real local ID returned native
  ALAC bytes, verified with ffprobe.
- A nonzero seek returned HTTP 206 and
  `Content-Range: bytes 1048576-1114111/42477286` with exactly 65536 bytes.

## Wavio phone acceptance and cleanup

The user confirmed the updated artist photo, album list, top songs and unowned
playback/seek test worked, using **Kid Cudi — Entergalactic Theme** from
**Entergalactic**. Earlier phone tests had separately confirmed local playback
and seeking. This completes the requested MVP acceptance on Wavio.

The actual album handoff was then checked before cleanup:

- ALACarte job `ac1fe4e1-c182-4351-8ecf-9eb3eed507d0`, album `1647008692`,
  completed with quality `alac`.
- All 15 expected album tracks were present and indexed by local Navidrome.
- All 15 M4A files were independently inspected: codec ALAC, 24-bit, 44.1 kHz.
- Search returned real track `ZRyWYL5D4oMvJp2zSx445C` for Entergalactic Theme,
  with native metadata and local album `4TQmpDH2I9bLuTHN3pH0ou`.
- Both original placeholder `ext-apple-song-1647008703` and the real local ID
  subsequently returned native seeks: HTTP 206,
  `Content-Range: bytes 65536-131071/17747073`, exactly 65536 bytes.

ALACarte's scan URL was restored to `http://192.168.1.169:4533` and verified.
The three `octocarte-validation-*` containers, isolated Navidrome data volume,
generated local login and partial media probes were removed. Port 15880 is no
longer the test server. Existing downloaded music, ALACarte credentials, the
approved top-songs extension, and the normal loopback Octocarte/shim services
were retained. Existing Monochrome and ALACarte source checkouts were untouched.

Production NAS deployment still needs ALACarte's music output on storage visible
to the NAS Navidrome. A successful scan cannot transfer files between hosts.

## Artist compatibility follow-up

Artist detail artwork now reaches `getArtist`, `getArtistInfo`, `getArtistInfo2`
and `getCoverArt`; Apple search results advertise a lazy artist cover-art ID.
Concurrent artist/discography/image requests share one bounded, five-minute
metadata cache entry. Failures can retry rather than caching empty responses.
Both artist-info variants preserve native Navidrome passthrough for local IDs.
Regression tests cover JSON/XML image fields, one upstream request, failed-call
retry and container routing.

On the updated temporary proxy, Kanye West returned 43 albums with an image URL
in 0.096 seconds; `getArtistInfo2` returned its image in 0.007 seconds and
`getCoverArt` returned HTTP 200 JPEG bytes in 0.111 seconds. ALACarte's own cache
may already have been warm. The user subsequently confirmed the updated artist
page worked during the phone acceptance test.

Real Apple top songs are available, but stock ALACarte does not expose them.
The user approved the separate [optional patch](../../integrations/alacarte/README.md),
which is now installed as a small overlay on the existing ALACarte image.
Its complete 142-test backend suite passes, including normalization and HTTP
route checks. The live endpoint rejects anonymous requests with HTTP 401 and
preserves the saved storefront/rating/ALAC/lyrics/artwork/scan settings.

Octocarte's expanded HTTP fixture checks ranked order, name/ID lookups,
JSON/XML native replacement, count validation, stock-endpoint fallback and
extension advertising. Live Kanye West requests returned five ranked songs
in 0.613 seconds by name and 0.129 seconds by ID. Billie Eilish returned 50
ranked songs in 0.346 seconds; three already owned tracks were replaced with
real Navidrome IDs and native 24-bit / 44.1 or 48 kHz metadata. These checks
were read-only and did not submit album jobs. The subsequent phone acceptance
and real Entergalactic acquisition are recorded above.
