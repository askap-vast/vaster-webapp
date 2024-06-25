#!/usr/bin/env python

import os
import re
import csv
import json
import argparse
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from astropy.io import fits

import logging

logger = logging.getLogger(__name__)


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token: str):
        self.token = str(token)

    def __call__(self, r):
        r.headers["Authorization"] = self.token
        return r


# Not needed for now
# def getmeta(servicetype="metadata", service="obs", params=None):
#     """
#     Function to call a JSON web service and return a dictionary:
#     Given a JSON web service ('obs', find, or 'con') and a set of parameters as
#     a Python dictionary, return a Python dictionary xcontaining the result.
#     Taken verbatim from http://mwa-lfd.haystack.mit.edu/twiki/bin/view/Main/MetaDataWeb
#     """

#     # Append the service name to this base URL, eg 'con', 'obs', etc.
#     BASEURL = "http://ws.mwatelescope.org/"

#     if params:
#         # Turn the dictionary into a string with encoded 'name=value' pairs
#         data = urllib.parse.urlencode(params)
#     else:
#         data = ""

#     try:
#         result = json.load(urllib.request.urlopen(BASEURL + servicetype + "/" + service + "?" + data))
#     except urllib.error.HTTPError as err:
#         logger.error("HTTP error from server: code=%d, response:\n %s" % (err.code, err.read()))
#         return
#     except urllib.error.URLError as err:
#         logger.error("URL or network error: %s" % err.reason)
#         return

#     return result


# def upload_obsid(obsid):
#     """Upload an MWA observation to the database.

#     Parameters
#     ----------
#     obsid : `int`
#         MWA observation ID.
#     """
#     data = getmeta(params={"obsid": obsid})

#     # Upload
#     session = requests.session()
#     session.auth = TokenAuth(os.environ["IMAGE_PLANE_TOKEN"])
#     url = f"{BASE_URL}/observation_create/"
#     data = {
#         "observation_id": obsid,
#         "obsname": data["obsname"],
#         "starttime": data["starttime"],
#         "stoptime": data["stoptime"],
#         "ra_tile_dec": data["metadata"]["ra_pointing"],
#         "dec_tile_dec": data["metadata"]["dec_pointing"],
#         "ra_tile_hms": Angle(data["metadata"]["ra_pointing"], unit=u.deg).to_string(unit=u.hour, sep=":")[:11],
#         "dec_tile_dms": Angle(data["metadata"]["dec_pointing"], unit=u.deg).to_string(unit=u.deg, sep=":")[:12],
#         "projectid": data["projectid"],
#         "azimuth": data["metadata"]["azimuth_pointing"],
#         "elevation": data["metadata"]["elevation_pointing"],
#         "frequency_channels": str(data["rfstreams"]["0"]["frequencies"]),
#         "cent_freq": (data["rfstreams"]["0"]["frequencies"][0] + data["rfstreams"]["0"]["frequencies"][-1]) * 1.28 / 2,
#         "freq_res": data["freq_res"],
#         "int_time": data["int_time"],
#     }
#     # r = session.post(url, data=data)
#     session.post(url, data=data)


def group_dictionaries(tuples_list):
    # Dictionary to hold the groups, using frozenset of dictionary items as keys
    grouped = {}

    for keys, dictionary in tuples_list:
        # Convert dictionary to frozenset of its items to use as a hashable key
        dict_key = frozenset(dictionary.items())
        if dict_key not in grouped:
            grouped[dict_key] = (keys, dictionary)
        else:
            grouped[dict_key][0].extend(keys)

    # Convert the dictionary back to the list of tuples
    return list(grouped.values())


def parse_filename(filename: str) -> Tuple[str, str, str]:
    """Parse the filename to get it's componenets"""

    # Get details of the filename and sort into folders
    split_filename = filename.split("_")
    obs_id = split_filename[0]
    beam_id = split_filename[1]  # or [4:]
    series = split_filename[2]

    series_split = series.split(".")
    if len(series_split) > 1:
        series = series_split[0]

    return obs_id, beam_id, series


# Find file in list
def find_best_match(file_list):
    # Define the pattern to match "_final.csv"
    pattern = re.compile(r"_final\.csv$")

    # Initialize variable to store the best match
    best_match = None

    # Iterate through the list of files
    for file_name in file_list:
        if pattern.search(file_name):
            best_match = file_name
            break  # Since we are looking for the best match, return as soon as we find one

    return best_match


def get_absolute_file_paths(directory):
    """
    Returns a list of absolute file paths for all files in the given directory.
    """
    file_paths = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            file_paths.append(os.path.abspath(os.path.join(dirpath, filename)))
    return file_paths


