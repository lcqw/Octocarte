# Octocarte

Octocarte connects a Subsonic/OpenSubsonic music client to Navidrome and ALACarte.
Search Apple's catalog, play an unowned track through temporary YouTube AAC/M4A,
and let ALACarte acquire its whole album in the background. Once Navidrome indexes
the files, local tracks take precedence.

Artist photos, ranked top songs and unattended service authentication are included.
ALACarte owns Apple sign-in, download preferences, metadata, lyrics, artwork,
library management and Navidrome scans.

**Status:** `0.0.5-alpha.1` is an early prerelease. The NAS end-to-end workflow has
passed user acceptance; long-term daily-use testing is ongoing. This repository
and its images remain private during preparation. Authorized testers need
[private registry access](docs/octocarte/PRIVATE_PREVIEW.md); no public availability
is implied by the examples below.

## Install

Requires an AMD64 Linux Docker host with Docker Compose v2 or newer, an existing
music folder, and an Apple account suitable for your ALACarte setup.

```sh
git clone https://github.com/Vixxy0w0/Octocarte.git
cd Octocarte
cp .env.example .env
nano .env
docker compose up -d
```

Set `MUSIC_DIR` to your music folder's absolute path. Set `HOST_BIND` to your NAS's
private LAN address if connecting from another device. The other settings have
defaults. Compose downloads the versioned images and initializes service storage
and authentication automatically.

Then finish account setup:

1. Open `http://HOST:4533` and create your Navidrome account.
2. Open `http://HOST:7373`, create an ALACarte UI login, sign into Apple and save
   your download/lyrics preferences. ALAC or lossless FLAC output is your choice.
3. In ALACarte, enable Navidrome integration with `http://navidrome:4533` and that
   server's scan credentials.
4. Connect Wavio or another client to `http://HOST:5274` using your Navidrome login.

The initializer showing **Exited (0)** is normal: it finishes its job and stops.
The wrapper may stop until Apple sign-in is completed in ALACarte.

Already running Navidrome? Use the [existing-Navidrome example](docs/octocarte/EXISTING_NAVIDROME.md)
to add Octocarte to its Compose project. On UGOS, the same Compose file and `.env`
values can be supplied through the Docker project UI.

If using Caddy, point it at Octocarte's address and port instead of Navidrome
(`octocarte:8080` on a shared Docker network).

## Storage and operation

ALACarte writes to `MUSIC_DIR`; Navidrome reads the same folder. Ensure its
container user can read that folder. The default Navidrome user/group is
`1000:10`; advanced installations can set `NAVIDROME_UID` and `NAVIDROME_GID`.

Docker-managed volumes hold service databases, Apple login state and the private
integration token. `docker compose down` retains them. **Do not add `--volumes`
unless you intend to delete that service state.** Back up the volumes and music
before upgrades. See [operations](docs/octocarte/OPERATIONS.md).

ALACarte's administration UI belongs on a trusted network: its existing Apple
sign-in flow needs the Docker socket to manage its wrapper. ALACarte expects one
`alacarte-wrapper` container per host. The shim and wrapper publish no host ports.

## Behavior and compatibility

- Temporary external results describe AAC/M4A, never ALAC or Hi-Res. Indexed
  tracks use Navidrome's native metadata and normal client-requested transcoding.
- Album submission runs independently of playback. ALACarte handles persistent
  duplicate detection and partial-album completion; Octocarte uses a short
  in-memory guard and treats already-present albums as a normal no-op.
- Apple lyrics credentials and account renewal remain under ALACarte's control.
  The separate integration token has no scheduled expiration.
- Wavio's Android prefetching can request lossy Opus for ALAC. Disabling prefetching
  resolved that behavior in the NAS trial; FLAC is another lossless compatibility
  option. See [client notes](docs/octocarte/CLIENTS.md).
- Soulseek/slskd is not included. External playlist acquisition is outside this
  release. Inherited Deezer, Qobuz, Tidal, Yandex and SquidWTF code remains, but
  those providers have not received Octocarte end-to-end acceptance testing.

## Development and attribution

See [CONTRIBUTING.md](CONTRIBUTING.md), [workflow validation](docs/octocarte/VALIDATION.md),
[deployment validation](deploy/VALIDATION.md) and [release notes](docs/releases/0.0.5-alpha.1.md).
Changes use branches and pull requests. The validated baseline is preserved at
`mvp-validated-2026-09-07`.

Octocarte derives from Octo-Fiesta and adapts YouTube streaming components from
Octo. ALACarte stays a separate service with small maintained integration patches.
See [NOTICE.OCTOCARTE.md](NOTICE.OCTOCARTE.md), [LICENSE](LICENSE), the
[ALACarte integration](integrations/alacarte/README.md), and the preserved
[upstream README](README.UPSTREAM.md).
