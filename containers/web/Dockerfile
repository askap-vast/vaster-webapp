# Use the miniconda container
FROM python:3.10

LABEL description = "Development web container for YWANG-VASTER Classification Tool"

### Need to install Postgres-16 so that it can seed the database with a superuser. 

# Add PostgreSQL Apt repository
RUN apt-get update && \
    apt-get install -y wget gnupg2 lsb-release && \
    echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | tee /etc/apt/sources.list.d/pgdg.list && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt-get update

# Install PostgreSQL Client 16
RUN apt-get install -y postgresql-client-16 libpq-dev cron && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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
