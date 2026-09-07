# Unattended ALACarte authentication

The [complete package](../../README.md) provisions this credential
automatically. These details are for maintenance and existing-service migrations.
The original Wavio-validated deployment used a cookie; its running services are
not changed by building or merging the new package.

## Contract

The image build applies `top-songs.patch`, then `service-auth.patch`, to ALACarte revision
`ef9b677c21b024a0acbf4f88d47c4ebff24802fa`. The patches remain separate
AGPL-3.0-only extensions to ALACarte. No Apple authentication or acquisition
implementation is copied into Octocarte.

A random 256-bit service token authorizes only:

- `GET /api/search`
- `GET /api/album/:numericId`
- `GET /api/artist/:numericId`
- `GET /api/artist/:numericId/top-songs`
- `POST /api/download` with exactly `{"albumId":"numericId"}`

The token does not grant access to settings, queue/library administration,
per-song or playlist downloads, cancellation, or preference overrides. The
existing Origin check still applies to writes. ALACarte's browser sessions and
Apple credentials keep their existing behavior. A service token is a separate
credential; browser logout or password changes do not revoke it.

Tokens have no scheduled expiration. Rotate or revoke them explicitly. ALACarte
rereads the configured file for every bearer-authenticated request; missing,
empty, malformed or unreadable files reject access. Rejected bearer tokens
never fall back to a browser cookie. Already accepted requests can finish after
revocation. Cached catalog metadata in Octocarte is not purged by revocation.

## Manual provisioning for existing services

The standard Compose installation creates and retains its token in the
`integration-auth` named volume automatically. The steps below are only needed
when connecting independently managed services.

Generate a dedicated secret without printing its value:

```sh
python3 scripts/create-alacarte-token.py ./secrets/alacarte-integration/token
```

The helper creates a mode-600 file containing a 43-character base64url token,
creates a new parent directory with mode 700, and refuses to overwrite an
existing file. Keep the directory outside Git and readable only by the intended
container accounts. It must not be ALACarte's `/config` or master-secret folder.

Mount this dedicated directory read-only into both containers at
`/run/octocarte-auth`. Configure:

| Service | Environment variable | Value |
|---|---|---|
| Octocarte | `Alacarte__ServiceTokenFile` | `/run/octocarte-auth/token` |
| ALACarte web | `OCTOCARTE_TOKEN_FILE` | `/run/octocarte-auth/token` |

For each service, the relevant Compose bind mount is:

```yaml
volumes:
  - type: bind
    source: ./secrets/alacarte-integration
    target: /run/octocarte-auth
    read_only: true
    bind:
      create_host_path: false
```

Use the same absolute host directory when the services belong to different
Compose projects. These manual additions are only for existing-service migrations; the complete
package already includes them. Remove the old cookie mount and cookie setting when migrating
that deployment to token authentication. Octocarte gives ServiceTokenFile
priority if both settings exist. Cookie-only deployments remain compatible.

Mounting the directory matters: replacing or deleting its token file becomes
visible inside both containers. A bind mount of the individual file, including
some Compose secret-file configurations, can retain the old inode after atomic
replacement; recreate the containers to remount such a file. Rotation can
briefly reject requests while the two services observe the change.

Keep the ALACarte connection on a trusted container network, or use authenticated
HTTPS for a connection across hosts. The token is carried in Authorization,
never query parameters. Octocarte disables redirects on this client and suppresses
HTTP-client logging. Do not publish the ALACarte or shim endpoints through the
music client's public reverse proxy.

## Lifecycle and rollback

The token file survives container replacement as deployment-owned state.
To rotate it, generate a replacement file and atomically rename it to `token` in
the dedicated mounted directory. To revoke it, remove that file. New clients in
Octocarte reread it, and ALACarte validates it on each API request.

Rolling back means selecting the previous images and their matching configuration. Do not reuse ALACarte's master secret to mint cookies
or service tokens. This feature only addresses Octocarte-to-ALACarte access;
Apple may still require a new login or renewed media-user-token independently.

## Validation

The focused tests cover endpoint/method/body boundaries, invalid and expired
credentials, browser-session compatibility, Origin enforcement, rotation and
revocation. The full streaming fixture runs in both cookie-compatible and
service-token modes, including local playback/search when ALACarte is unavailable.
A disposable full ALACarte container checks real catalog access, restart,
atomic rotation and revocation without user credentials or album downloads.
