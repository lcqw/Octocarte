# Octocarte

Apple Music discovery for your Navidrome library.

Search artists, albums and songs from your usual Subsonic app. Play something
new and Octocarte starts a YouTube stream while ALACarte downloads the whole
album. Once Navidrome scans it, your local lossless tracks take over.

- Artist photos, discographies and top songs.
- Whole-album downloads in ALAC or lossless FLAC, with artwork and lyrics.
- Your existing Navidrome library and login.

## Requirements

- An existing Navidrome server and access to its music folder.
- A Linux x86-64 host with Docker and Docker Compose v2 or newer.
- An Apple Music subscription.

## Install

Current images are private. [Sign in to GitHub first](docs/development/PRIVATE_PREVIEW.md).

```sh
git clone https://github.com/Vixxy0w0/Octocarte.git
cd Octocarte
cp .env.example .env
nano .env
```

Set these three values in `.env`:

```dotenv
NAVIDROME_URL=http://192.168.1.100:4533
MUSIC_DIR=/path/to/your/music
HOST_BIND=192.168.1.100
```

Use your Navidrome address, your music folder and the LAN address of the machine
running Octocarte. Navidrome must read the same files that ALACarte writes.

```sh
docker compose up -d
```

1. Open **`http://YOUR_HOST:7373`** for ALACarte. Create its login, sign into Apple
   and choose your download preferences. If it asks for a setup token, see
   [first login](docs/SETUP.md#first-login).
2. Enable Navidrome integration in ALACarte using your Navidrome address and scan
   credentials.
3. Point your music app at **`http://YOUR_HOST:5274`**, using your Navidrome login.

Artist photos, top songs and service authentication are included automatically.
Octocarte connects to your server; it does not install or manage Navidrome.

## Good to know

Temporary playback uses YouTube AAC/M4A. After download and scanning, playback
uses your library's real format and quality. ALACarte handles download settings,
lyrics, duplicate detection and partially downloaded albums.

Keep ALACarte's web UI on your trusted network; its Apple sign-in flow needs
access to Docker. If using Caddy, point it at Octocarte's address and port.

**Status:** early alpha, tested end to end with Wavio. See [client notes](docs/CLIENTS.md)
for known limitations. [Setup help](docs/SETUP.md) · [Updating and backups](docs/OPERATIONS.md)
· [Migrating the earlier full-stack install](docs/MIGRATION.md).

## Credits

Built on [Octo-Fiesta](https://github.com/V1ck3s/octo-fiesta), with YouTube streaming
adapted from [Octo](https://github.com/winters27/octo) and Apple Music provided by
[ALACarte](https://github.com/sosjalapeno/alacarte).

Octocarte is GPLv3 software. ALACarte remains a separate AGPLv3 service.
See [LICENSE](LICENSE), [attribution](NOTICE.md) and [contributing](.github/CONTRIBUTING.md).
