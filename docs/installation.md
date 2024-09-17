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

Starting the production version of the webapp is similar to the above. However before deploying, there are a number of variables to change in the `docker-compose.prod.yml` file. These variables are the following:

- DJANGO_ALLOWED_HOSTS: Add your production url here, for example, `ywangvaster.duckdns.org`. These are the domains that are allowed be used to access the webapp.
- DJANGO_SUPERUSER_USERNAME: A unique username.
- DJANGO_SUPERUSER_PASSWORD: A strong password is recommended. More than 16 characters, mixed with numbers, symbols, lowercase and uppercase.
- DJANGO_SUPERUSER_EMAIL: An email address that users can send emails to if they come across issues with the webapp.
- DJANGO_SECRET_KEY: A complex key with many different numbers, letters, and capitals.

To start the production version of the webapp, you will to run the following command:

```bash
docker compose -f docker-compose.prod.yml up -d
```

and to turn shutdown all of the containers and the docker network:

```bash
docker compose -f docker-compose.prod.yml down
```

The production mode containers are:

- Postgres: Database to hold all of the candidate data and webapp data.
- Django web: Web server start by Gunicorn.
- Nginx: A reverse proxy to assist with handling a number of web requests.
- Autoheal: Container to watch and restart any of the other containers if there are issues.

You will need to make sure that port 80 on the host machine is forwarded correctly for internet traffic to be passed to the docker network.

Please see this [guide](https://linuxconfig.org/how-to-open-allow-incoming-firewall-port-on-ubuntu-22-04-jammy-jellyfish) on how to open ports on Ubuntu 22.04.
