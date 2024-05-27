FROM postgres:16 as db

LABEL description = "PostgreSQL 16 with q3c"

# Install dependencies
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen &&\
    locale-gen

RUN apt-get update
RUN apt-get install postgresql-16-q3c postgresql-contrib -yqq

# This init script is only run once at first run of the container.
COPY ./containers/db/init-db.sh /docker-entrypoint-initdb.d/init-db.sh