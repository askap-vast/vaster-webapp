<a id="uploading-candidates"></a>

# Uploading candidates

## Upload Script

Uploading candidates to the webapp can be done using the `ywangvaster_webapp/upload_cand.py` python script. It uses a number of POST requests to push the candidate data to the webapp.

1. Ensure you install or use a Python 3.10 environment with `astropy` installed.

   ```bash
   pip3 install astropy
   ```

   or you can install the full requirements for the webapp

   ```bash
   pip3 install -r requirements.txt
   ```

2. Log into the webapp using your credentials and get your upload token from the "User management" button a the top right of the navbar.

3. Use the following Python script to send candidate data to the webapp,

   ```bash
   python3 ywangvaster_webapp/upload_cand.py --base_url http://<webapp_url>:80 --token <your_upload_token> --project_id <project_to_upload_to> --observation_id <the SBID> --data_directory <path_to_candidate_data>
   ```

Notes:

- Any user can upload candidates to the webapp.
- If the `project_id` given to the upload script does not match one existing in the webapp's database, the webapp will create a new one and upload the candidate data to that newly created `project_id`. The same goes for Observations, Beams and Candidates records.
- The `data_directory` path can be relative or absolute but requires the `<SBID>_beam<index>_final.csv` to be present for the upload script to pull the candidate information in for each beam and upload to the webapp.
- All of the relevant fits files, images, and gifs from the beam and candidate are found by the upload script by their filename and will be uploaded with the associated candidate. If any are no files present, then there will be a placeholder for them on the candidate rating page.
- You do not need to copy the candidate data to the host machine of the webapp. One should be able to use the python script from a remote machine with an internet connect to send all of the candidate data to the webapp.
