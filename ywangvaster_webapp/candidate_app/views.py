import csv
import json
import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from urllib.parse import urlencode

from astropy import units
from astropy.coordinates import Angle, SkyCoord
from astroquery.simbad import Simbad

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q, Value
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import TemplateView, View

from django_q3c.expressions import Q3CDist, Q3CRadialQuery
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ywangvaster_webapp.settings import MEDIA_ROOT

from . import forms, models, serializers
from .utils import get_disk_space

logger = logging.getLogger(__name__)


table_display_col_mapping = {
    "chi_square": "Chi Square",
}

CONFIDENCE_MAPPING = {"T": "True", "F": "False", "U": "Unsure"}


def home_page(request):
    """Render the home page html."""

    return render(request, "candidate_app/home_page.html")


def about(request):
    """Render the about html."""

    return render(request, "candidate_app/about.html")


def nearby_objects_table(request: HttpRequest):
    """Render a table of nearby objects from the local DB, (filtered by project), Simbad and ATNF pulsars."""

    dist_arcmin = 2
    selected_project_hash_id = request.session.get("selected_project_hash_id")

    if request.method == "POST":
        data = json.loads(request.body.decode())

        ra_str = data.get("ra_str")
        dec_str = data.get("dec_str")
        dist_arcmin = float(data.get("dist_arcmin", 1))
        selected_project_hash_id = data.get("selected_project_hash_id")
        exclude_hash_id = data.get("exclude_id")

    result = []
    simbad_results = get_simbad(ra_str, dec_str, dist_arcmin)

    result.extend(simbad_results)

    atnf_results = get_atnf(ra_str, dec_str, dist_arcmin)
    result.extend(atnf_results)

    if selected_project_hash_id or selected_project_hash_id != "":
        incoming = models.Candidate.objects.filter(project_id=selected_project_hash_id)
    else:
        incoming = models.Candidate.objects.all()

    # if we are given a candidate ID then exclude it from the results
    if exclude_hash_id:
        incoming = incoming.exclude(hash_id=exclude_hash_id)

    local_db_results = filter_candidates_by_coords(
        incoming,
        ra_str,
        dec_str,
        ra_col="ra",
        dec_col="dec",
        arcmin_search_radius=dist_arcmin,
        for_rating_table=True,
    )

    result.extend(local_db_results)

    sorted_results = sorted(result, key=lambda x: x["sep"], reverse=False)

    return render(
        request,
        "candidate_app/nearby_objects_table.html",
        context={"result_table": sorted_results},
    )


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
            search_term = result["MAIN_ID"].replace("+", "%2B").replace(" ", "+")
            simbad_coord = SkyCoord(result["RA"], result["DEC"], unit=(units.hour, units.deg), frame="icrs")
            ra = simbad_coord.ra.to_string(unit=units.hour, sep=":", pad=True)[:11]
            dec = simbad_coord.dec.to_string(unit=units.deg, sep=":", pad=True)[:11]
            sep = coord.separation(simbad_coord).arcminute
            simbad_result_table.append(
                {
                    "name": result["MAIN_ID"],
                    "search_term": search_term,
                    "ra_str": ra,
                    "dec_str": dec,
                    "sep": sep,
                    "from_db": "Simbad",
                }
            )

    return simbad_result_table


def about(request: HttpRequest):
    """The about page for the user to upload files."""

    # If loggin in, get the users token for them and make it available, if not, dont give out the token.

    context = {}

    return render(request, "candidate_app/about.html", context)


@login_required(login_url="/")
def create_tag(request: HttpRequest):

    if request.method == "POST":

        new_tag = forms.ClassificationForm(request.POST)

        print(f"Attempting to create new tag with request.POST: {request.POST}")

        if new_tag.is_valid():

            print(f"New tag is valid! Adding {request.POST['name']} DB.")

            new_tag.save()

            return redirect(request.META["HTTP_REFERER"])


