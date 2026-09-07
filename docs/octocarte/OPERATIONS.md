# Operations

The standard installation uses named volumes for Navidrome data (full stack
only), Octocarte state, ALACarte configuration, wrapper login data, the integration
token and yt-dlp cache. Docker prefixes their names with the Compose project name.
Music lives in the separate host folder configured by `MUSIC_DIR`.

Keep the same project name and configuration when restarting or upgrading.
Changing project names selects new volumes and can look like a fresh installation.
Back up service volumes and music while downloads are idle and the stack is
stopped. Keep backups private; ALACarte and wrapper volumes contain credentials.

Use `docker compose ps -a` for status. The initializer exits successfully after
setup. `docker compose down` removes containers/network and retains named volumes
and bind-mounted music. Adding `--volumes` deletes named service state and must
not be used for a routine restart or upgrade.

For an upgrade, retain the previous Compose configuration and image version,
back up data, choose the new `OCTOCARTE_VERSION` in `.env`, then run:

```sh
docker compose pull
docker compose up -d
```

Read release notes first. Rollback selects the previous image version and may
require restoring the corresponding database backup after schema changes.
The same workflow applies to the existing-Navidrome example with both `-f` files.

The initializer retains an existing valid token. An empty, malformed or unreadable
token stops initialization rather than silently replacing a credential. The token
volume is mounted read-only by Octocarte and ALACarte. For deliberate rotation or
revocation, see the service-auth contract in `integrations/alacarte/SERVICE_AUTH.md`;
use the dedicated integration volume, never ALACarte's master-secret directory.

## Migrating the early NAS bundle

The earlier `nas-preview.2` bundle uses host bind directories and `manage.sh`.
The new standard installation uses named volumes. It is not an in-place migration
of that bundle: starting the new file under an existing project name must not be
used as a shortcut to move state. Keep the working NAS installation running until
a migration has been planned and its ALACarte credentials, Navidrome database and
integration token backed up. New installations use the short root README flow.

The old bundle remains available for rollback. Its image-ID repair uses the
versioned names recorded in `images.lock.json`; no service or music deletion is
needed for that repair.
