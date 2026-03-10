import csv
import zipfile
from io import StringIO, BytesIO
from typing import List, Optional

from astropy import units
from astroquery.simbad import Simbad
from astropy.coordinates import Angle, SkyCoord

from django.db.models import Count, F, Q, Value, QuerySet
from django.http import HttpResponse

from django_q3c.expressions import Q3CDist, Q3CRadialQuery

from rest_framework import status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from . import models

CONFIDENCE_MAPPING = {
    "T": "True",
    "F": "False",
    "U": "Unsure",
}

DEFAULT_RATINGS_INPUT = {
    "tag": None,
    "confidence": "",
    "observation": None,
    "user": None,
    "page": 1,
}

DOWNLOAD_CANDIDATE_FIELDS = [
    "hash_id",
    "proj_id",
    "obs_id",
    "beam_index",
    "name",
    "ra_str",
    "dec_str",
    "ra",
    "dec",
    "chi_square",
    "chi_square_log_sigma",
    "chi_square_sigma",
    "peak_map",
    "peak_map_log_sigma",
    "peak_map_sigma",
    "gaussian_map",
    "gaussian_map_sigma",
    "std_map",
    "bright_sep_arcmin",
    "beam_ra",
    "beam_dec",
    "beam_sep_deg",
    "deep_ra_deg",
    "deep_dec_deg",
    "deep_sep_arcsec",
    "deep_name",
    "deep_num",
    "deep_peak_flux",
    "deep_int_flux",
    "md_deep",
    "lightcurve_data",
]

FILTER_FORM_FLOAT_VARAIBLES = [
    "chi_square",
    "chi_square_log_sigma",
    "chi_square_sigma",
    "peak_map",
    "peak_map_log_sigma",
    "peak_map_sigma",
    "gaussian_map",
    "gaussian_map_sigma",
    "std_map",
    "md_deep",
    "deep_sep_arcsec",
    "bright_sep_arcmin",
    "beam_sep_deg",
    "deep_peak_flux",
    "deep_int_flux",
]

FILTER_CAND_VAR_MAPPING = {
    "chi_square": "Chi Square",
    "chi_square_sigma": "Chi Square Sigma",
    "chi_square_log_sigma": "Chi Square Log Sigma",
    "peak_map": "Peak Map",
    "peak_map_sigma": "Peak Map Sigma",
    "peak_map_log_sigma": "Peak Map Log Sigma",
    "gaussian_map": "Gaussian Map",
    "gaussian_map_sigma": "Gaussian Map Sigma",
    "std_map": "Std Map",
    "bright_sep_arcmin": "Bright Sep (arcmin)",
    "beam_sep_deg": "Beam Sep (deg)",
    "deep_int_flux": "Deep Int Flux",
    "deep_peak_flux": "Deep Peak Flux",
    "deep_sep_arcsec": "Deep Sep (arcsec)",
    "md_deep": "Modulation Index",
    "rated": "Rating Count",
    "observation.id": "Observation",
    "beam.index": "Beam Index",
    "deep_num": "Deep Num",
    "rating_count": "Rating Count",
    "rating.confidence": "Rating Confidence",
    "rating.tag.name": "Rating Tag",
    "cand_sep": "Candidate Position Sep (arcmin)",
    "beam_sep": "Beam Position Sep (arcmin)",
    "deep_sep": "Deep Position Sep (arcmin)",
}

PROJECT_COLOURS = [
    "#5470C6",
    "#91CC75",
    "#FAC858",
    "#EE6666",
    "#73C0DE",
    "#3BA272",
    "#FC8452",
    "#9A60B4",
    "#FF6E76",
    "#EA7CCC",
    "#D9A0F7",
]


def get_atnf(ra_str: str, dec_str, dist_arcmin: float = 1.0) -> List[dict]:
    """Get a list of ANTF pulsars near coordindates"""

    ra = Angle(ra_str, unit=units.hour)
    dec = Angle(dec_str, unit=units.deg)

    # Perform atnf query
    table = (
        models.ATNFPulsar.objects.filter(
            Q(
                Q3CRadialQuery(
                    center_ra=ra.deg,
                    center_dec=dec.deg,
                    ra_col="raj",
                    dec_col="decj",
                    radius=dist_arcmin / 60.0,
                )
            )
        )
        .annotate(  # do the distance calcs in the db
            sep=Q3CDist(
                ra1=F("raj"),
                dec1=F("decj"),
                ra2=ra.deg,
                dec2=dec.deg,
            )
            * 60,  # arcsec -> degrees
            from_db=Value("ATNF"),
        )
        .order_by("sep")
        .values()
    )

    return table