@login_required(login_url="/")
def candidate_rating(request, cand_hash_id, arcmin=2):
    candidate = get_object_or_404(models.Candidate, hash_id=cand_hash_id)

    # Convert time to readable format
    time = candidate.observation.obs_start

    # Grab the previous rating for this candidate and user
    try:
        prev_rating = models.Rating.objects.get(candidate=candidate, user=request.user)
    except:
        prev_rating = None

    rate_form = forms.RateCandidateForm()
    new_tag_form = forms.ClassificationForm()

    if request.method == "POST":

        rate_form = forms.RateCandidateForm(request.POST)

        if rate_form.is_valid():
            # Add tags to the rating (later there could be multiple tags per rating)
            tag_id = request.POST.get("classification")
            classification = models.Classification.objects.get(name=tag_id)

            # Delete the old rating if it exists
            if prev_rating:
                prev_rating.delete()

            # Create a new rating
            models.Rating.objects.create(
                hash_id=uuid4(),
                candidate=candidate,
                user=request.user,
                rating=request.POST["confidence"],
                notes=request.POST["notes"],
                tag=classification,
                date=datetime.now(),
            )

            # TODO - change this to go to a random page for a candidate that's not been rated yet in same set of candidates
            # This is done with the NEXT button??

            return redirect(request.META["HTTP_REFERER"])

    # Convert the lightcurve data to mJy and put into a form for Echarts to use.
    converted_lc = []
    if candidate.lightcurve_data is not None:
        converted_lc = []
        for row in candidate.lightcurve_data:
            try:
                val = float(row[1]) * 1000.0
                err = float(row[2]) * 1000.0
                converted_lc.append([row[0], str(val), str(err)])
            except ValueError as e:
                print(f"Value error: {e}")
                converted_lc.append([row[0], row[1], row[2]])

    context = {
        "CONFIDENCE_MAPPING": CONFIDENCE_MAPPING,
        "candidate": candidate,
        "prev_rating": prev_rating,
        "time": time,
        "rate_form": rate_form,
        "new_tag_form": new_tag_form,
        "lightcurve_data": converted_lc,
        "arcmin_search": arcmin,
        "cand_type_choices": tuple((c.name, c.name) for c in models.Classification.objects.all()),
    }
    return render(request, "candidate_app/candidate_rating.html", context)


@login_required(login_url="/")
@api_view(["POST"])
def get_token(request):
    """Get the user's token using a POST request."""

    if request.method == "POST":
        try:
            create_new = json.loads(request.POST.get("create"))

            token = Token.objects.filter(user=request.user).first()

            # User doesn't have a token yet, create one
            if token is None:
                token = Token.objects.create(user=request.user)

            if create_new:
                token.delete()
                token = Token.objects.create(user=request.user)

            return JsonResponse({"token": token.key}, status=201)
        except:
            return JsonResponse({"Error: Unable to create token for user": request.user}, status=500)


# ### TODO: CHECK IF WE NEED THIS
@login_required(login_url="/")
def candidate_random(request):
    """"""


#     # Get session data for candidate ordering and inclusion settings
#     session_settings = request.session.get("session_settings", 0)

#     # deal with users who have no session settings
#     if not session_settings:
#         return render(request, "candidate_app/nothing_to_rate.html")

#     user = request.user
#     # choose all the candidates this user hasn't rated
#     next_cands = models.Candidate.objects.exclude(rating__user=user)

#     # filter based on selected project
#     next_cands = next_cands.filter(project__name=session_settings["project"])

#     # Filter candidates based on ranking
#     if session_settings["filtering"] == "unrank":
#         # Get unrated candidates
#         next_cands = next_cands.filter(rating__isnull=True)
#         if not next_cands.exists():
#             return render(
#                 request,
#                 "candidate_app/nothing_to_rate.html",
#                 {"project": session_settings["project"]},
#             )
#     elif session_settings["filtering"] == "old":
#         # Get candidates the user hasn't recently ranked
#         next_cands = next_cands.exclude(rating__date__gte=datetime.now() - timedelta(days=7))
#         if not next_cands.exists():
#             return render(
#                 request,
#                 "candidate_app/nothing_to_rate.html",
#                 {"project": session_settings["project"]},
#             )

