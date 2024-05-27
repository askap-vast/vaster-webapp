#!/usr/bin/env python

import os
import glob
import argparse
import urllib.request
import requests
import json

from astropy.coordinates import Angle
import astropy.units as u
from astropy.io import fits

import logging

logger = logging.getLogger(__name__)

SYSTEM_ENV = os.environ.get("SYSTEM_ENV", None)
if SYSTEM_ENV == "DEV":
    BASE_URL = "http://127.0.0.1:8000"
else:
    BASE_URL = "https://mwa-image-plane.duckdns.org"


class TokenAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = "Token {}".format(self.token)
        return r


def getmeta(servicetype="metadata", service="obs", params=None):
    """
    Function to call a JSON web service and return a dictionary:
    Given a JSON web service ('obs', find, or 'con') and a set of parameters as
    a Python dictionary, return a Python dictionary xcontaining the result.
    Taken verbatim from http://mwa-lfd.haystack.mit.edu/twiki/bin/view/Main/MetaDataWeb
    """

    # Append the service name to this base URL, eg 'con', 'obs', etc.
    BASEURL = "http://ws.mwatelescope.org/"

    if params:
        # Turn the dictionary into a string with encoded 'name=value' pairs
        data = urllib.parse.urlencode(params)
    else:
        data = ""

    try:
        result = json.load(urllib.request.urlopen(BASEURL + servicetype + "/" + service + "?" + data))
    except urllib.error.HTTPError as err:
        logger.error("HTTP error from server: code=%d, response:\n %s" % (err.code, err.read()))
        return
    except urllib.error.URLError as err:
        logger.error("URL or network error: %s" % err.reason)
        return

    return result


def upload_obsid(obsid):
    """Upload an MWA observation to the database.

    Parameters
    ----------
    obsid : `int`
        MWA observation ID.
    """
    data = getmeta(params={"obsid": obsid})

    # Upload
    session = requests.session()
    session.auth = TokenAuth(os.environ["IMAGE_PLANE_TOKEN"])
    url = f"{BASE_URL}/observation_create/"
    data = {
        "observation_id": obsid,
        "obsname": data["obsname"],
        "starttime": data["starttime"],
        "stoptime": data["stoptime"],
        "ra_tile_dec": data["metadata"]["ra_pointing"],
        "dec_tile_dec": data["metadata"]["dec_pointing"],
        "ra_tile_hms": Angle(data["metadata"]["ra_pointing"], unit=u.deg).to_string(unit=u.hour, sep=":")[:11],
        "dec_tile_dms": Angle(data["metadata"]["dec_pointing"], unit=u.deg).to_string(unit=u.deg, sep=":")[:12],
        "projectid": data["projectid"],
        "azimuth": data["metadata"]["azimuth_pointing"],
        "elevation": data["metadata"]["elevation_pointing"],
        "frequency_channels": str(data["rfstreams"]["0"]["frequencies"]),
        "cent_freq": (data["rfstreams"]["0"]["frequencies"][0] + data["rfstreams"]["0"]["frequencies"][-1]) * 1.28 / 2,
        "freq_res": data["freq_res"],
        "int_time": data["int_time"],
    }
    # r = session.post(url, data=data)
    session.post(url, data=data)


def upload_candidate(fits_files, image_gif_directory):
    """Upload an MWA observation to the database.

    Parameters
    ----------
    fits_files : `list`
        A list of the file locations of each fits file you would like to upload.
    image_gif_directory : `str`
        The directory containing all the images and gifs.
    """
    # Set up session
    session = requests.session()
    session.auth = TokenAuth(os.environ["IMAGE_PLANE_TOKEN"])
    url = f"{BASE_URL}/candidate_create/"

    # Loop over fits files
    for fits_path in fits_files:
        # Read fits file
        hdul = fits.open(fits_path)

        # loop over each candidate
        for cand in hdul[1].data:
            data = {}
            # Loop over each header and append data to the upload dictionary
            for hi, dat in enumerate(cand):
                fits_header = f"TTYPE{hi+1}"
                header = hdul[1].header[fits_header]
                logger.debug("")
                logger.debug(f"{header}: {dat}")
                if f"TCOMM{hi+1}" in hdul[1].header.keys():
                    logger.debug(hdul[1].header[f"TCOMM{hi+1}"])
                if header == "obs_cent_freq":
                    # Skip because already have that data in obsid
                    pass
                elif header == "obs_id":
                    # upload obsid
                    upload_obsid(dat)
                    data[header] = dat
                elif header.endswith("ra_deg"):
                    # parse to hms
                    data[header] = dat
                    hms_header = header[:-3] + "hms"
                    data[hms_header] = Angle(dat, unit=u.deg).to_string(unit=u.hour, sep=":")[:11]
                elif header.endswith("dec_deg"):
                    # parse to dms
                    data[header] = dat
                    dms_header = header[:-3] + "dms"
                    data[dms_header] = Angle(dat, unit=u.deg).to_string(unit=u.deg, sep=":")[:12]
                else:
                    data[header] = dat

            # Work out image and gif path
            base_path = f"{image_gif_directory}/{data['obs_id']}_" + f"{data['filter_id']}_{data['cand_id']:03d}"
            image_path = f"{base_path}.png"
            gif_path = f"{base_path}.gif"

            # open the image file
            with open(image_path, "rb") as image, open(gif_path, "rb") as gif:
                # upload to database
                r = session.post(url, data=data, files={"png": image, "gif": gif})
            print(r.text)
            r.raise_for_status()


if __name__ == "__main__":
    loglevels = dict(DEBUG=logging.DEBUG, INFO=logging.INFO, WARNING=logging.WARNING)
    parser = argparse.ArgumentParser(description="Upload a transient candidate to the database.")
    parser.add_argument(
        "--data_directory",
        type=str,
        help="Path to directory containing all of the gifs and images.",
    )
    parser.add_argument(
        "--fits",
        type=str,
        help="Optional option to specify a fits file. " "If not used, will get all fits files in the data_directory",
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

    if args.fits:
        fits_files = [args.fits]
    else:
        fits_files = glob.glob(f"{args.data_directory}/*fits")
    upload_candidate(fits_files, args.data_directory)