def get_simbad(ra_str: str, dec_str: str, dist_arcmin: float = 1.0) -> List[dict]:
    """Get a list of object next to candidate with ra_str and dec_str"""

    ra_deg = Angle(ra_str, unit=units.hour).deg
    dec_deg = Angle(dec_str, unit=units.deg).deg
    dist_arcmin = float(dist_arcmin)

    # limit query distance or we get very long timeouts
    dist_arcmin = min(dist_arcmin, 60)

    coord = SkyCoord(ra_deg, dec_deg, unit=(units.deg, units.deg), frame="icrs")
    # Perform simbad query
    raw_result_table = Simbad.query_region(coord, radius=dist_arcmin * units.arcmin)
    simbad_result_table = []
    # Reformat the result into the format we want
    if raw_result_table:
        for result in raw_result_table:
            search_term = result["main_id"].replace("+", "%2B").replace(" ", "+")
            simbad_coord = SkyCoord(
                result["ra"], result["dec"], unit=(units.hour, units.deg), frame="icrs"
            )
            ra = simbad_coord.ra.to_string(unit=units.hour, sep=":", pad=True)[:11]
            dec = simbad_coord.dec.to_string(unit=units.deg, sep=":", pad=True)[:11]
            sep = coord.separation(simbad_coord).arcsec
            simbad_result_table.append(
                {
                    "name": result["main_id"],
                    "search_term": search_term,
                    "ra_str": ra,
                    "dec_str": dec,
                    "sep": sep,
                    "from_db": "Simbad",
                }
            )

    return simbad_result_table


def filter_candidates_by_coords(
    incoming: List[models.Candidate],
    ra_str: str,
    dec_str: str,
    ra_col: str,
    dec_col: str,
    arcmin_search_radius: float,
    annotate: Optional[bool] = False,
    sep_name: Optional[str] = None,
    for_rating_table: Optional[bool] = False,
):
    """Convert from str ra_hms and dec_dms to degrees and filter
    candidates that are within the arcmin_search_radius."""

    # Ensure that the incoming radius is a float value
    arcmin_search_radius = float(arcmin_search_radius)

    if not (None in (ra_str, dec_str) or dec_str == "" or dec_str == ""):
        ra_deg = Angle(ra_str, unit=units.hour).deg
        dec_deg = Angle(dec_str, unit=units.deg).deg

        if annotate:
            if sep_name:
                filtered = (
                    incoming.filter(
                        Q(
                            Q3CRadialQuery(
                                center_ra=ra_deg,
                                center_dec=dec_deg,
                                ra_col=ra_col,
                                dec_col=dec_col,
                                radius=arcmin_search_radius / 60.0,
                            )
                        )
                    )
                    .annotate(
                        **{
                            sep_name: Q3CDist(
                                ra1=F(ra_col),
                                dec1=F(dec_col),
                                ra2=ra_deg,
                                dec2=dec_deg,
                            )
                            * 60
                        }
                    )
                    .order_by(sep_name)
                )

            else:
                filtered = (
                    incoming.filter(
                        Q(
                            Q3CRadialQuery(
                                center_ra=ra_deg,
                                center_dec=dec_deg,
                                ra_col=ra_col,
                                dec_col=dec_col,
                                radius=arcmin_search_radius / 60.0,
                            )
                        )
                    )
                    .annotate(  # do the distance calcs in the db
                        sep=Q3CDist(
                            ra1=F(ra_col),
                            dec1=F(dec_col),
                            ra2=ra_deg,
                            dec2=dec_deg,
                        )
                        * 60  # arcsec -> degrees # ???? How doe that turn into degrees???
                    )
                    .order_by("sep")
                )

            print(f"filtered candidates: {filtered}")

        elif for_rating_table:
            filtered = (
                incoming.filter(
                    Q(
                        Q3CRadialQuery(
                            center_ra=ra_deg,
                            center_dec=dec_deg,
                            ra_col=ra_col,
                            dec_col=dec_col,
                            radius=arcmin_search_radius / 60.0,
                        )
                    )
                )
                .annotate(  # do the distance calcs in the db
                    sep=Q3CDist(
                        ra1=F(ra_col),
                        dec1=F(dec_col),
                        ra2=ra_deg,
                        dec2=dec_deg,
                    )
                    * 60,
                    # arcsec -> degrees # ???? How doe that turn into degrees???
                    from_db=Value("Local"),
                )
                .values()
            )

        else:
            filtered = incoming.filter(
                Q(
                    Q3CRadialQuery(
                        center_ra=ra_deg,
                        center_dec=dec_deg,
                        ra_col=ra_col,
                        dec_col=dec_col,
                        radius=arcmin_search_radius / 60.0,
                    )
                )
            )

        return filtered
    else:
        print(
            f"Incoming variables did not pass the None or empty test - cols {ra_col} {dec_col}"
        )
        return incoming


