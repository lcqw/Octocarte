#!/bin/sh
# Run from the package directory. Never sources user configuration as shell code.
set -eu
cd "$(dirname "$0")"
compose() { docker compose --env-file images.env --env-file settings.env -f compose.yml "$@"; }
case "${1:-}" in
  init)
    test -f settings.env || { echo 'Copy settings.env.example to settings.env and edit it first.' >&2; exit 1; }
    # Compose resolves paths and variables; a one-off service mounts no music or socket.
    docker compose --env-file images.env --env-file settings.env -f initialize.compose.yml run --rm initialize
    ;;
  up)
    # Avoid attaching this package to ALACarte from a different Compose project.
    owner=$(docker inspect alacarte-wrapper --format '{{index .Config.Labels "com.docker.compose.project"}}' 2>/dev/null || true)
    if [ -n "$owner" ] && [ "$owner" != octocarte ]; then
      echo 'Another ALACarte wrapper exists. Stop and remove that deployment before installing this package.' >&2
      exit 1
    fi
    compose up -d
    ;;
  down) compose down ;;
  status) compose ps -a ;;
  *) echo 'Usage: ./manage.sh init|up|down|status' >&2; exit 1 ;;
esac
