# Validation

## Automated evidence

The `v0.0.5-alpha.1` release passed 692 .NET tests, the controlled HTTP streaming
fixture, clean full-stack installation and existing-Navidrome integration tests.
Five images were published to GHCR, downloaded again and tested with
fresh startup. Matching release-source/configuration assets verified against their
checksums. CI also covers the shim and ALACarte integration patches.

The standalone installation tests start a disposable Navidrome under a separate
Compose project, verify catalog/photos/top songs, index generated ALAC audio and
check HTTP 206/Content-Range. They recreate Octocarte's containers while retaining
its volumes, then verify the original token and Navidrome account still work and
that Navidrome's original container remains running. These tests do not perform
Apple sign-in or download paid catalog audio.

## Reported NAS acceptance — 2026-09-07

A user installed `0.0.5-alpha.1` from a fresh repository clone and GHCR pulls on a
UGREEN DXP4800 Pro (UGOS Pro), with fresh Docker volumes. In Wavio they reported:

- Immediate search results, artist profiles and ranked top songs.
- Unowned playback beginning in roughly 0.5–1 second.
- Immediate whole-album acquisition in ALACarte.
- Local lossless FLAC replacing YouTube results after reopening the album.
- Accounts, preferences and playback surviving a Compose restart.

These are user-reported timings and observations, not instrumented benchmarks.
That installation used the earlier bundled Navidrome layout. Subsequent
standalone testing is recorded below; long-term use remains ongoing.

## Standalone 0.1.1 acceptance — 2026-09-08

The same tester subsequently installed Octocarte with an independently managed
Navidrome server and reported successful playback. After updating to `0.1.1`,
they confirmed:

- Multiple single-song downloads completed with `DOWNLOAD_WHOLE_ALBUM=false`.
- Playing downloaded songs used local files without another acquisition request.
- Switching to `DOWNLOAD_WHOLE_ALBUM=true` with `docker compose up -d` retained
  local playback without requesting the remainder of an album for an owned song.
- Playing an unowned song from the same album queued the album, and ALACarte
  correctly downloaded only the missing tracks.

These are user-reported live NAS results. Automated `0.1.1` verification passed
705 .NET tests, the HTTP playback/acquisition contracts in both download modes,
shim and ALACarte integration tests, and fresh container installation checks.
The real downloader started successfully in both modes before publication and
again after pulling the release images. Those automated downloader checks use
no Apple credentials and do not substitute for the live results above.

## Limitations

Wavio prefetching can request lossy Opus for ALAC; disabling prefetching resolved
that report. The user subsequently selected lossless FLAC in ALACarte. Navic
playback was subsequently confirmed working after an earlier failed trial. See
[client notes](../CLIENTS.md).

## Standalone cleanup candidate

Candidate `0.0.5-standalone.2`, built from `31e8f36`, passed the standalone
container test with all five freshly built images. The unauthenticated ALACarte
source download matched the emitted archive byte for byte; source notices and
licenses were present, and app/shim/ALACarte image license files were verified.
The HTTP streaming/acquisition fixture and all pull-request CI jobs passed.

A separate disposable migration exercise started the original alpha Navidrome
service and initializer from the release-tag Compose file, created an account
and playlist, stopped that server and attached its data volume to a separately
named Navidrome project using an external volume. The original account and
playlist remained available. Stopping the new server and starting the original
container also retained both, validating the documented rollback. Only temporary
containers and volumes were used; this was not a migration of the user's NAS.