#     return redirect(reverse("candidate_rating", args=(candidate.id,)))


def filter_candidates_by_coords(
    incoming: List[models.Candidate],
    ra_str: str,
    dec_str: str,
    ra_col: str,
    dec_col: str,
    arcmin_search_radius: float,
    annotate: Optional[bool] = False,
    for_rating_table: Optional[bool] = False,
):
    """Convert from str ra_hms and dec_dms to degrees and filter candidates that are within the arcmin_search_radius."""

    # Ensure that the incoming radius is a float value
    arcmin_search_radius = float(arcmin_search_radius)

    if not (None in (ra_str, dec_str) or dec_str == "" or dec_str == ""):
        ra_deg = Angle(ra_str, unit=units.hour).deg
        dec_deg = Angle(dec_str, unit=units.deg).deg

        if annotate:

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
                    from_db=Value(f"Local"),
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
        print(f"Incoming variables did not pass the None or empty test - cols {ra_col} {dec_col}")
        return incoming


@login_required(login_url="/")
def clear_candidates_filter(request: HttpRequest):

    if "current_filter_data" in request.session or "clear_filter_data" in request.POST:
        del request.session["current_filter_data"]

    return redirect("/candidates/")


@login_required(login_url="/")
def project_select(request):

    selected_project_hash_id = request.session.get("selected_project_hash_id")

    if request.POST:

        project_form = forms.ProjectSelectForm(request.POST)

        if project_form.is_valid():

            print(f"incoming post request - {request.POST}")

            print(f"old project selected - {selected_project_hash_id}")

            request.session["selected_project_hash_id"] = request.POST["selected_project_hash_id"]

            print(f"setting selected_project_hash_id to {request.session['selected_project_hash_id']}")

    return redirect(request.META["HTTP_REFERER"])


@login_required(login_url="/")
def change_password(request):
    if request.method == "POST":
        pw_reset_form = PasswordChangeForm(request.user, request.POST)
        if pw_reset_form.is_valid():
            user = pw_reset_form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, "Your password was successfully updated!")
            return redirect(request.META["HTTP_REFERER"])
        else:
            messages.error(request, "Please correct the error below.")


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

