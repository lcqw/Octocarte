# Connect existing services

This advanced deployment runs only Octocarte and its YouTube shim. The
[complete package](../../deploy/README.md) includes Navidrome and a prepared
ALACarte image with top songs and service authentication; choose that for a new installation.

Stock ALACarte supports artist photos through its existing API. Apple-ranked top
songs and the scoped service token require the prepared ALACarte image. When
using stock ALACarte, the adapter falls back to Navidrome top songs and a browser
session cookie must be refreshed when it expires. These are compatibility limits
of the external-service setup, not extra steps in the complete installation.

## Cookie-compatible setup

1. Keep your existing ALACarte and Navidrome services running. ALACarte owns all
   Apple settings, credentials, library management and Navidrome scans. Its music
   output must be visible to Navidrome: use the same shared storage when they run
   on different machines. A scan cannot transfer files between hosts.
2. Copy `.env.octocarte.example` to `.env.octocarte` and set the three connection
   values. A container cannot reach host ALACarte using `127.0.0.1`; use
   `http://host.docker.internal:7373` on this Linux host.
3. Put only the `alacarte_session` cookie **value** in the secret file referenced
   by `ALACARTE_COOKIE_FILE`; use mode `600`. For this installation the file is
   `./secrets/alacarte-cookie` (or another local secret-file path). Octocarte reads it when
   constructing ALACarte clients. After rotating the file, recreate the service
   with `docker compose --env-file .env.octocarte -f compose.octocarte.yml up -d --force-recreate octocarte`
   so an atomically replaced file is remounted. Never commit its contents.
   Never use ALACarte's master `.secret`. An empty file works only when ALACarte
   already uses its own externally managed authentication configuration.
4. Run:

   ```sh
   docker compose --env-file .env.octocarte -f compose.octocarte.yml up -d --build
   ```

5. Point Wavio at port `5880` on the Octocarte host, using your normal Navidrome
   client credentials. The default bind is loopback. Set `OCTOCARTE_BIND` to your
   private LAN interface address if Wavio runs on another device.

The shim has no published host port or music-library mount. Octocarte mounts
only its own state volume, not ALACarte's music or configuration directories.
No Navidrome administrator credentials are needed in Compose; the chassis
validates client credentials with Navidrome and uses them for local lookups.


For an existing ALACarte installation using the prepared image, use the
[service-token configuration](../../integrations/alacarte/SERVICE_AUTH.md) instead
of a cookie. Back up its data and change images while its download queue is idle.
