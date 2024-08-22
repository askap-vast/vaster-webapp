# Usage

The candidate data for the webapp is separated by the following tree Projects, Observations, Beams, and Candidates.


# Uploading candidates

Uploading candidates is achieved by following steps.

1. Ensure you install, or use a python 3.10 environment with astropy installed.
    or use 'pip3 install astropy'
2. Log into the webapp and get your upload token from the "User management" button in the navbar. 
3. Use the following python script to send candidate data to the webapp host machine

```
python3 ywangvaster_webapp/upload_cand.py --base_url http://<webapp_url>:80 --token <your_upload_token> --project_id <project_to_upload_to> --observation_id <the SBID> --data_directory <path_to_candidate_data>
```
