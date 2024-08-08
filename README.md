# YWANG - VAST

This webapp is based in Django v4.2, Bootstrap v5.2 and a Postgres backend to store all of the important site assets and data.

## Deployment

Ensure that the variables in the .env.dev (for development) are correct)

Start the docker containers using:

`docker compose up -d`

which will build and run the webapp locally.

To shutdown the docker containers,

`docker compose down`

and by adding the `-v` tag will remove the webapps volumes and databases.

## Uploading candidates

Please make sure that you clone the Github repo and install the requirements into your python environment.

`pip install -r requirements.txt`

use the upload script to send the candidate data to the webapp

`python3 ywangvaster_webapp/upload_cand.py --base_url http://localhost:8000 --token <your_token> --project_id <ex_project1> --observation_id <obs_id> --data_directory <candidate_directory>`

or when it is deployed to a production url

`python3 ywangvaster_webapp/upload_cand.py --base_url http://ywangvaster.duckdns--token <your_token> --project_id <ex_project1> --observation_id <obs_id> --data_directory <candidate_directory>`
