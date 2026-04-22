#!/bin/bash
# Daily backup script for VASTER webapp.
# Backs up the PostgreSQL database to Swift object storage and the media files
# volume using restic.
#
# Prerequisites:
#   - /opt/vaster/openrc.sh exists and contains OpenStack credentials with
#     OS_PASSWORD hardcoded (no interactive prompt)
#   - RESTIC_PASSWORD is set in /opt/vaster/openrc.sh or exported before calling
#     this script, OR passed via environment variable
#   - restic, python3-openstackclient, python3-swiftclient are installed
#   - The restic repository has been initialised:
#       source /opt/vaster/openrc.sh
#       RESTIC_PASSWORD=<password> restic -r swift:vaster-backups:/restic-media init
#
# Usage:
#   sudo /opt/vaster/backup/backup.sh
#   (or via cron — see IMPLEMENT_BACKUP.md)
#
# Configuration: edit the variables below to match your deployment.

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENRC=/opt/vaster/openrc.sh

DB_CONTAINER=ywangvaster-db
DB_USERNAME=ywangvaster
DB_NAME=ywangvaster

# Path on the host to the django_media bind mount (check docker-compose.volumes.yml)
MEDIA_PATH=/path/to/django_media

# Swift container name
SWIFT_CONTAINER=vaster-backups

# Restic repository (Swift container + path prefix)
RESTIC_REPO="swift:${SWIFT_CONTAINER}:/restic-media"

# Restic encryption password — override via environment or set here
# RESTIC_PASSWORD is already exported if set in openrc.sh; otherwise set it:
# export RESTIC_PASSWORD="your-restic-password"

# Number of daily DB dumps to keep in Swift
DB_RETAIN_DAYS=30

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

TIMESTAMP=$(date +%Y%m%dT%H%M%S)
LOGPREFIX="[vaster-backup $TIMESTAMP]"

log() { echo "$LOGPREFIX $*"; }
die() { echo "$LOGPREFIX ERROR: $*" >&2; exit 1; }

[[ -f "$OPENRC" ]] || die "OpenRC file not found at $OPENRC"
# shellcheck source=/dev/null
source "$OPENRC"

[[ -n "${RESTIC_PASSWORD:-}" ]] || die "RESTIC_PASSWORD is not set"
[[ -d "$MEDIA_PATH" ]] || die "MEDIA_PATH does not exist: $MEDIA_PATH"

log "Starting backup"

# ---------------------------------------------------------------------------
# Database — pg_dump piped directly to Swift
# ---------------------------------------------------------------------------

log "Dumping database to Swift..."
docker exec "$DB_CONTAINER" pg_dump \
    -U "$DB_USERNAME" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=9 \
    | swift upload "$SWIFT_CONTAINER" --object-name "db/vaster-$TIMESTAMP.pgdump" -

log "Database dump complete"

# Prune old dumps, keeping the most recent DB_RETAIN_DAYS
log "Pruning DB dumps older than $DB_RETAIN_DAYS days..."
DUMPS_TO_DELETE=$(swift list "$SWIFT_CONTAINER" --prefix db/ | sort | head -n "-${DB_RETAIN_DAYS}")
if [[ -n "$DUMPS_TO_DELETE" ]]; then
    echo "$DUMPS_TO_DELETE" | xargs -r -I{} swift delete "$SWIFT_CONTAINER" {}
    log "Pruned: $DUMPS_TO_DELETE"
else
    log "Nothing to prune"
fi

# ---------------------------------------------------------------------------
# Media files — restic
# ---------------------------------------------------------------------------

log "Backing up media files with restic..."
restic -r "$RESTIC_REPO" backup "$MEDIA_PATH"

log "Running restic retention policy (keep 30 daily, 12 monthly)..."
restic -r "$RESTIC_REPO" forget \
    --keep-daily 30 \
    --keep-monthly 12 \
    --prune

log "Backup complete"
