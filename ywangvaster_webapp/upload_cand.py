#!/usr/bin/env python

import os
import glob
import argparse
import re
import csv
from typing import List, Tuple
import urllib.request
import requests
import json

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


def parse_filename(filename: str) -> Tuple[str, str, str]:
    """Parse the filename to get it's componenets"""

    # Get details of the filename and sort into folders
    split_filename = filename.split("_")
    survey_id = split_filename[0]
    beam_id = split_filename[1]  # or [4:]
    series = split_filename[2]

    series_split = series.split(".")
    if len(series_split) > 1:
        series = series_split[0]

    return survey_id, beam_id, series


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


def find_csv_file_with_name(search_pattern: str, data_type: str, file_list: List[str], project_id: str):
    """Find the a file that best matches '{search pattern}.csv' and read from it."""

    data = []
    for path in file_list:

        # Get info from filename.
        filename = os.path.basename(path)
        survey_id, beam_id, series = parse_filename(filename)

        # Get path to file
        pattern = re.compile(rf"{search_pattern}\.csv$")
        if pattern.search(filename):

            # Read csv file

            with open(path, mode="r", newline="", encoding="utf-8") as csv_file:
                csv_reader = csv.DictReader(csv_file)

                if data_type == "cand_list":
                    for row in csv_reader:
                        row["project_id"] = project_id
                        row["survey_id"] = survey_id
                        row["beam_id"] = beam_id
                        data.append(row)

                if data_type == "per_cand":
                    for row in csv_reader:
                        data.append(row)

            break

    return data


def upload_candidates(base_url, token, project_id, data_directory):
    """Upload a survey/observation to the YWANG-VASTER webapp."""
    # Set up session
    session = requests.session()
    session.auth = TokenAuth(token)
    url = f"{base_url}/upload_candidate/"

    # Get list of files from the data directory
    file_list = get_absolute_file_paths(data_directory)

    # Find csv final - list of candidates to be pushed to the webapp
    candidates = find_csv_file_with_name("_final", "cand_list", file_list, project_id)

    # Get lightcurve data
    lightcurve_local_rms = find_csv_file_with_name("_lightcurve_local_rms", "per_cand", file_list, project_id)
    lightcurve_peak_flux = find_csv_file_with_name("_lightcurve_peak_flux", "per_cand", file_list, project_id)

    # for each candidate
    for cand in candidates:

        survey_id, beam_id, cand_id = cand["survey_id"], cand["beam_id"], cand["name"]

        # Add the lightcurve data to the candidate data
        cand["lightcurve_local_rms"] = [[lc["Time"], lc[cand_id]] for lc in lightcurve_local_rms]
        cand["lightcurve_peak_flux"] = [[lc["Time"], lc[cand_id]] for lc in lightcurve_peak_flux]

        print(cand["lightcurve_local_rms"])

        # Upload the images, gifs and fits files
        upload_files = {}
        for series_name, fmt_list in [
            ("lightcurve", ["png"]),
            ("slices", ["gif", "fits"]),
            ("deepcutout", ["png", "fits"]),
        ]:

            for fmt in fmt_list:
                filename = os.path.join(data_directory, f"{survey_id}_{beam_id}_{series_name}_{cand_id}.{fmt}")
                upload_files[f"{series_name}.{fmt}"] = open(filename, "rb")

        try:
            # Send the request
            r = session.post(
                url,
                data=cand,
                files=upload_files,
            )
            print(r.text)
            r.raise_for_status()

        finally:
            for file in upload_files.values():
                file.close()


if __name__ == "__main__":
    loglevels = dict(DEBUG=logging.DEBUG, INFO=logging.INFO, WARNING=logging.WARNING)
    parser = argparse.ArgumentParser(description="Upload a transient candidate to the database.")

    parser.add_argument(
        "--base_url",
        type=str,
        help="URL fo the webapp to upload to.",
    )

    parser.add_argument(
        "--username",
        type=str,
        help="Username for the webapp.",
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

    upload_candidates(args.base_url, args.token, args.project_id, data_path)
