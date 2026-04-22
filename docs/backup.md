# Backups

The `scripts/backup.sh` script performs daily backups of the two critical data stores:

- **PostgreSQL database** — dumped with `pg_dump` and uploaded to Swift object storage. The last 30 daily dumps are retained.
- **Media files** (`django_media` volume) — snapshotted with [restic](https://restic.net/) into a Swift-backed restic repository. 30 daily and 12 monthly snapshots are retained.

## Running a backup

The script is intended to run daily via cron but can also be triggered manually:

```bash
sudo scripts/backup.sh
```

## Configuration

The configuration block at the top of `scripts/backup.sh` controls the database container name, Swift container name, restic repository path, and the path to the `django_media` bind mount. Edit these to match your deployment before first use.

The script expects OpenStack credentials to be sourced from an RC file and a `RESTIC_PASSWORD` environment variable to be set.

## Restore

To restore the database, download the desired dump from Swift and pipe it into `pg_restore`:

```bash
docker exec -i ywangvaster-db pg_restore \
    -U ywangvaster -d ywangvaster --clean --if-exists \
    < /tmp/restore.pgdump
```

To restore media files, use restic:

```bash
restic -r swift:vaster-backups:/restic-media restore latest --target /path/to/django_media
```