def find_files_with_pattern(search_pattern: str, directory: str) -> List[str]:
    """
    param search_pattern: The regex style search pattern to find the files with that string.
    param
    """

    pattern = re.compile(search_pattern)
    matching_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if pattern.match(file):
                matching_files.append(os.path.join(root, file))

    return matching_files


def parse_csv_file(file_path: str, data_type: str, project_id: str):
    """"""

    # Get info from filename.
    filename = os.path.basename(file_path)
    obs_id, beam_id, _ = parse_filename(filename)

    if not os.path.exists(file_path):
        print(f"File path {file_path} does not exsist!")
        return None

    data = []
    with open(file_path, mode="r", newline="", encoding="utf-8") as csv_file:
        csv_reader = csv.DictReader(csv_file)

        if data_type == "cand_list":
            for row in csv_reader:
                beam_int = int(beam_id[4:])
                row["proj_id"] = project_id
                row["obs_id"] = obs_id
                row["beam_index"] = beam_int
                data.append(row)

        if data_type == "per_cand":
            for row in csv_reader:
                data.append(row)

    return data


def send_observation_request(
    session: requests.Session,
    obs_url: str,
    project_id: str,
    obs_id: str,
    directory: str = os.path.dirname(os.path.realpath(__file__)),
):

    ### Get the observation date from one of the fits files ###
    std_fits_obs_file_path = os.path.join(directory, f"{obs_id}_beam00_std.fits")
    with fits.open(std_fits_obs_file_path) as hdul:
        # Access the primary header
        header = hdul[0].header

        # Retrieve the value of the 'DATE-OBS' keyword
        _date_obs = header.get("DATE-OBS")
        _time_sys = header.get("TIMESYS")

        # Turn datetime into a proper datetime object for
        timesys = _time_sys.strip()
        datetime_object = datetime.fromisoformat(_date_obs)
        if timesys.upper() == "UTC":
            datetime_object = datetime_object.replace(tzinfo=timezone.utc)

    ### Send a request to create an observation record in the DB ###
    r = session.post(
        obs_url,
        data={
            "id": obs_id,
            "proj_id": project_id,
            "obs_start": datetime_object.isoformat(),
            "obs_obj_id": f"{project_id}_{obs_id}",
        },
    )
    print(r.text)
    # r.raise_for_status()


def send_beam_request(
    session: requests.Session,
    beam_url: str,
    project_id: str,
    obs_id: str,
    beam_id: str,
    directory: str = os.path.dirname(os.path.realpath(__file__)),
):
    """Uploads beam specific files to the ywangvaster webapp."""

    beam_upload_files = {}
    for series_name, fmt_list in [
        ("final", ["csv"]),
        ("std", ["fits"]),
        # ("chisquare_cand", ["csv"]),
        ("chisquare_map1", ["png"]),
        ("chisquare_map2", ["png"]),
        ("chisquare", ["fits"]),
        # ("peak_cand", ["csv"]),
        ("peak_map1", ["png"]),
        ("peak_map2", ["png"]),
        ("peak", ["fits"]),
    ]:

        for fmt in fmt_list:
            filename = os.path.join(directory, f"{obs_id}_{beam_id}_{series_name}.{fmt}")
            beam_upload_files[f"{series_name}_{fmt}"] = open(filename, "rb")

    try:
        beam_int = int(beam_id[4:])
        # Send the request
        r = session.post(
            beam_url,
            data={
                "proj_id": project_id,
                "obs_id": obs_id,
                "index": beam_int,
                "beam_obj_id": f"{project_id}_{obs_id}_beam{beam_int}",
            },
            files=beam_upload_files,
        )
        print(r.text)
        r.raise_for_status()

    finally:
        # Close all of the opened files.
        for file in beam_upload_files.values():
            file.close()


def send_cand_request(
    session: requests.Session,
    cand_url: str,
    obs_id: str,
    beam_id: str,
    cand: Dict,
    lightcurve_local_rms: Optional[Dict] = None,
    lightcurve_peak_flux: Optional[Dict] = None,
    directory: str = os.path.dirname(os.path.realpath(__file__)),
):

    # Add the lightcurve data to the candidate, and in error bars and cast as strings for json handling.
    if (
        lightcurve_peak_flux is not None
        and lightcurve_local_rms is not None
        and cand["name"] in lightcurve_peak_flux[0]
    ):

        lightcurve = [["Time", cand["name"], "rms_error"]]
        for lc, lc_err in zip(lightcurve_peak_flux, lightcurve_local_rms):

            assert (
                lc["Time"] == lc_err["Time"]
            ), f"Time x-value for the lightcurve data is not the same in CSVs! {cand['name']}"

            lightcurve.append([lc["Time"], lc[cand["name"]], lc_err[cand["name"]]])
        cand["lightcurve_data"] = json.dumps(lightcurve)

    cand_upload_files = {}
    # Upload the images, gifs and fits files if it is from the "final" model.
    for series_name, fmt_list in [
        ("lightcurve", ["png"]),
        ("slices", ["gif", "fits"]),
        ("deepcutout", ["png", "fits"]),
    ]:

        for fmt in fmt_list:
            filename = os.path.join(directory, f"{obs_id}_{beam_id}_{series_name}_{cand['name']}.{fmt}")
            if os.path.exists(filename):
                cand_upload_files[f"{series_name}_{fmt}"] = open(filename, "rb")

    try:
        # Send the request
        r = session.post(
            cand_url,
            data=cand,
            files=cand_upload_files,
        )
        print(r.text)
        r.raise_for_status()

    finally:
        # Close all of the opened files.
        for file in cand_upload_files.values():
            file.close()


