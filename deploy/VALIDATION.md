# Compose package validation

Validated on 2026-09-07 using Docker Engine 29.7.2 and Docker Compose 5.5.1,
Linux AMD64. The five images were built from committed Octocarte source and
pinned ALACarte source with all included patches. No pre-existing service image
or container was replaced during validation.

## Passed checks

- Compose configuration: shared music source, Navidrome read-only mount, private
  token-directory mounts, no shim/wrapper host ports, exact wrapper image
  selection, and no music or Docker-socket mount in Octocarte.
- Initialization: private token generation, repeated initialization retains the
  token and existing data, malformed existing tokens and secret-directory
  symbolic links are rejected.
- Fresh five-service startup using isolated names, ephemeral loopback ports,
  generated accounts and temporary state. The ALACarte Docker socket was replaced
  with a harmless file to prevent the test from managing other containers.
- Real Apple catalog search, artist image metadata and ranked top songs through
  Octocarte, using the automatically configured service token.
- A generated silent ALAC file in the shared library was indexed by real
  Navidrome and played through Octocarte with HTTP 206 and correct Content-Range.
- ALACarte and Octocarte restarted successfully; the existing integration token,
  catalog access and top songs survived.
- The existing HTTP integration fixture passed with the packaged Octocarte image:
  immediate temporary streaming, independent whole-album submission, debounce,
  local replacement, old-placeholder playback, image/top-songs mapping and ranges.
- A separate disposable ALACarte instance passed real catalog access, restricted
  administrative access, restart, atomic token rotation and revocation.
- GitHub CI passed .NET/build/HTTP checks, shim tests and the patched ALACarte
  catalog/authentication tests.

The disposable services, generated credentials and temporary library were removed.

## What remains

UGOS installation, Apple sign-in through its Docker socket, real album acquisition
on NAS storage, and sustained daily use still need NAS acceptance. Apple sign-in
and album acquisition were not repeated during this packaging check. Their
existing implementations remain in ALACarte; the earlier real acquisition/Wavio
results are recorded in the Octocarte source at `docs/octocarte/VALIDATION.md`.

This is an installation and integration check, not a claim of complete security
coverage or long-term reliability. Each package's `images.lock.json` identifies
its exact images and source revisions; retain it with the image archive.
