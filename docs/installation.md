# Installation

Please ensure that Docker and Docker compose v3.9 is installed on the host machine. Download and install instructions for Docker on Ubuntu can be found here [link](https://docs.docker.com/engine/install/ubuntu/).

## Development

To install the webapp locally in development mode, start the docker containers and network with

```bash
   docker compose up -d
```

This will start only the Django and the Postgres containers. Once it successfully starts and the ATNF database has been loaded, you should be able to access it at `http://localhost:80` and log in with the following credentials:

- Username: admin
- Password: test

To shutdown the containers:

```bash
   docker compose down
```

## Production

### Environment variables

Starting the production version of the webapp is similar to the above. However before deploying, there are a number of variables to change in the `docker-compose.prod.yml` file. These variables are the following:

- DJANGO_ALLOWED_HOSTS: Add your production url here, for example, `ywangvaster.duckdns.org`. These are the domains that are allowed be used to access the webapp.
- DJANGO_SUPERUSER_USERNAME: A unique username.
- DJANGO_SUPERUSER_PASSWORD: A strong password is recommended. More than 16 characters, mixed with numbers, symbols, lowercase and uppercase.
- DJANGO_SUPERUSER_EMAIL: An email address that users can send emails to if they come across issues with the webapp.
- DJANGO_SECRET_KEY: A complex key with many different numbers, letters, and capitals.

### Volumes

If you wish to have the data for the webapp stored in a specific location on the host machine, please make sure you follow these steps:

1. Create a folder for postgres_data, django_media and django_static using the following commands

```bash
mkdir -p django_media
sudo chown -R 999:999 django_media
```

2. Uncomment the type, bind and device paramters in the docker-compose.prod.yml and set your path to the folders that were just created, for example:

```bash
volumes:
  django_media:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/vaster_webapp/volumes/django_media
```

### Starting the webapp


To start the production version of the webapp, you will to run the following command:

```bash
docker compose -f docker-compose.prod.yml up -d
```

and to turn shutdown all of the containers and the docker network:

```bash
docker compose -f docker-compose.prod.yml down
```

Please note that you will need to make sure that port 80 on the host machine is forwarded correctly for internet traffic to be passed to the docker network. Refer to this [guide](https://linuxconfig.org/how-to-open-allow-incoming-firewall-port-on-ubuntu-22-04-jammy-jellyfish) on how to open ports on Ubuntu 22.04.