def upload_data(base_url, token, project_id, obs_id, data_directory):
    """Upload a obs/observation to the YWANG-VASTER webapp."""
    # Set up session
    session = requests.session()
    session.auth = TokenAuth(token)
    obs_url = f"{base_url}/upload_observation/"
    beam_url = f"{base_url}/upload_beam/"
    cand_url = f"{base_url}/upload_candidate/"

    # Find all of the beam output files for this observation.
    beam_final_candidate_files = find_files_with_pattern(rf"{obs_id}_.*_final\.csv", data_directory)

    print(f"beam_final_candidate_files: {beam_final_candidate_files}")

    # Get the list of beams in the directory
    all_beam_ids = []
    for beam_final_csv_path in beam_final_candidate_files:
        filename = os.path.basename(beam_final_csv_path)
        all_beam_ids.append(filename.split("_")[1])

    # Upload information about the observation
    send_observation_request(session, obs_url, project_id, obs_id, data_directory)

    # For each beam
    for beam_id in all_beam_ids:

        # Upload the metadata, fits and images for each beam
        send_beam_request(session, beam_url, project_id, obs_id, beam_id, data_directory)

        candidate_csv_path = os.path.join(data_directory, f"{obs_id}_{beam_id}_final.csv")

        # List of candidates from the *_final.csv
        candidates = parse_csv_file(candidate_csv_path, "cand_list", project_id)

        print(f"Number of candidates for upload - {len(candidates)}")

        # Read in the lightcurve data files
        lightcurve_peak_flux = parse_csv_file(
            os.path.join(data_directory, f"{obs_id}_{beam_id}_lightcurve_peak_flux.csv"),
            "per_cand",
            project_id,
        )

        lightcurve_local_rms = parse_csv_file(
            os.path.join(data_directory, f"{obs_id}_{beam_id}_lightcurve_local_rms.csv"),
            "per_cand",
            project_id,
        )

        # Loop through each possible candidate
        for cand in candidates:

            # Remove source_id
            cand.pop("source_id")

            # Add or remove other keys for webapp
            cand["cand_obj_id"] = f"{project_id}_{obs_id}_beam{int(beam_id[4:])}_{cand['name']}"

            send_cand_request(
                session,
                cand_url,
                obs_id,
                beam_id,
                cand,
                lightcurve_local_rms,
                lightcurve_peak_flux,
                data_directory,
            )


if __name__ == "__main__":
    loglevels = dict(DEBUG=logging.DEBUG, INFO=logging.INFO, WARNING=logging.WARNING)
    parser = argparse.ArgumentParser(description="Upload a transient candidate to the database.")

    parser.add_argument(
        "--base_url",
        type=str,
        help="URL fo the webapp to upload to.",
    )

    parser.add_argument(
        "--token",
        type=str,
        help="Uplaod token for the webapp.",
    )

    parser.add_argument(
        "--project_id",
        type=str,
        help="ID of the propject to upload to.",
    )

    parser.add_argument(
        "--observation_id",
        type=str,
        help="Observation ID - eg, SB50230",
    )

    parser.add_argument(
        "--data_directory",
        type=str,
        help="Path to directory containing all of candidate data.",
    )

    parser.add_argument(
        "-L",
        "--loglvl",
        type=str,
        help="Logger verbosity level. Default: INFO",
        choices=loglevels.keys(),
        default="INFO",
    )
    args = parser.parse_args()

    # set up the logger for stand-alone execution
    formatter = logging.Formatter("%(asctime)s  %(name)s  %(lineno)-4d  %(levelname)-9s :: %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    # Set up local logger
    logger.setLevel(args.loglvl)
    logger.addHandler(ch)
    logger.propagate = False

    # To handle relative or absolute paths
    if not os.path.isabs(args.data_directory):
        data_path = os.path.abspath(args.data_directory)
    else:
        data_path = args.data_directory

    upload_data(args.base_url, args.token, args.project_id, args.observation_id, data_path)
