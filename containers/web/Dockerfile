# Use the miniconda container
FROM python:3.10

LABEL description = "Development web container for YWANG-VASTER Classification Tool"

# Install Postgres for Django to talk to the postgres server.
RUN apt-get -y update && apt-get install -y postgresql libpq-dev cron

# Copy across the cron job for refreshing the pulsar table. Set it to run every week at 12am Sunday.
COPY ./containers/web/refresh_pulsar_table_cron /etc/cron.d/refresh_pulsar_table_cron
RUN chmod 0644 /etc/cron.d/refresh_pulsar_table_cron
RUN crontab /etc/cron.d/refresh_pulsar_table_cron

# Copy requirements over
COPY ./requirements.txt /.
COPY ./containers/web/entrypoint.sh /.

# Install requirements for the web app
RUN pip3 install -r /requirements.txt
WORKDIR /ywangvaster_webapp

# Start the webapp 
ENTRYPOINT [ "/entrypoint.sh" ]

# Bring cron logs to the foreground for docker logs
CMD ["cron", "-f"]
