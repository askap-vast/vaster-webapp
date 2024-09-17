# Database

## Structure

The database for this webapp is a Postgres v16 container with the Q3C extension installed. All indexing of coordinates and initialisation of the database is handled by a combination of entrypoint scripts for the docker containers as well as the Django migration scripts.

When candidate data is uploaded, it is split into separate models: Projects, Observations, Beam, Candidates, with each model being linked back with a foreign key relationship.

When using the upload script, it will create the necessary records if they don't already exist. For example, if candidates under a given "project_id" have not been uploaded before, then a new project with that name will be created. The same will happen for the Observations, Beams, and Candidates.

The Beams and Candidates hold the related files for each observation. This includes all of the fits, slices and deep images. The Beam model holds the files for the statistical maps, and the Candidate model only holds files relating to that specific candidate.

A diagram of how the database is structured can be found below.

![Database structure image](./images/db_structure.svg "Database structure")

## Clearing the database

Starting from fresh can be done simply by stopping and starting up the docker containers with the volume flag. All of the data is stored on docker volumes and not in the containers themselves.

To stop the docker containers and delete the volumes:

```bash
docker compose -f docker-compose.prod.yml down -v
```

and simply start the containers again with

```bash
docker compose -f docker-compose.prod.yml up -d
```

## ATNF Pulsars

The full ANTF pulsar [catalogue](https://www.atnf.csiro.au/research/pulsar/psrcat/) is imported into the webapp on first start-up. This is done to make the searching of the database much quicker rather than making a web request for each search on the Candidate Rating page.

The pulsar catalogue is regularly updated automatically at 12am Sunday every week by the Django web container. This is done using a cron job defined in the `containers/web/refresh_pulsar_table_cron` file.

Alternatively, you can force the update manually by using the following docker command on the machine that is hosting the webapp:

```bash
    docker exec -it ywangvaster-web python3 /ywangvaster_webapp/manage.py refresh_pulsar_table
```

which will download and parse the full ATNF database and overwrite current version of the table in the Postgres docker container. When running the update command you will see logs printed to the console.
