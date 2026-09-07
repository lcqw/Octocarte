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

Open ALACarte at `http://YOUR_HOST:7373`. If the welcome screen asks for a one-time
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

## Ports and access

| Setting | Default | Purpose |
|---|---|---|
| `HOST_BIND` | `127.0.0.1` | Bind to your LAN address for access from other devices |
| `OCTOCARTE_PORT` | `5274` | Subsonic/OpenSubsonic clients |
| `ALACARTE_PORT` | `7373` | ALACarte administration |

If Octo-Fiesta already uses port 5274, stop it or choose another Octocarte port.
Keep the administration UI on a trusted network. ALACarte's Docker socket access
allows it to manage its wrapper and grants control of the Docker host. The shim
and wrapper publish no host ports.

For connection errors, check `docker compose ps -a`, the Navidrome URL, and the
host's firewall. Private-image authentication is covered in the
[private preview guide](development/PRIVATE_PREVIEW.md).