def get_candidate_form_defaults():
    """Make a dictionary of default values for the filter form.

    Pulls the min and max values from the DB and sets as the default form values."""

    # Get the max and mins from the materialised view table
    aggs = models.CandidateMinMaxStats.objects.values().last()

    # Get the default values for the float sliders.
    default_float_values = {}
    for variable in FILTER_FORM_FLOAT_VARAIBLES:
        for x, y in zip(["min", "max"], ["gte", "lte"]):
            default_float_values[f"{variable}__{y}"] = (
                float(aggs[f"{x}_{variable}"])
                if aggs[f"{x}_{variable}"] is not None
                else None
            )

    default_inputs = {
        "rated": "",
        "ratings_count": None,
        "tag": None,
        "confidence": "",
        "observation": None,
        # Cand
        "cand_ra_str": "",
        "cand_dec_str": "",
        "cand_arcmin_search_radius": 2.0,
        # Beam
        "beam_index": None,
        "beam_ra_str": "",
        "beam_dec_str": "",
        "beam_arcmin_search_radius": 2.0,
        # Deep
        "deep_num": None,
        "deep_ra_str": "",
        "deep_dec_str": "",
        "deep_arcmin_search_radius": 2.0,
    }

    return default_inputs, default_float_values


def get_new_values_diff(original: dict, new: dict):
    """Get the difference between two dictionaries and return the new values."""

    new_values = {}
    for key, original_value in original.items():
        if key in new:
            if original_value != new[key] and new[key] is not None:
                new_values[key] = new[key]
        else:
            new_values[key] = original_value

    return new_values


def build_candidate_queryset(
    session_data: dict,
    project_hash_id: Optional[str] = None,
    unrated_only: bool = False,
) -> QuerySet:
    """Build a filtered candidate queryset from session filter data.

    Applies all filters present in session_data, including the three-state
    'rated' filter ("" = all, "true" = rated only, "false" = unrated only).

    If unrated_only=True, the 'rated' filter is overridden to "false" regardless
    of what session_data contains.
    """
    if unrated_only:
        session_data = {**session_data, "rated": "false"}

    default_inputs, default_float_values = get_candidate_form_defaults()

    inputs_to_filter = get_new_values_diff(default_inputs, session_data)
    floats_to_filter = get_new_values_diff(default_float_values, session_data)

    if project_hash_id:
        candidates = models.Candidate.objects.filter(project=project_hash_id)
    else:
        candidates = models.Candidate.objects.all()

    # Float filtering
    if floats_to_filter:
        candidates = candidates.filter(**{k: v for k, v in floats_to_filter.items()})

    # Confidence filter
    if "confidence" in inputs_to_filter:
        candidates = candidates.filter(rating__rating=inputs_to_filter["confidence"])

    # Tag filter
    if "tag" in inputs_to_filter:
        candidates = candidates.filter(rating__tag__hash_id=inputs_to_filter["tag"])

    # Rated/unrated filter ("" = no filter, "true" = rated only, "false" = unrated only)
    if "rated" in inputs_to_filter:
        rated_value = inputs_to_filter["rated"]
        if rated_value == "true":
            candidates = candidates.annotate(rating_count=Count("rating")).filter(
                rating_count__gt=0
            )
        elif rated_value == "false":
            candidates = candidates.annotate(rating_count=Count("rating")).filter(
                rating_count=0
            )

    # Observation filter
    if "observation" in inputs_to_filter:
        candidates = candidates.filter(observation=inputs_to_filter["observation"])

    # Beam index filter
    if "beam_index" in inputs_to_filter:
        candidates = candidates.filter(beam__index=inputs_to_filter["beam_index"])

    # Deep num filter
    if "deep_num" in inputs_to_filter:
        candidates = candidates.filter(deep_num=inputs_to_filter["deep_num"])

    # Candidate cone search
    if (
        session_data.get("cand_ra_str")
        and session_data.get("cand_dec_str")
        and session_data.get("cand_arcmin_search_radius")
    ):
        candidates = filter_candidates_by_coords(
            candidates,
            session_data["cand_ra_str"],
            session_data["cand_dec_str"],
            "ra",
            "dec",
            session_data["cand_arcmin_search_radius"],
            annotate=True,
            sep_name="cand_sep",
        )

    # Beam cone search
    if (
        session_data.get("beam_ra_str")
        and session_data.get("beam_dec_str")
        and session_data.get("beam_arcmin_search_radius")
    ):
        candidates = filter_candidates_by_coords(
            candidates,
            session_data["beam_ra_str"],
            session_data["beam_dec_str"],
            "beam_ra",
            "beam_dec",
            session_data["beam_arcmin_search_radius"],
            annotate=True,
            sep_name="beam_sep",
        )

    # Deep cone search
    if (
        session_data.get("deep_ra_str")
        and session_data.get("deep_dec_str")
        and session_data.get("deep_arcmin_search_radius")
    ):
        candidates = filter_candidates_by_coords(
            candidates,
            session_data["deep_ra_str"],
            session_data["deep_dec_str"],
            "deep_ra_deg",
            "deep_dec_deg",
            session_data["deep_arcmin_search_radius"],
            annotate=True,
            sep_name="deep_sep",
        )

    return candidates


