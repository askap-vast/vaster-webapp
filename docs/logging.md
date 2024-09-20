# Logs

## Container

Checking the logs can be done by looking each of the docker container logs.

```bash
   docker logs <container-name> logs
```

You can also include the `--follow` if you want to stream the current logs from the container.

```bash
   docker logs <container-name> logs --follow
```

## Gunicorn

Logs form Gunicorn will be saves to the `logs/gunicorn_access.log` file. This keeps record of all the requests made from the external web to the Django container.

## Django

All of the logs from Django will be stored in the `logs/webapp.log` text file. All of Django's logs are keep here and is useful if there are any errors with the webapp, and the standard python traceback will be present in this file.
