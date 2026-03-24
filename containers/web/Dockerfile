# Use the miniconda container
FROM python:3.14

LABEL description = "Development web container for YWANG-VASTER Classification Tool"

### Need to install Postgres-16 so that it can seed the database with a superuser. 

# Add PostgreSQL Apt repository
RUN apt-get update && \
    apt-get install -y wget gnupg2 lsb-release && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | tee /etc/apt/sources.list.d/pgdg.list && \
    apt-get update

# Install PostgreSQL Client 16 and JS9 build dependencies (nodejs + make)
RUN apt-get install -y postgresql-client-16 libpq-dev cron nodejs npm make && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Vendor JS9 FITS viewer static files into /opt/js9_static.
# The entrypoint copies these into the Django static directory at startup.
# See scripts/vendor_js9.sh for details on why JS9 is vendored and how to update.
COPY ./scripts/vendor_js9.sh /scripts/vendor_js9.sh
RUN bash /scripts/vendor_js9.sh /opt/js9_static

# Copy across the cron job for refreshing the pulsar table. Set it to run every week at 12am Sunday.
COPY ./containers/web/refresh_pulsar_table_cron /etc/cron.d/refresh_pulsar_table_cron
RUN chmod 0644 /etc/cron.d/refresh_pulsar_table_cron
RUN crontab /etc/cron.d/refresh_pulsar_table_cron

# Copy requirements over
COPY ./requirements.txt /.
COPY ./containers/web/entrypoint.sh /.
COPY ./vendor/django-q3c /vendor/django-q3c

# Install requirements for the web app
RUN pip3 install -r /requirements.txt && \
    pip3 install /vendor/django-q3c
WORKDIR /ywangvaster_webapp

# Start the webapp 
ENTRYPOINT [ "/entrypoint.sh" ]

# Bring cron logs to the foreground for docker logs
CMD ["cron", "-f"]
