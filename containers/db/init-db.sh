#!/bin/bash
set -e

# Initialise the DB on only the first ever start-up 
# Have to do this per line otherwise postgres complains
psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE $DB_NAME;"
psql -v ON_ERROR_STOP=1 -c "CREATE USER $DB_USERNAME WITH ENCRYPTED PASSWORD '$DB_PASSWORD';"

# Apply superuser role to DB admin
psql -v ON_ERROR_STOP=1 -c "ALTER ROLE $DB_USERNAME SUPERUSER;"
