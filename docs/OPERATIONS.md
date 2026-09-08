# Updating and backups

Octocarte manages its own containers and Docker volumes. Navidrome is managed
separately. Music stays in `MUSIC_DIR`; service state lives in the `octocarte-state`,
`alacarte-data`, `wrapper-data`, `integration-auth` and `ytdlp-cache` volumes.
Docker prefixes these names with the Compose project name.

Keep that project name when updating. Changing it selects new volumes and can
look like a fresh installation. Never replace your `.env` with the example when
updating an existing installation.

## Updates

Read the release notes first. Stop active downloads and back up the music and
service volumes, with services stopped for a consistent backup. Keep backups
private: ALACarte and wrapper state contain credentials. Back up Navidrome through
its own deployment's backup process.

Install the release's configuration changes and select its image version using
`OCTOCARTE_VERSION` in `.env`, then run:

```sh
docker compose pull
docker compose up -d
```

The earlier release that bundled Navidrome needs the [migration procedure](MIGRATION.md)
before updating its Compose file. A routine update must not orphan or recreate
that Navidrome server unexpectedly.

## Repository address change

The repository is now `lcqw/Octocarte`, and images are under
`ghcr.io/lcqw/octocarte`. Existing containers keep running. In your existing
checkout, update the remote and installation files:

```sh
git remote set-url origin https://github.com/lcqw/Octocarte.git
git pull --ff-only
```

If your `.env` defines `OCTOCARTE_IMAGE_BASE`, change it to
`ghcr.io/lcqw/octocarte`. Otherwise the updated Compose file selects it
already. Then follow the normal update commands above, keeping your `.env`,
project name and volumes. The `0.0.6` images themselves are unchanged.

Older release attachments retain their original addresses and checksums. To use
one of those Compose files, set `OCTOCARTE_IMAGE_BASE=ghcr.io/lcqw/octocarte` in
`.env`; this also updates ALACarte's wrapper image address.

## Restart and removal

```sh
docker compose restart
docker compose ps -a
```

`docker compose down` removes Octocarte's containers and network but retains its
volumes and music. Adding `--volumes` deletes service state and is not a routine
restart or upgrade operation. Do not use `--remove-orphans` when an older bundled
Navidrome container still belongs to the project.

Keep the previous configuration and image versions for rollback. Database changes
may require restoring the matching backup as well as selecting older images.
No installed image version is silently replaced by the release workflow.

## Authentication

The integration token survives container replacement and has no scheduled expiry.
Apple sign-in and lyrics credentials remain under ALACarte's control. For service
token rotation/revocation, see the [authentication contract](../integrations/alacarte/SERVICE_AUTH.md).
Never use ALACarte's master secret as an integration token.
