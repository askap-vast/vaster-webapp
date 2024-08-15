# YWANG VASTER - Classification tool

This webapp is based in Python 3.10, Django v4.2, Bootstrap v5.2 and a Postgres backend to store all of the important site assets and data.

## Running locally

Start the docker containers using:

`docker compose up -d`

which will build and run the webapp locally. You can then access the webapp at http://localhost:80/ and login with "admin" and "test".

To kill webapp, shutdown the docker containers,

`docker compose down`

Adding the `-v` tag will remove the webapps volumes and databases. This includes any candidate data, ratings and user accounts.

## Deployment

You will need to add the correct domain for the webapp to the "ALLOWED_HOSTS" variable in the docker-compose.prod.yml file. Also,
please be sure to fill and set a strong password for the DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD as this is exposed to the public internet.

Once setting the variables in the production config file, start the containers with:

`docker compose up -d -f docker-compose.prod.yml`

## Uploading candidates

To upload candidates to the webapp, you will need to install the requirements.txt into your python environment. It is best to use create a new Python v3.10 virtual environment. Install the requirements.txt using the following:

`pip3 install -r requirements.txt`

The upload script finds all beam, candidates ( in the `*_final.csv`), and all of their associated files the --data_directory path (which can be an absolute or a relative path).

When upload candidates, you will need to log into the webapp and copy your upload token. It can be found under the "User Management" modal in the navigation bar. Please note that you can 'refresh' the upload token. Any previous token will be considered expired and will not work for uploading candidates to the webapp.

The "project_id" here can be any arbitary string. It is used to organise many different observations. The "project_id" must be unique and you will not be able to upload multiple observations of the same observation ID under the same project. You will also need to define the observation ID (obs_id) in

Example usage of the upload script to a local version:

`python3 ywangvaster_webapp/upload_cand.py --base_url http://localhost:8000 --token <your_token> --project_id <project_id> --observation_id <obs_id> --data_directory <path_to_candidate_files>`

or when it is deployed to a production url, simply replace the base_url entry with the production URL set in the docker-compose.prod.yml file.

## Usage

Once logged into the webapp, the user will be viewing all projects in the webapp by default. You can select which project you are viewing by going to the "User Management" button in the navigation bar.

Users can also reset their password in this window.

### Filtering Candidates

Filtering for candidates uploaded in the webapp is done in the "Candidate" tab. Here you will be able to filter based on the observation, beam index, cone serach of the candidate (using string RA and DEC), various other float values that are stored in the candidate data (such as Chi^2 and sigma values), and if by the rating of the candidate.
