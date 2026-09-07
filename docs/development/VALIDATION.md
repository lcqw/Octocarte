# Validation

## Automated evidence

The `v0.0.5-alpha.1` release passed 692 .NET tests, the controlled HTTP streaming
fixture, clean full-stack installation and existing-Navidrome integration tests.
Five images were published privately to GHCR, downloaded again and tested with
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
That installation used the earlier bundled Navidrome layout; it does not establish
that the new standalone migration has been run on the user's NAS. Their running
installation was not changed by repository cleanup. Long-term use remains ongoing.

## Limitations

Wavio prefetching can request lossy Opus for ALAC; disabling prefetching resolved
that report. The user subsequently selected lossless FLAC in ALACarte. Navic
playback had an unresolved compatibility report. See [client notes](../CLIENTS.md).
Public image redistribution remains subject to the [license review](LICENSING.md).
