#!/usr/bin/env python

import os
import re
import argparse
import logging

from script_utils import make_session, setup_logging, validate_url, validate_token

logger = logging.getLogger(__name__)

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def upload_dynamic_spectra(base_url, token, file_path, name=None, hash_id=None):
    """Upload a dynamic spectra PNG to an existing candidate via the webapp API."""
    session = make_session(token)
    url = f"{base_url.rstrip('/')}/upload_dynamic_spectra/"

    data = {}
    if name is not None:
        data["name"] = name
    if hash_id is not None:
        data["hash"] = hash_id

    with open(file_path, "rb") as f:
        response = session.post(
            url,
            data=data,
            files={
                "dynamic_spectra_png": (os.path.basename(file_path), f, "image/png")
            },
        )

    print(f"Status {response.status_code}: {response.text}")
    response.raise_for_status()


if __name__ == "__main__":
    loglevels = dict(DEBUG=logging.DEBUG, INFO=logging.INFO, WARNING=logging.WARNING)

    parser = argparse.ArgumentParser(
        description=(
            "Upload a dynamic spectra PNG to an existing candidate in the VASTER webapp. "
            "The candidate must already exist; this command attaches the image to it."
        )
    )

    parser.add_argument(
        "--base_url",
        type=str,
        required=True,
        help="Base URL of the webapp (e.g. https://vaster.example.com).",
    )
    parser.add_argument(
        "--token",
        type=str,
        required=True,
        help="40-character hex upload token for the webapp.",
    )

    ident = parser.add_mutually_exclusive_group(required=True)
    ident.add_argument(
        "--name",
        type=str,
        help=(
            "Name of the candidate to attach the image to. "
            "If multiple candidates share this name, the upload will be rejected — "
            "use --hash instead."
        ),
    )
    ident.add_argument(
        "--hash",
        type=str,
        dest="hash_id",
        metavar="HASH",
        help="UUID hash_id of the candidate (unambiguous identifier).",
    )

    parser.add_argument(
        "file",
        metavar="FILE",
        help="Path to the dynamic spectra PNG file to upload.",
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

    setup_logging(logger, loglevels[args.loglvl])

    errors = []

    url_error = validate_url(args.base_url)
    if url_error:
        errors.append(url_error)

    token_error = validate_token(args.token)
    if token_error:
        errors.append(token_error)

    file_path = os.path.abspath(args.file)
    if not os.path.exists(file_path):
        errors.append(f"FILE does not exist: '{file_path}'")
    elif not os.path.isfile(file_path):
        errors.append(f"FILE is not a regular file: '{file_path}'")
    elif not file_path.lower().endswith(".png"):
        errors.append(f"FILE does not have a .png extension: '{file_path}'")

    if args.hash_id is not None and not UUID_RE.fullmatch(args.hash_id):
        errors.append(
            f"--hash must be a valid UUID "
            f"(e.g. 550e8400-e29b-41d4-a716-446655440000), got: '{args.hash_id}'"
        )

    if errors:
        parser.error("The following arguments are invalid:\n  " + "\n  ".join(errors))

    upload_dynamic_spectra(
        args.base_url,
        args.token,
        file_path,
        name=args.name,
        hash_id=args.hash_id,
    )
