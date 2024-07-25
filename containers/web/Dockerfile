# Use the miniconda container
FROM python:3.10

LABEL description = "Development web container for YWANG-VASTER Classification Tool"

# Install Postgres for Django to talk to the postgres server.
RUN apt-get -y update && apt-get install -y postgresql libpq-dev

### - To check why curl is needed?
# Install curl
RUN apt-get -y update && apt-get -y install curl cron gcc

# create a location for Django to keep static files
# RUN mkdir -p /var/www/static

# Copy requirements over
COPY ./requirements.txt /.
COPY ./containers/web/entrypoint.sh /.

# Install requirements for the web app
RUN pip3 install -r /requirements.txt

WORKDIR /ywangvaster_webapp

ENTRYPOINT [ "/entrypoint.sh" ]
