# Separate Navidrome from the earlier full-stack install

This applies only to installations made with the bundled `v0.0.5-alpha.1`
Compose file. New installations connect to an existing Navidrome server.
The earlier `nas-preview.2` offline bundle used different bind-mounted storage;
its archived instructions remain in that release's source and Git history.

Do not replace a working full-stack Compose file and run `--remove-orphans`.
The new file no longer defines Navidrome. First move that service to its own
Compose project while retaining its database, music path and account settings.
The running installation does not need to be changed just to read this guide.

## 1. Save the working configuration

Keep private copies of the current Compose file and `.env` outside the checkout.
Back up service data and music using your existing backup process. Pause downloads
and stop services while taking database backups. Restart them after the backup.
Record Navidrome's current image, user/group, port binding, environment and mounts:

```sh
docker inspect octocarte-navidrome-1 --format '{{.Config.Image}} {{.Config.User}}{{range .Mounts}}{{printf "\n%s %s -> %s" .Type .Source .Destination}}{{end}}'
docker volume inspect octocarte_navidrome-data
```

The default bundled installation uses `octocarte_navidrome-data`. If you used a
different project name or storage layout, use the actual volume or bind mount.
Do not proceed with an empty replacement database.

## 2. Prepare an independent Navidrome project

Create a separate directory outside the Octocarte checkout. In it, save a
`compose.yml` that retains the old service's image, user/group, environment,
ports and music mount. For the unmodified alpha defaults, the template is:

```yaml
name: navidrome
services:
  navidrome:
    image: deluan/navidrome:0.63.2
    user: "${NAVIDROME_UID:-1000}:${NAVIDROME_GID:-10}"
    restart: unless-stopped
    ports:
      - "${HOST_BIND:?Set your existing LAN binding}:4533:4533"
    environment:
      ND_LOGLEVEL: info
      ND_ENABLEINSIGHTSCOLLECTOR: "false"
    volumes:
      - existing-data:/data
      - type: bind
        source: ${MUSIC_DIR:?Set your existing music folder}
        target: /music
        read_only: true
        bind: {create_host_path: false}
volumes:
  existing-data:
    external: true
    name: octocarte_navidrome-data
```

Create this project's `.env` with your existing `HOST_BIND` and `MUSIC_DIR`.
Carry over any non-default user/group, port or environment settings. The external
volume declaration reuses the database and fails if that volume does not exist.

## 3. Transfer only Navidrome

Stop the old Navidrome container, then start the new project from its directory:

```sh
docker stop octocarte-navidrome-1
docker compose up -d
```

Open Navidrome directly at its existing address. Confirm your original account,
library and playlists are present. A fresh-account setup screen means the wrong
database was selected: stop the new Navidrome and start the original container
with `docker start octocarte-navidrome-1`, then correct the volume mapping.
Never run both instances against the same database simultaneously.

## 4. Point Octocarte and ALACarte at it

In Octocarte's existing `.env`, set `NAVIDROME_URL` to the independent server's
reachable LAN URL. The old `http://navidrome:4533` name will not resolve across
separate default Docker networks. Change ALACarte's saved scan URL in its normal
UI to the same reachable address; its existing scan credentials remain valid.

After confirming the independent Navidrome works, remove only its stopped old
container (no volume deletion):

```sh
docker rm octocarte-navidrome-1
```

Now update Octocarte's checkout/configuration, retaining its `.env` and the
`octocarte` project name, and start it with `docker compose up -d`. Confirm client
login, local playback, an unowned album acquisition, automatic scan and restart
persistence before removing configuration backups. Navidrome is now managed from
its own directory; routine Octocarte commands no longer manage it.