def download_rating_csv_zip(
    queryset: QuerySet,
    table: str,
    candidate_fields: List[str] = None,
) -> HttpResponse:
    """Write the ratingd queryset all tags into zip file to be downloaded by the user."""

    # Create an in-memory output file for the zip file
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        # Create CSV for ratings
        ratings_csv_buffer = StringIO()
        ratings_writer = csv.writer(ratings_csv_buffer)

        # Define headers, including candidate information
        rating_field_names = [field.name for field in queryset.model._meta.fields]
        # Rename some column names
        if "hash_id" in rating_field_names:
            index = rating_field_names.index("hash_id")
            rating_field_names[index] = "rating_hash_id"

        if candidate_fields is None:
            candidate_fields = [
                field.name for field in models.Candidate._meta.fields
            ]  # Default to all candidate fields
        ratings_headers = rating_field_names + candidate_fields
        ratings_writer.writerow(ratings_headers)

        # Write data rows for ratings
        for rating in queryset:
            candidate = rating.candidate
            row = []
            for field in rating_field_names:
                if field == "tag":
                    row.append(rating.tag.name)  # Access tag name
                elif field == "date":
                    row.append(rating.date)
                elif field == "rating_hash_id":
                    row.append(rating.hash_id)
                else:
                    row.append(getattr(rating, field))

            if candidate:
                row += [getattr(candidate, field) for field in candidate_fields]
            else:
                row += ["N/A"] * len(candidate_fields)  # If no candidate, fill with N/A
            ratings_writer.writerow(row)

        # Write ratings CSV to the zip file
        zip_file.writestr(f"{table}_ratings.csv", ratings_csv_buffer.getvalue())

        # Create CSV for tags
        tags_csv_buffer = StringIO()
        tags_writer = csv.writer(tags_csv_buffer)

        # Define headers for tags
        tag_field_names = [field.name for field in models.Tag._meta.fields]
        tags_writer.writerow(tag_field_names)

        # Write data rows for tags
        tags = models.Tag.objects.all()
        for tag in tags:
            row = [getattr(tag, field) for field in tag_field_names]
            tags_writer.writerow(row)

        # Write tags CSV to the zip file
        zip_file.writestr("all_tags.csv", tags_csv_buffer.getvalue())

    # Create a response with the zip file
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{table}_data.zip"'

    return response


def get_upload_token(request):
    """Extract and validate the Authorization token from an upload request.

    Returns (token, None) on success, or (None, Response(...)) on failure."""
    try:
        token_str = request.headers["Authorization"]
    except KeyError:
        return None, Response(
            {"status": "error", "message": "Unable to pull out token of the request."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        token = Token.objects.get(key=token_str)
        return token, None
    except Exception as error:
        return None, Response(
            {"status": "error", "message": f"Invalid or expired token - {error}"},
            status=status.HTTP_403_FORBIDDEN,
        )


def get_session_filter_data(request):
    """Return (session_data, default_inputs, default_float_values, default_all_values)."""
    default_inputs, default_float_values = get_candidate_form_defaults()
    default_all_values = {**default_inputs, **default_float_values}
    session_data = request.session.get("current_filter_data", default_all_values)
    return session_data, default_inputs, default_float_values, default_all_values
