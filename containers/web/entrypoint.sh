#!/bin/bash

### Make migrations (incase of changes) and apply 
python3 manage.py makemigrations --noinput
python3 manage.py makemigrations candidate_app --noinput
python3 manage.py migrate 

###  Check if the auth_user table has been created to see if the DB has already been migrated by DJango

### This is to check if a migration is necessary for the DB - keep just in case
###   TABLE_CHECK="$( psql "postgres://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:$DB_PORT" -XtAc "SELECT rolname FROM pg_roles WHERE rolsuper IS TRUE;" )"

TABLE_CHECK="$( psql "postgres://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:$DB_PORT" -XtAc "SELECT username FROM auth_user WHERE is_superuser IS TRUE;" )"
echo "Result from auth_table check: " $TABLE_CHECK

if  [[ "$TABLE_CHECK" == *"$DJANGO_SUPERUSER_USERNAME"* ]]; then

    echo "Django superuser with username $DJANGO_SUPERUSER_USERNAME has already been created." 

else 
    echo "Postgres DB is missing the django superuser $DJANGO_SUPERUSER_USERNAME - Adding it to the DB."

    python3 manage.py createsuperuser --noinput --username $DJANGO_SUPERUSER_USERNAME --email $DJANGO_SUPERUSER_EMAIL

    # Since it is a fresh DB, load up the ANTF pulsar table
    python3 manage.py refresh_pulsar_table

    if [[ $PROD == "true" ]]; then 

        echo "--- Running as PROD version - $PROD ---"

        echo "Copying across the static files."

        python manage.py collectstatic --noinput

    else

        echo "Not copying across the static files."

    fi

fi 

### Do the setup for the cron job for the refresh_pulsar_table

# Export all environment variables to a file - used by cron job
printenv | grep -v "no_proxy" > /etc/environment

# Start cron in the background
cron &

### Start the web server

# Dev or Production versions.
if [[ "$PROD" == "true" ]]; then 

    echo "--- Running as PROD version - $PROD ---"

    echo "Starting production web server using gunicorn."

    gunicorn ywangvaster_webapp.wsgi:application --bind 0.0.0.0:80 --error-logfile /home/app/gunicorn_error.log --access-logfile /home/app/logs/gunicorn_access.log

else

    echo "--- Running as DEV version ---"

    # This runs the web app locally through Django
    python3 manage.py runserver 0.0.0.0:80

fi