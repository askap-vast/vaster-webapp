#!/bin/bash
set -e

#  Check if the auth_user table has been created to see if the DB has already been migrated by DJango
TABLE_CHECK="$( psql "postgres://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:$DB_PORT" -XtAc "SELECT rolname FROM pg_roles WHERE rolsuper IS TRUE AND rolname = '$DJANGO_SUPERUSER_USERNAME';" )"

echo "Result from auth_table check: " $TABLE_CHECK

# Make migrations (just incase of changes) and apply 
python3 /ywangvaster_webapp/manage.py makemigrations
python3 /ywangvaster_webapp/manage.py makemigrations candidate_app 
python3 /ywangvaster_webapp/manage.py migrate 

if  [[ $TABLE_CHECK == *DJANGO_SUPERUSER_USERNAME* ]]; then

    echo "Django has already seeded the Postgres DB - Not migrating." 

else 
    echo "Postgres DB is missing the \"auth\" table -  Creating the Django superuser."

    # Create Django superuser to log into Django's admin system.
    python3 /ywangvaster_webapp/manage.py createsuperuser --noinput --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL

fi 

# This runs the web app locally through Django
python3 /ywangvaster_webapp/manage.py runserver 0.0.0.0:8000