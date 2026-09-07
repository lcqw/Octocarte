# Complete Compose installation

This package includes **artist photos, Apple-ranked top songs and unattended
Octocarte-to-ALACarte authentication**. It runs five services in one Compose
project: Octocarte, Navidrome, the YouTube shim, ALACarte and its wrapper. Users
complete normal account setup; no extensions need to be installed afterward.

Status: private NAS preview. The earlier Wavio workflow is validated; this
deployment passed a fresh isolated Compose check and still needs the NAS daily-use
trial. See [package validation](VALIDATION.md). Public images are not published.
The package carries exact local images and their source so the NAS can load them
without Git, Python or a compiler. It targets Linux AMD64 because the upstream
ALACarte downloader and wrapper require it.

## Prepare the private package

On a development machine with Git, Python 3.12+ and Docker/Compose, from a clean
Octocarte checkout:

```sh
python3 scripts/build-compose-package.py --version nas-preview.1 --output ../octocarte-nas-preview.1
```

This builds distinct images, applies the included ALACarte changes automatically,
and writes a transferable directory containing `images.tar`, `images.env`,
`images.lock.json`, Compose files, setup helpers, source archives and checksums.
It does not start services or publish anything. Choose a new version for each
build; the helper refuses to overwrite existing candidate image tags. A local ALACarte Git checkout can
be supplied with `--alacarte-source /path/to/alacarte` to avoid downloading it
again; only the pinned committed revision is read.

Every base image is resolved to a registry digest before building. The manifest
records those digests, source revisions and resulting image IDs. Runtime Compose
uses the image IDs directly and never pulls a replacement. OS package repositories
can still change between builds; the image archive is the exact tested artifact,
not a claim of bit-for-bit reproducible builds at a later date.

## Install on the NAS

Copy the complete package directory onto the NAS. Run these commands in that
directory using an account permitted to manage Docker (use `sudo` if required):

```sh
sha256sum -c SHA256SUMS
docker load -i images.tar
cp settings.env.example settings.env
```

Edit `settings.env` before continuing:

| Setting | Purpose |
| --- | --- |
| `DATA_DIR` | New, absolute directory for Octocarte's service data, such as `/volume2/docker/octocarte`. Keep it outside the package directory. |
| `MUSIC_DIR` | Existing, absolute music directory, such as `/volume1/Media/Music`. ALACarte writes here; Navidrome reads the same folder. |
| `HOST_BIND` | NAS private LAN address for phone and administration access. The default is loopback. |
| `NAVIDROME_UID` / `NAVIDROME_GID` | Account that can read the music directory. Defaults are `1000:10`; initialization assigns new Navidrome data to this account. |
| Ports | Defaults: Octocarte `5274`, Navidrome `4533`, ALACarte `7373`. |

The music directory must already exist and be readable by Navidrome. ALACarte
retains its upstream container user; verify NAS permissions allow its writes and
Navidrome's reads. Do not apply the Navidrome UID setting to the ALACarte wrapper.
Initialization never recursively changes ownership of music or existing data.

For a replacement installation, stop the old Octo-Fiesta/Navidrome project before
starting this one if it uses those ports. Keep a copy of its Compose configuration
and data until the new setup works. Use a fresh `DATA_DIR`; do not delete music.
ALACarte expects the container name `alacarte-wrapper`, so only one ALACarte
installation can use this package on a Docker host at a time.

```sh
./manage.sh init
./manage.sh up
./manage.sh status
```

Initialization creates separate service directories and a random service token
with mode `600` inside a private directory. Existing valid tokens and service
data are retained. Both services mount only that token directory read-only for
integration authentication. No browser cookie or Apple master secret is used.

UGOS's Docker project UI can manage the same `compose.yml`. After initialization,
supply the values from both `images.env` and `settings.env` as the project's
environment (or combine them into its `.env` file). Use project name `octocarte`
and absolute host paths. The command-line helper is provided to make the first
private trial independent of differences between UGOS UI versions.

## Finish normal account setup

1. Open `http://NAS_ADDRESS:4533` and create your Navidrome account.
2. Open `http://NAS_ADDRESS:7373`, create the ALACarte UI login, and complete its
   normal Apple account setup. ALACarte handles Apple sign-in and 2FA through its
   existing wrapper flow.
3. In ALACarte, select your download preferences. For the tested workflow: US
   storefront, Prefer Explicit, ALAC, LRC lyrics with lyrics only, and 1400×1400
   artwork. Provide the lyrics media-user-token through ALACarte's normal UI.
4. Enable ALACarte's Navidrome integration with URL `http://navidrome:4533` and
   scan credentials for this Navidrome instance. Save those settings in ALACarte.
5. Connect Wavio to `http://NAS_ADDRESS:5274` using the Navidrome account. Photos
   and top songs are already included; play an unowned song to test streaming
   and whole-album acquisition, then verify later playback uses the local file.

ALACarte owns these saved preferences. Octocarte sends only the album ID and does
not maintain a second settings page or persistent duplicate index. Its service
token has no scheduled expiry; Apple can still require renewed login or media
credentials independently. Token rotation and revocation are described in the
included source at `integrations/alacarte/SERVICE_AUTH.md`.

If using Caddy, point its reverse proxy at the Octocarte address and port, instead
of Navidrome (`octocarte:8080` when sharing the Docker network).

Keep ALACarte's administration UI on a trusted network. Its existing Apple-login
implementation requires the Docker socket, which grants control of the host's
containers. The shim and wrapper have no published host ports.

## Data, upgrades and rollback

`DATA_DIR` contains `navidrome`, `octocarte`, `alacarte`, `wrapper`, `ytdlp-cache`
and `secrets`. Music is stored separately in `MUSIC_DIR`. Back up service data
and secrets securely; never include them in Git or a package shared with others.

`./manage.sh down` stops/removes the Compose containers and network and retains
all bind-mounted data and music. Stop downloads before planned shutdowns. A
wrapper login can briefly create `alacarte-wrapper-login`; finish or cancel
that login in ALACarte before shutting down. Removing the package directory
does not remove the library or service data. Delete trial data only after
checking the paths and deciding which music to retain.

For upgrades, retain the old package, stop the stack, back up its data, load the
new image archive, copy your settings and start the new package. Use the same
state and music paths. Rollback selects the previous package's images; restore
the corresponding data backup if an upgraded component changed its database.
Never move a validation tag or silently replace a package's image manifest.

The private package includes Octocarte source and modified ALACarte source with
their existing licenses. Review full history, artifacts and binary redistribution
requirements before any public release.
