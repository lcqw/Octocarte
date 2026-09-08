# Setup help

## Navidrome connection

Use a LAN address reachable from the Octocarte container. `localhost` and
`127.0.0.1` inside a container refer to that container. A Docker service name
works only when both services share a Docker network.

For a separate host, mount the shared music storage on the Octocarte host and
set `MUSIC_DIR` to that mount. A Navidrome scan does not transfer files. Ensure
Navidrome's user can read the files ALACarte creates.

The default install runs in its own `octocarte` Compose project. Users comfortable
with Compose can merge its service and volume entries into an existing project;
include `x-logging` and retain the existing project name. Do not replace existing
service definitions. One ALACarte wrapper named `alacarte-wrapper` is supported
per Docker host.

## First login

Open ALACarte at `http://<octocarte-host-ip>:7373`. If the welcome screen asks for a one-time
setup token, retrieve it locally with:

```sh
docker compose logs alacarte
```

Enter that token in ALACarte's welcome screen. Do not share these logs or paste
credentials into issues. Complete Apple sign-in in ALACarte and save its download,
artwork and lyrics preferences. Lyrics use your Apple media-user-token, managed
only by ALACarte. Enable Navidrome scans there with the existing server's URL and
scan credentials.

The `initialize` container showing **Exited (0)** means setup succeeded. The
wrapper can exit before Apple sign-in is completed. After sign-in, check ALACarte's
connection status if acquisition is unavailable.

## Download quality

ALACarte offers **FLAC, ALAC, Dolby Atmos and AAC** in its settings. The default is
**FLAC**: ALACarte downloads Apple Lossless audio and converts it to FLAC without
losing audio quality. Select ALAC to retain the original lossless format, AAC for
smaller lossy files, or Dolby Atmos for releases that offer it. Atmos playback
requires a compatible client and device.

Octocarte uses ALACarte's saved choice. Changing the setting affects future
downloads; it does not convert albums already in your library.

## Lyrics

**Your Apple `media-user-token` is required for lyrics.** Grab the raw cookie value
from [music.apple.com](https://music.apple.com/) → DevTools → Application → Cookies.

1. Sign into Apple Music in Chrome or Edge, then open the browser's developer tools.
2. Under **Application → Cookies → https://music.apple.com**, find
   `media-user-token` and copy its **Value** only.
3. In **ALACarte → Settings → media-user-token**, paste the value and save it.
   Enable **Download lyrics** and choose **LRC** for line-synced lyrics.

Lyrics depend on availability for the track. Keep the token in ALACarte's settings;
do not put it in `.env`, Compose files, screenshots or issue reports. If Apple
rejects it later, replace it with the current value from your signed-in browser.

## Ports and access

| Setting | Default | Purpose |
|---|---|---|
| `HOST_BIND` | Set in `.env` | Use this machine's LAN IP, or `127.0.0.1` for local access only |
| `OCTOCARTE_PORT` | `5274` | Subsonic/OpenSubsonic clients |
| `ALACARTE_PORT` | `7373` | ALACarte administration |

If Octo-Fiesta already uses port 5274, stop it or choose another Octocarte port.
Keep the administration UI on a trusted network. ALACarte's Docker socket access
allows it to manage its wrapper and grants control of the Docker host. The shim
and wrapper publish no host ports.

For connection errors, check `docker compose ps -a`, the Navidrome URL, and the
host's firewall.


## Download scope

Full-album downloads are the default. To download only the requested song, set
this in Octocarte's `.env`:

```dotenv
DOWNLOAD_WHOLE_ALBUM=false
```

Apply the setting with `docker compose up -d`. To restore album downloads, set
it to `true` and run the same command. This preference applies to all clients.
Existing installations that omit it continue downloading whole albums.

Playback still starts through YouTube while ALACarte handles the download,
quality, tagging, duplicate checks and Navidrome scan. Changing this preference
does not cancel jobs ALACarte has already accepted or remove existing music.
A client's prefetch requests can also trigger acquisition.

When configuring Octocarte without the supplied Compose file, use the container
environment variable `Alacarte__DownloadWholeAlbum=false` instead. Custom
installations need an ALACarte integration image from the same Octocarte release,
which permits the existing single-song download endpoint.
