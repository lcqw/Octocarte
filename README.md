# Octocarte

---

Apple Music discovery and album downloads for your Navidrome library, built on
[Octo-Fiesta](https://github.com/V1ck3s/octo-fiesta),
[ALACarte](https://github.com/sosjalapeno/alacarte) and
[Octo](https://github.com/winters27/octo).

**Note: An Apple Music subscription is required.**

**Features**

---

- **Apple Music search:** Search Apple Music's artists, albums and songs alongside your local library from your usual Subsonic client, using ALACarte's catalog search and Octo-Fiesta's client support.
- **Artist pages:** Browse artist photos, discographies and Apple-ranked top songs. Octocarte's ALACarte integration includes these automatically, with no extra extensions to install.
- **Listen while downloading:** Play a song you don't have yet and a temporary YouTube stream starts while ALACarte downloads its whole album in the background. Playback uses the streaming system adapted from Octo, including seeking support. The temporary stream is AAC/M4A, not lossless.
- **Lossless albums:** ALACarte downloads complete albums in ALAC or lossless FLAC, with artwork, metadata and optional lyrics. Choose your quality and other download preferences in its web UI.
- **Local playback takes over:** After ALACarte triggers a Navidrome scan, Octocarte matches the downloaded tracks to your library. Later searches and playback use the local lossless files.
- **Library-aware downloads:** ALACarte reuses queued album jobs, skips albums already in your library and downloads only missing tracks from partially downloaded albums.

**Disclaimer**

---

**Octocarte is intended for personal archival use.** Downloading through third-party
tools may violate [Apple's Terms of Service](https://www.apple.com/legal/internet-services/itunes/),
even with a subscription. You are responsible for following applicable service
terms and the laws in your jurisdiction.

**Quick start**

---

Requires an existing Navidrome server and a Linux x86-64 host with Docker and
Docker Compose v2 or newer.

```sh
git clone https://github.com/Vixxy0w0/Octocarte.git
cd Octocarte
cp .env.example .env
nano .env
```

In `.env`, replace `<navidrome-host>` with your Navidrome server's address and
adjust its port if needed. Set `MUSIC_DIR` to the music folder on this machine
that Navidrome reads. Replace `<octocarte-host-ip>` with the LAN IP of the machine
running Octocarte. Both hosts can be the same machine.

```dotenv
NAVIDROME_URL=http://<navidrome-host>:4533
MUSIC_DIR=/path/to/your/music
HOST_BIND=<octocarte-host-ip>
```

Save the file, then start Octocarte:

```sh
docker compose up -d
```

Open `http://<octocarte-host-ip>:7373` for ALACarte. Grab the one-time setup token
from `docker compose logs alacarte` and enter it on the welcome screen.
See [first login](docs/SETUP.md#first-login) for help.

Create your ALACarte login, sign into Apple and choose your download preferences.
Enable Navidrome integration in ALACarte with your Navidrome address and scan
credentials.

Point your Subsonic client to **`http://<octocarte-host-ip>:5274`** and use your
existing Navidrome login. If using Caddy, point it at this address and port too.

[Setup help](docs/SETUP.md) · [Updating and backups](docs/OPERATIONS.md) · [Client notes](docs/CLIENTS.md)

---

Octocarte is licensed under [GPLv3](LICENSE). ALACarte runs as a separate
[AGPLv3](integrations/alacarte/LICENSE) service. See [attribution](NOTICE.md)
and [contributing](.github/CONTRIBUTING.md).