# To later be replaced with maths characters that the html can recognise
# variable in db: Label for html
FILTER_FORM_FLOAT_VARAIBLES_DICT = {
    "chi_square": "Chi Squared",
    "chi_square_log_sigma": "Chi Square Log Sigma",
    "chi_square_sigma": "Chi Square Sigma",
    "peak_map": "Peak Map",
    "peak_map_log_sigma": "Peak map log sigma",
    "peak_map_sigma": "Peak map sigma",
    "gaussian_map": "Gaussian Map",
    "gaussian_map_sigma": "Gaussian map sigma",
    "std_map": "Standard Map (units?)",
    "md_deep": "Deep modulation (units?)",
    "deep_sep_arcsec": "Deep separation (arcsec)",
    "bright_sep_arcmin": "Bright separation (arcmin)",
    "beam_sep_deg": "Beam separation (degrees)",
    "deep_peak_flux": "Deep peak flux (units?)",
    "deep_int_flux": "Deep initial flux (units?)",
    "rated": "Rating count",
}


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
                float(aggs[f"{x}_{variable}"]) if aggs[f"{x}_{variable}"] is not None else None
            )

    default_inputs = {
        "rated": False,
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

    new_values = {}
    for key, original_value in original.items():
        if original_value != new[key]:
            new_values[key] = new[key]

    return new_values


@login_required(login_url="/")
def candidate_table(request: HttpRequest):

    # Get session data to keep filters when changing page
    # This only holds what values are used for the filtering, not all.

    default_inputs, default_float_values = get_candidate_form_defaults()
    default_all_values = {**default_inputs, **default_float_values}

    candidate_table_session_data = request.session.get("current_filter_data", default_all_values)

    selected_project_hash_id = request.session.get("selected_project_hash_id")

    if request.method == "GET" and request.GET:
        candidate_table_session_data.update(request.GET.dict())

        # Update the form values with the variables from url decode.
        form = forms.CandidateFilterForm(
            selected_project_hash_id=selected_project_hash_id,
            initial=candidate_table_session_data,
        )

    # This is a filter request.
    if request.method == "POST":

        form = forms.CandidateFilterForm(
            request.POST,
            selected_project_hash_id=selected_project_hash_id,
        )

        if form.is_valid():

            cleaned_data = {**form.cleaned_data}

            # To allow the user to keep filtering and navigate back on page.
            request.session["current_filter_data"] = cleaned_data
            candidate_table_session_data = cleaned_data

            # Filter the manual inputs, see if they are different from the default values.
            url_dictionary = get_new_values_diff(default_all_values, cleaned_data)

            # Make the query string
            query_string = urlencode(url_dictionary)

            print(f"======================================= {query_string}")

            return redirect(f"{request.path}?{query_string}")
    else:

        form = forms.CandidateFilterForm(
            selected_project_hash_id=selected_project_hash_id,
            initial=candidate_table_session_data,
        )

    filtered_columns = set()

    inputs_to_filter = get_new_values_diff(default_inputs, candidate_table_session_data)
    floats_to_filter = get_new_values_diff(default_float_values, candidate_table_session_data)

    if selected_project_hash_id:

        print(f"Filtering for candidates with project hash_id: {selected_project_hash_id}")
        candidates = models.Candidate.objects.all()
        candidates = candidates.filter(project=selected_project_hash_id)

    else:
        candidates = models.Candidate.objects.all()

    ### Float Filtering ###

    # These are the sliders that are used for filtering the candidates.
    filtered_columns = {key.split("__")[0] for key in floats_to_filter.keys()}
    candidates = candidates.filter(**{key: value for key, value in floats_to_filter.items()})

    ### Individual input filtering ###

    confidence_filter = None
    if "confidence" in inputs_to_filter:

        # Fetch all ratings with the specified confidence
        all_ratings = models.Rating.objects.filter(rating=inputs_to_filter["confidence"]).distinct()
        candidate_hash_ids = all_ratings.values_list("candidate__hash_id", flat=True)
        candidates = models.Candidate.objects.filter(hash_id__in=candidate_hash_ids)
        filtered_columns.add("rating.confidence")
        confidence_filter = inputs_to_filter["confidence"]

    # Tag / Classification filter
    tag_filter_name = None
    if "tag" in inputs_to_filter:

        # Bit of messing around here because can be multiple raitings for each candidate
        candidates_unset = candidates.filter(rating__tag=inputs_to_filter["tag"])
        candidates_list = list(set(list(candidates_unset)))
        candidate_hash_ids = [candidate.hash_id for candidate in candidates_list]
        candidates = models.Candidate.objects.filter(hash_id__in=candidate_hash_ids)

        filtered_columns.add("rating.tag.name")
        tag_filter_name = models.Classification.objects.get(hash_id=inputs_to_filter["tag"]).name

    # Ratings filter
    if "rated" in inputs_to_filter:
        candidates = candidates.annotate(rating_count=Count("rating")).filter(rating_count__gt=0)
        filtered_columns.add("rating_count")

    # Obsid filter
    if "observation" in inputs_to_filter:
        candidates = candidates.filter(observation=inputs_to_filter["observation"])
        filtered_columns.add("observation.id")

    # Beam index filtering
    if "beam_index" in inputs_to_filter:  # Because index of 0 is treated as false
        candidates = candidates.filter(beam__index=inputs_to_filter["beam_index"])
        filtered_columns.add("beam.index")

    # Filter candidate by cone search
    if (
        candidate_table_session_data["cand_ra_str"]
        and candidate_table_session_data["cand_dec_str"]
        and candidate_table_session_data["cand_arcmin_search_radius"]
    ):
        candidates = filter_candidates_by_coords(
            candidates,
            candidate_table_session_data["cand_ra_str"],
            candidate_table_session_data["cand_dec_str"],
            "ra",
            "dec",
            candidate_table_session_data["cand_arcmin_search_radius"],
        )
        filtered_columns.add("candidate_cone_radius")

    # Filter beam by beam position
    if (
        candidate_table_session_data["beam_ra_str"]
        and candidate_table_session_data["beam_dec_str"]
        and candidate_table_session_data["beam_arcmin_search_radius"]
    ):
        candidates = filter_candidates_by_coords(
            candidates,
            candidate_table_session_data["beam_ra_str"],
            candidate_table_session_data["beam_dec_str"],
            "beam_ra",
            "beam_dec",
            candidate_table_session_data["beam_arcmin_search_radius"],
        )
        filtered_columns.add("beam_cone_radius")

    # Filter candidate by deep position
    if (
        candidate_table_session_data["deep_ra_str"]
        and candidate_table_session_data["deep_dec_str"]
        and candidate_table_session_data["deep_arcmin_search_radius"]
    ):
        candidates = filter_candidates_by_coords(
            candidates,
            candidate_table_session_data["deep_ra_str"],
            candidate_table_session_data["deep_dec_str"],
            "deep_ra_deg",
            "deep_dec_deg",
            candidate_table_session_data["deep_arcmin_search_radius"],
        )
        filtered_columns.add("deep_cone_radius")

    # Paginate
    paginator = Paginator(candidates, 25)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    content = {
        "page_obj": page_obj,
        "form": form,
        "CONFIDENCE_MAPPING": CONFIDENCE_MAPPING,
        "default_float_values": default_float_values,
        "updated_float_values": candidate_table_session_data,
        "filtered_columns": filtered_columns,
        "column_labels": FILTER_FORM_FLOAT_VARAIBLES_DICT,
        "tag_filter_name": tag_filter_name,
        "confidence_filter": confidence_filter,
    }
    return render(request, "candidate_app/candidate_table.html", content)


def download_rating_csv(request, queryset, table, candidate_fields=None):
    if not request.user.is_staff:
        raise PermissionDenied
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{table}.csv"'
    writer = csv.writer(response)

    # Define headers, including candidate information
    rating_field_names = [field.name for field in queryset.model._meta.fields]
    candidate_fields = candidate_fields or [
        field.name for field in models.Candidate._meta.fields
    ]  # Default to all candidate fields
    headers = rating_field_names + candidate_fields
    writer.writerow(headers)

    # Write data rows
    for rating in queryset:
        candidate = rating.candidate
        row = [getattr(rating, field) for field in rating_field_names]
        if candidate:
            row += [getattr(candidate, field) for field in candidate_fields]
        else:
            row += ["N/A"] * len(candidate_fields)  # If no candidate, fill with N/A
        writer.writerow(row)

    return response


def rating_summary(request: HttpRequest):
    """Render the ratings template."""

    selected_project_hash_id = request.session.get("selected_project_hash_id")
    print(f"selected_project_hash_id - {selected_project_hash_id}")

    if selected_project_hash_id:
        ratings = models.Rating.objects.filter(candidate__project=selected_project_hash_id)
    else:
        ratings = models.Rating.objects.all()

    # Handle CSV download
    if request.GET.get("download") == "csv":
        # print
        return download_rating_csv(request, ratings, "ratings_summary")

    ### Ratings table ###

    # Handle the filter form
    if request.method == "POST":
        form = forms.RatingFilterForm(selected_project_hash_id, request.POST)
        if form.is_valid():
            if form.cleaned_data["observation"]:
                ratings = ratings.filter(candidate__observation=form.cleaned_data["observation"])
            if form.cleaned_data["tag"]:
                ratings = ratings.filter(tag=form.cleaned_data["tag"])
            if form.cleaned_data["confidence"]:
                ratings = ratings.filter(rating=form.cleaned_data["confidence"])
            if form.cleaned_data["user"]:
                ratings = ratings.filter(user__username=form.cleaned_data["user"])

            # if form.cleaned_data["date_from"]:
            #     ratings = ratings.filter(date__gte=form.cleaned_data["date_from"])
            # if form.cleaned_data["date_to"]:
            #     ratings = ratings.filter(date__lte=form.cleaned_data["date_to"])
    else:
        form = forms.RatingFilterForm(selected_project_hash_id=selected_project_hash_id)

    ### Echarts bar plots ###

    # For echarts bar plots of the tags and ratings per user and tag/classification.
    # Convert QuerySet to list of dictionaries for ratings per user
    ratings_per_user = list(ratings.values("user__username").annotate(count=Count("hash_id")))

    # Convert QuerySet to list of dictionaries for ratings per tag
    ratings_per_tag = list(ratings.values("tag__name").annotate(count=Count("hash_id")))

    # Paginate
    paginator = Paginator(ratings, 25)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "form": form,
        "CONFIDENCE_MAPPING": CONFIDENCE_MAPPING,
        "page_obj": page_obj,
        "ratings": ratings,
        "ratings_per_user": ratings_per_user,
        "ratings_per_tag": ratings_per_tag,
    }

    print(f"context for the ratings page: {context}")

    return render(request, "candidate_app/ratings_summary.html", context)


