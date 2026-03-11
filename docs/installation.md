# Installation

Please ensure that Docker and Docker Compose is installed on the host machine. Download and install instructions for Docker on Ubuntu can be found here [link](https://docs.docker.com/engine/install/ubuntu/).

## Setup

Before running any environment, copy the environment and volumes template files:

```bash
cp .env.template .env
cp docker-compose.volumes.yml.template docker-compose.volumes.yml
```

Then fill in the required values in `.env` (see [Environment variables](#environment-variables) below). Both files are gitignored and will not be committed.

## Development

To start the webapp locally in development mode:

```bash
make dev
```

This starts the Django and Postgres containers. Once running, the webapp is accessible at `http://localhost:80` with the following default credentials:

- Username: admin
- Password: test

To shut down:

```bash
make dev-down
```

## Production

To start the production version:

```bash
make prod
```

To shut down:

```bash
make prod-down
```

## Staging

To start the staging version:

```bash
make staging
```

The staging environment is identical to production but displays a `[STAGING]` indicator in the header bar. Optionally, place a `staging-details.html` file in the repo root to display release notes on the home page.

To shut down:

```bash
make staging-down
```

## Environment variables

All environment-specific configuration is set in `.env`. The following variables must be filled in before deploying:

- `DJANGO_ALLOWED_HOSTS`: Space-separated list of allowed hostnames, e.g. `vaster.duckdns.org`
- `DJANGO_SUPERUSER_USERNAME`: Admin username
- `DJANGO_SUPERUSER_PASSWORD`: A strong password (16+ characters, mixed case, numbers, symbols)
- `DJANGO_SUPERUSER_EMAIL`: Admin email address shown to users for support
- `DJANGO_SECRET_KEY`: A long random string used for cryptographic signing
- `DB_PASSWORD` / `POSTGRES_PASSWORD`: Database passwords

See `.env.template` for the full list of variables.

## Volumes

By default, Docker manages the named volumes for the database and media files. If you wish to store data at specific paths on the host machine, edit `docker-compose.volumes.yml` and uncomment the `driver_opts` block for each volume:

```yaml
volumes:
  django_media:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/vaster_webapp/volumes/django_media
```

Make sure the directories exist and have the correct permissions before starting:

```bash
mkdir -p /data/vaster_webapp/volumes/django_media
sudo chown -R 999:999 /data/vaster_webapp/volumes/django_media
```

Please note that port 80 on the host machine must be open for internet traffic to reach the webapp. Refer to this [guide](https://linuxconfig.org/how-to-open-allow-incoming-firewall-port-on-ubuntu-22-04-jammy-jellyfish) on how to open ports on Ubuntu 22.04.