@api_view(["POST"])
@transaction.atomic
def upload_observation(request):

    if request.method == "POST":

        # Get user specific data
        try:
            token_str = request.headers["Authorization"]

        except KeyError:
            return Response(
                {"status": "error", "message": f"Unable to pull out token of the request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Find token in the db
            token = Token.objects.get(key=token_str)
            if token is not None:

                print(f" --------------- Observation uploaded by user: {token.user} --------------- ")
                try:

                    # Pull out the project id
                    project_id = request.data["proj_id"]

                    print(f"++++++++ project_id: {project_id} ++++++++ ")

                    # Create the project if it doesn't already exist.
                    if not models.Project.objects.filter(id=project_id).exists():
                        uploaded_datetime = datetime.now(timezone.utc)

                        # Create the Upload metadata
                        upload = models.Upload.objects.create(
                            user=token.user,
                            date=uploaded_datetime,
                        )
                        upload.save()

                        project = models.Project(
                            hash_id=uuid4(),
                            id=project_id,
                            description=f"Project created on {uploaded_datetime.isoformat()}",
                            upload=upload,
                        )
                        project.save()

                        print(f"Created project {project_id} in DB!")
                    else:
                        project = models.Project.objects.get(id=project_id)

                    obs = serializers.ObservationSerializer(data=request.data, context={"user": token.user})
                    if models.Observation.objects.filter(project=project, id=request.data["id"]).exists():
                        return Response("Observation already created so skipping", status=status.HTTP_201_CREATED)
                    if obs.is_valid():
                        obs.save()
                        print(f"Observation {request.data['id']} saved!")
                        return Response(obs.data, status=status.HTTP_201_CREATED)
                    logger.debug(request.data)
                    return Response(obs.errors, status=status.HTTP_400_BAD_REQUEST)

                except Exception as error:
                    print("An exception occurred:", error)
                    return Response({"error-message": error}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response(
                    {"status": "error", "message": f"Token given does not match a user."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except Exception as error:
            print("An exception occurred:", error)
            return Response(
                {"status": "error", "message": f"Invalid or expired token - {error}"}, status=status.HTTP_403_FORBIDDEN
            )

    return Response({"status": "error", "message": f"Not a POST request."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@transaction.atomic
def upload_beam(request):

    if request.method == "POST":

        # Get user specific data
        try:
            token_str = request.headers["Authorization"]

        except KeyError:
            return Response(
                {"status": "error", "message": f"Unable to pull out token of the request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Find token in the db
            token = Token.objects.get(key=token_str)
            if token is not None:

                print(f" --------------- Beam uploaded by user: {token.user} --------------- ")

                try:

                    # Check if beam has already been uploaded before.
                    proj = models.Project.objects.get(id=request.data["proj_id"])
                    obs = models.Observation.objects.get(project=proj, id=request.data["obs_id"])
                    if models.Beam.objects.filter(project=proj, observation=obs, index=request.data["index"]).exists():
                        return Response(
                            f"Beam '{request.data['index']}' for obsservation '{request.data['obs_id']}' already created so skipping",
                            status=status.HTTP_200_OK,
                        )

                    print("before serialiser for beam")
                    beam = serializers.BeamSerializer(data=request.data, context={"user": token.user})

                    if beam.is_valid():
                        beam.save()
                        print(f"Beam {request.data['index']} saved to {request.data['obs_id']}!")
                        return Response(beam.data, status=status.HTTP_201_CREATED)
                    logger.debug(request.data)
                    return Response(beam.errors, status=status.HTTP_400_BAD_REQUEST)

                except Exception as error:
                    print("An exception occurred:", error)
                    return Response({"error-message": error}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response(
                    {"status": "error", "message": f"Token given does not match a user."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except Exception as error:
            print("An exception occurred:", error)
            return Response(
                {"status": "error", "message": f"Invalid or expired token - {error}"}, status=status.HTTP_403_FORBIDDEN
            )

    return Response({"status": "error", "message": f"Not a POST request."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@transaction.atomic
def upload_candidate(request):

    if request.method == "POST":

        # Get user specific data
        try:
            token_str = request.headers["Authorization"]

        except KeyError:
            return Response(
                {"status": "error", "message": f"Unable to pull out token of the request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Find token in the db
            token = Token.objects.get(key=token_str)
            if token is not None:

                print(f" --------------- Candidate uploaded by user: {token.user} --------------- ")

                cand_obj_id = request.data["cand_obj_id"]
                proj = models.Project.objects.get(id=request.data["proj_id"])
                obs = models.Observation.objects.get(project=proj, id=request.data["obs_id"])
                beam = models.Beam.objects.get(project=proj, observation=obs, index=request.data["beam_index"])
                if models.Candidate.objects.filter(
                    project=proj,
                    observation=obs,
                    beam=beam,
                    cand_obj_id=cand_obj_id,
                ).exists():
                    return Response(
                        f"Candidate '{cand_obj_id}' has already been uploaded/created so skipping",
                        status=status.HTTP_200_OK,
                    )

                cand = serializers.CandidateSerializer(data=request.data, context={"user": token.user})

                if cand.is_valid():
                    cand.save()
                    print(cand.data)
                    return Response(f"Data from - {cand.data}", status=status.HTTP_201_CREATED)

                logger.debug(request.data)
                return Response(f"{cand.errors}", status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response(
                    {"status": "error", "message": f"Token given does not match a user."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        except Exception as error:
            print("An exception occurred:", error)
            return Response(
                {"status": "error", "message": f"Invalid or expired token - {error}"}, status=status.HTTP_403_FORBIDDEN
            )

    return Response({"status": "error", "message": f"Not a POST request."}, status=status.HTTP_400_BAD_REQUEST)


@login_required(login_url="/")
def page_admin(request: HttpRequest):
    """Display a summary details about each project, observation and the space used internal to the webapp."""

    selected_project_hash_id = request.session.get("selected_project_hash_id")

    if selected_project_hash_id:
        selected_projects = [models.Project.objects.get(hash_id=selected_project_hash_id)]
    else:
        selected_projects = models.Project.objects.all()

    annotated_projects = []

    for project in selected_projects:
        observations = project.obs_proj.annotate(
            candidate_count=Count("cand_obs"),
            rated_candidate_count=Count("cand_obs__rating"),
        )

        annotated_projects.append({"project": project, "observations": observations})

    # Get disk space used by projects
    total_disk_space, used_disk_space, free_disk_space = get_disk_space(MEDIA_ROOT)

    print(annotated_projects)

    context = {
        "annotated_projects": annotated_projects,
        "free_disk_space": free_disk_space,
        "used_disk_space": used_disk_space,
        "total_disk_space": total_disk_space,
    }

    return render(request, "candidate_app/page_admin.html", context)


@login_required(login_url="/")
def delete(request: HttpRequest):
    """Using a authorised POST request, delete records from the DB."""

    if request.user.is_staff and "recordType" in request.POST:

        record_type = request.POST.get("recordType")

        if record_type == "project":
            to_delete = request.POST.get("hashId")
            print(f"Attempting to delete project: {to_delete}")

            try:
                # Delete project record and cascading objects
                project = models.Project.objects.get(hash_id=to_delete)
                project.delete()

                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=201)
            except:
                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=500)

        if record_type == "observation":
            to_delete = request.POST.get("hashId")
            print(f"Attempting to delete observation: {to_delete}")

            try:
                # Delete observation record and cascading records obs > beams > cands
                observation = models.Observation.objects.get(hash_id=to_delete)
                observation.delete()

                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=201)
            except:
                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=500)

        if record_type == "beam":
            to_delete = request.POST.get("hashId")
            print(f"Attempting to delete beam: {to_delete}")

            try:
                # Delete beam record and cascading records beams > cands
                beam = models.Beam.objects.get(hash_id=to_delete)
                beam.delete()

                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=201)
            except:
                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=500)

        if record_type == "candidate":
            to_delete = request.POST.get("hashId")
            print(f"Attempting to delete candidate: {to_delete}")

            try:
                # Delete beam record and cascading records beams > cands
                beam = models.Candidate.objects.get(hash_id=to_delete)
                beam.delete()

                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=201)
            except:
                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=500)

        if record_type == "rating":
            to_delete = request.POST.get("hashId")
            print(f"Attempting to delete rating: {to_delete}")

            try:
                # Delete beam record and cascading records beams > cands
                beam = models.Rating.objects.get(hash_id=to_delete)
                beam.delete()

                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=201)
            except:
                return JsonResponse({"deleted_recordType": record_type, "deleted_hashId": to_delete}, status=500)

    else:

        return JsonResponse({"message": f"User {request.user} is not authorised to delete records."}, status=500)


@login_required(login_url="/")
def download_lightcurve_csv(request: HttpRequest, cand_hash_id: str):
    """Download path for the candidate lightcurve csv file."""

    if request.method == "GET":

        candidate = get_object_or_404(models.Candidate, hash_id=cand_hash_id)

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{candidate.name}_lightcurve.csv"'

        writer = csv.writer(response)

        for row in candidate.lightcurve_data:
            writer.writerow(row)

        return response


class AppChangePassword(TemplateView, View):

    def get(self, request, *args, **kwargs):
        return self.render_to_response({})

    def post(self, request, *args, **kwargs):
        """Allow users to change their own password."""

        pw_reset_form = PasswordChangeForm(request.user, request.POST)
        if pw_reset_form.is_valid():
            user = pw_reset_form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, "Your password was successfully updated!")
        else:
            print(pw_reset_form.errors.as_data())
            for field, errors in pw_reset_form.errors.as_data().items():
                for error in errors:
                    message = error.message % error.params if error.params else error.message
                    messages.error(request, f"{message}")

        return redirect(request.META["HTTP_REFERER"])


class LoginView(TemplateView, View):
    def get(self, request, *args, **kwargs):
        return self.render_to_response({})

    def post(self, request, *args, **kwargs):
        user = authenticate(username=request.POST.get("username"), password=request.POST.get("password"))
        if user is not None:
            if user.is_active:
                login(request, user)
            else:
                messages.warning(request, "The password is valid, but the account has been disabled!")
        else:
            messages.warning(request, "The username or password were incorrect.")

        return redirect(request.POST.get("next", "/"))


class LogoutView(View):
    def post(self, request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/")
        logout(request)
        messages.success(request, "You are now logged out!")
        return redirect("/")
