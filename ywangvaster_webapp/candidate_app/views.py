import csv
import json
import logging
import random
from uuid import uuid4

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from astropy import units
from astropy.coordinates import Angle, SkyCoord
from astropy.time import Time
from astroquery.simbad import Simbad
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Q, F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django_q3c.expressions import Q3CRadialQuery, Q3CDist
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ywangvaster_webapp.settings import MEDIA_ROOT

from .utils import count_files, download_fits, get_disk_space

from django.http import HttpRequest
from django.views.generic import TemplateView, View
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q

from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from django.shortcuts import render

from . import forms, models, serializers

logger = logging.getLogger(__name__)


table_display_col_mapping = {
    "chi_square": "Chi Square",
}


def home_page(request):
    """Render the home page html."""

    page_context = {}

    return render(request, "candidate_app/home_page.html", page_context)


def cone_search_simbad(request):  # , ra_deg, dec_deg, dist_arcmin):
    ra_deg = 0
    dec_deg = 0
    dist_arcmin = 2
    if request.method == "POST":
        data = json.loads(request.body.decode())
        ra_deg = Angle(data.get("ra_str"), unit=units.hour).deg
        dec_deg = Angle(data.get("dec_str"), unit=units.deg).deg
        dist_arcmin = float(data.get("dist_arcmin", 1))

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
            ra = simbad_coord.ra.to_string(unit=units.hour, sep=":")[:11]
            dec = simbad_coord.dec.to_string(unit=units.deg, sep=":")[:11]
            sep = coord.separation(simbad_coord).arcminute
            simbad_result_table.append(
                {
                    "name": result["MAIN_ID"],
                    "search_term": search_term,
                    "ra": ra,
                    "dec": dec,
                    "sep": sep,
                }
            )
    return render(
        request,
        "candidate_app/nearby_object_tables/simbad.html",
        context={"simbad_result_table": simbad_result_table},
    )


def cone_search(request):
    if request.method == "POST":
        data = json.loads(request.body.decode())
        ra_str = data.get("ra_str", 0)
        dec_str = data.get("dec_str", 0)
        dist_arcmin = float(data.get("dist_arcmin", 30))
        exclude_hash_id = data.get("exclude_id", None)
        project = data.get("project", None)

        table = models.Candidate.objects.all()

        # Restrict project if given
        if project:
            table = table.filter(project__hash_id=project)

        # if we are given a candidate ID then exclude it from the results
        if exclude_hash_id:
            table = table.exclude(hash_id=exclude_hash_id)

        table = filter_candidates_by_coords(
            table,
            ra_str,
            dec_str,
            ra_col="ra",
            dec_col="dec",
            arcmin_search_radius=dist_arcmin,
            annotate=True,
        )

        table = table.values()
    else:
        table = []
    return render(
        request,
        "candidate_app/nearby_object_tables/cone_search.html",
        context={"table": table},
    )


def cone_search_pulsars(request):
    if request.method == "POST":
        data = json.loads(request.body.decode())
        print(data)

        ra_str = data.get("ra_str")
        dec_str = data.get("dec_str")

        ra = Angle(ra_str, unit=units.hour)
        dec = Angle(dec_str, unit=units.deg)
        dist_arcmin = float(data.get("dist_arcmin", 1))

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
                ra_str=ra_str,
                dec_str=dec_str,
                sep=Q3CDist(
                    ra1=F("raj"),
                    dec1=F("decj"),
                    ra2=ra.deg,
                    dec2=dec.deg,
                )
                * 60,  # arcsec -> degrees
            )
            .order_by("sep")
            .values()
        )

    else:
        table = []

    return render(
        request,
        "candidate_app/nearby_object_tables/atnf_pulsar.html",
        context={"table": table},
    )


@login_required(login_url="/")
def candidate_rating(request, cand_hash_id, arcmin=2):
    candidate = get_object_or_404(models.Candidate, hash_id=cand_hash_id)

    # Convert time to readable format
    time = candidate.observation.obs_start

    # Grab any previous ratings
    rating = models.Rating.objects.filter(candidate=candidate, user=request.user).first()

    rate_form = forms.RateCandidateForm()

    # This is a filter request.
    if request.method == "POST":

        rate_form = forms.RateCandidateForm(request.POST)

        print(f"trying to submit form for ------------------------- {cand_hash_id}")

        # if rate_form.is_valid():

        #     print(f"Attempting to create a rating form.")

        # Read info from form
        # Create the rating

        # Refresh page to go to next candidate?

        # Skip button??

    # # Convert seperation to arcminutes
    # if candidate.nks_sep_deg is None:
    #     sep_arcmin = None
    # else:
    #     sep_arcmin = candidate.nks_sep_deg * 60

    # Perform voevent database query
    # https://voeventdbremote.readthedocs.io/en/latest/notebooks/00_quickstart.html
    # conesearch skycoord and angle error
    # cand_err = Angle(arcmin, unit=units.arcmin)
    # cand_err = Angle(5,  unit=units.deg)
    # cone = (cand_coord, cand_err)

    # my_filters = {
    #     FilterKeys.role: "observation",
    #     FilterKeys.authored_since: time.tt.datetime - timedelta(hours=1),
    #     FilterKeys.authored_until: time.tt.datetime + timedelta(hours=1),
    #     # FilterKeys.authored_since: time.tt.datetime - timedelta(days=1),
    #     # FilterKeys.authored_until: time.tt.datetime + timedelta(days=1),
    #     FilterKeys.cone: cone,
    # }

    voevents = []

    converted_lc = []
    if candidate.lightcurve_data is not None:
        # Convert the lightcurve data to mJy
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
        "candidate": candidate,
        "rating": rating,
        "time": time,
        "rate_form": rate_form,
        # "sep_arcmin": sep_arcmin,
        "lightcurve_data": converted_lc,
        "arcmin_search": arcmin,
        "cand_type_choices": tuple((c.name, c.name) for c in models.Classification.objects.all()),
        "voevents": voevents,
    }
    return render(request, "candidate_app/candidate_rating_form.html", context)


# def voevent_view(request, id):
#     ivorn = models.xml_ivorns.objects.filter(id=id).first().ivorn
#     xml_packet = apiv1.packet_xml(ivorn)
#     v = voeventparse.loads(xml_packet)
#     xml_pretty_str = voeventparse.prettystr(v)
#     return HttpResponse(xml_pretty_str, content_type="text/xml")


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


@login_required(login_url="/")
@api_view(["POST"])
@transaction.atomic
def candidate_update_rating(request, hash_id):
    candidate = models.Candidate.objects.filter(hash_id=hash_id).first()
    if candidate is None:
        raise ValueError("Candidate not found")

    rating = models.Rating.objects.filter(candidate=candidate, user=request.user).first()
    if rating is None:
        # User hasn't made a rating of this cand so make one
        rating = models.Rating(
            candidate=candidate,
            user=request.user,
            rating=None,
        )

    classification = request.data.get("classification", None)
    if classification:
        rating.classification = models.Classification.objects.filter(name=classification).first()

    score = request.data.get("rating", None)
    if score:
        logger.debug("setting score %s=>%s", rating.rating, score)
        rating.rating = score

    # Update time
    rating.date = datetime.now(tz=timezone.utc)

    rating.save()

    # Update candidate notes
    notes = request.data.get("notes", "")
    if candidate.notes != notes:
        logger.debug("setting notes %s=>%s", candidate.notes, notes)
        candidate.notes = notes
    candidate.save()

    # Redirects to a random next candidate
    return redirect(reverse("candidate_random"))


# @login_required(login_url="/")
# @api_view(["POST"])
# @transaction.atomic
# def candidate_update_catalogue_query(request, id):
#     logger.debug(request.data)
#     candidate = models.Candidate.objects.filter(id=id).first()
#     if candidate is None:
#         raise ValueError("Candidate not found")
#     logger.debug("candidate obj %s", candidate)

#     arcmin = request.data.get("arcmin", None)
#     if arcmin:
#         logger.debug(f"New query with {arcmin}")
#         return candidate_rating(request, id, arcmin=arcmin)


### TODO: CHECK IF WE NEED THIS
@login_required(login_url="/")
def candidate_random(request):
    # Get session data for candidate ordering and inclusion settings
    session_settings = request.session.get("session_settings", 0)

    # deal with users who have no session settings
    if not session_settings:
        return render(request, "candidate_app/nothing_to_rate.html")

    user = request.user
    # choose all the candidates this user hasn't rated
    next_cands = models.Candidate.objects.exclude(rating__user=user)

    # filter based on selected project
    next_cands = next_cands.filter(project__name=session_settings["project"])

    # Filter candidates based on ranking
    if session_settings["filtering"] == "unrank":
        # Get unrated candidates
        next_cands = next_cands.filter(rating__isnull=True)
        if not next_cands.exists():
            return render(
                request,
                "candidate_app/nothing_to_rate.html",
                {"project": session_settings["project"]},
            )
    elif session_settings["filtering"] == "old":
        # Get candidates the user hasn't recently ranked
        next_cands = next_cands.exclude(rating__date__gte=datetime.now() - timedelta(days=7))
        if not next_cands.exists():
            return render(
                request,
                "candidate_app/nothing_to_rate.html",
                {"project": session_settings["project"]},
            )

    # Filter based on observation frequencies (+/- 1 MHz)
    if session_settings["exclude_87"]:
        next_cands = next_cands.exclude(obs_id__cent_freq__lt=87.68 + 1, obs_id__cent_freq__gt=87.68 - 1)
    if session_settings["exclude_118"]:
        next_cands = next_cands.exclude(obs_id__cent_freq__lt=118.50 + 1, obs_id__cent_freq__gt=118.50 - 1)
    if session_settings["exclude_154"]:
        next_cands = next_cands.exclude(obs_id__cent_freq__lt=154.24 + 1, obs_id__cent_freq__gt=154.24 - 1)
    if session_settings["exclude_184"]:
        next_cands = next_cands.exclude(obs_id__cent_freq__lt=184.96 + 1, obs_id__cent_freq__gt=184.96 - 1)
    if session_settings["exclude_200"]:
        next_cands = next_cands.exclude(obs_id__cent_freq__lt=200.32 + 1, obs_id__cent_freq__gt=200.32 - 1)
    if session_settings["exclude_215"]:
        next_cands = next_cands.exclude(obs_id__cent_freq__lt=215.68 + 1, obs_id__cent_freq__gt=215.68 - 1)

    # Use session data to decide candidate order
    if session_settings["ordering"] == "rand":
        candidate = random.choice(list(next_cands))
    elif session_settings["ordering"] == "new":
        candidate = next_cands.order_by("-obs_id__starttime").first()
    elif session_settings["ordering"] == "old":
        candidate = next_cands.order_by("obs_id__starttime").first()
    elif session_settings["ordering"] == "brig":
        candidate = next_cands.order_by("-can_peak_flux").first()
    elif session_settings["ordering"] == "faint":
        candidate = next_cands.order_by("can_peak_flux").first()
    return redirect(reverse("candidate_rating", args=(candidate.id,)))


def filter_candidates_by_coords(
    incoming: List[models.Candidate],
    ra_str: str,
    dec_str: str,
    ra_col: str,
    dec_col: str,
    arcmin_search_radius: float,
    annotate: Optional[bool] = False,
):
    """Convert from str ra_hms and dec_dms to degrees and filter candidates that are within the arcmin_search_radius."""

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
def clear_candidate_table_filter(request):
    if "current_filter_data" in request.session:
        del request.session["current_filter_data"]
    return redirect("/candidate_table/")


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


@login_required(login_url="/")
def candidate_table(request):

    # Get session data to keep filters when changing page
    session_settings = request.session.get("session_settings", 0)
    candidate_table_session_data = request.session.get("current_filter_data")

    # Get the max and mins from the materialised view table
    aggregates = models.CandidateMinMaxStats.objects.values().last()

    cand_values = {}
    for variable in FILTER_FORM_FLOAT_VARAIBLES:
        temp = {}
        for x in ["min", "max"]:
            temp[x] = aggregates[f"{x}_{variable}"]

        # These low and highs are the values that the user set before.
        temp["gte"] = "null"
        temp["lte"] = "null"

        cand_values[variable] = temp

    # This is a filter request.
    if request.method == "POST":

        form = forms.CandidateFilterForm(request.POST)

        if form.is_valid():

            if form.cleaned_data["observation_id"] is None:
                observation_id_filter = None
            else:
                observation_id_filter = form.cleaned_data["observation_id"]

            cleaned_data = {**form.cleaned_data}
            cleaned_data["observation_id"] = observation_id_filter
            request.session["current_filter_data"] = cleaned_data
            candidate_table_session_data = cleaned_data

            cand_ra_str = candidate_table_session_data["cand_ra_str"]
            cand_dec_str = candidate_table_session_data["cand_dec_str"]
            cand_arcmin_search_radius = candidate_table_session_data["cand_arcmin_search_radius"]

            beam_ra_str = candidate_table_session_data["beam_ra_str"]
            beam_dec_str = candidate_table_session_data["beam_dec_str"]
            beam_arcmin_search_radius = candidate_table_session_data["beam_arcmin_search_radius"]

            deep_ra_str = candidate_table_session_data["deep_ra_str"]
            deep_dec_str = candidate_table_session_data["deep_dec_str"]
            deep_arcmin_search_radius = candidate_table_session_data["deep_arcmin_search_radius"]

    # Page is loaded normall
    else:

        form = forms.CandidateFilterForm()
        observation_id_filter = None

        cand_ra_str = None
        cand_dec_str = None
        cand_arcmin_search_radius = 2

        beam_ra_str = None
        beam_dec_str = None
        beam_arcmin_search_radius = 2

        deep_ra_str = None
        deep_dec_str = None
        deep_arcmin_search_radius = 2

        # This is a dictionary of floats
        floats_filter_criteria = None

    filtered_columns = set()
    if candidate_table_session_data:
        # Prefil form with previous session results
        form = forms.CandidateFilterForm(
            initial=candidate_table_session_data,
        )

        cand_ra_str = candidate_table_session_data["cand_ra_str"]
        cand_dec_str = candidate_table_session_data["cand_dec_str"]
        cand_arcmin_search_radius = candidate_table_session_data["cand_arcmin_search_radius"]

        beam_ra_str = candidate_table_session_data["beam_ra_str"]
        beam_dec_str = candidate_table_session_data["beam_dec_str"]
        beam_arcmin_search_radius = candidate_table_session_data["beam_arcmin_search_radius"]

        deep_ra_str = candidate_table_session_data["deep_ra_str"]
        deep_dec_str = candidate_table_session_data["deep_dec_str"]
        deep_arcmin_search_radius = candidate_table_session_data["deep_arcmin_search_radius"]

        # Set the float slider values to what they were before the page load.
        for variable in FILTER_FORM_FLOAT_VARAIBLES:
            for x in ["gte", "lte"]:
                cand_values[variable][x] = candidate_table_session_data[f"{variable}__{x}"]

        # Find values that are different and make filtering dict from those
        # Get floats out and remove Nones
        floats_filter_criteria = {}
        for variable in FILTER_FORM_FLOAT_VARAIBLES:
            agg_min = float(aggregates[f"min_{variable}"]) if aggregates[f"min_{variable}"] is not None else None
            agg_max = float(aggregates[f"max_{variable}"]) if aggregates[f"max_{variable}"] is not None else None

            # For the min side
            if (
                candidate_table_session_data[f"{variable}__gte"] is not None
                and candidate_table_session_data[f"{variable}__gte"] != agg_min
            ):
                floats_filter_criteria[f"{variable}__gte"] = candidate_table_session_data[f"{variable}__gte"]
                filtered_columns.add(variable)

            # For the max side
            if (
                candidate_table_session_data[f"{variable}__lte"] is not None
                and candidate_table_session_data[f"{variable}__lte"] != agg_max
            ):
                floats_filter_criteria[f"{variable}__lte"] = candidate_table_session_data[f"{variable}__lte"]
                filtered_columns.add(variable)

    # Gather all the cand types and prepare them as kwargs
    count_kwargs = {}
    column_type_to_name = {}
    for cand_type_tuple in [c.name for c in models.Classification.objects.all()]:
        cand_type_short = cand_type_tuple
        count_kwargs[f"{cand_type_short}_count"] = Count(
            "rating", filter=Q(rating__classification__name=cand_type_short)
        )
        # Also create a column name
        column_type_to_name[cand_type_short] = cand_type_short

    candidates = models.Candidate.objects.all()
    project = "All projects"
    if session_settings:
        candidates = candidates.filter(project__name=session_settings["project"])
        project = "Project " + session_settings["project"]

    # These are the sliders that are used for filtering the candidates.
    if floats_filter_criteria:
        candidates = candidates.filter(**{key: value for key, value in floats_filter_criteria.items()})

    # # Annotate with counts of different candidate type counts
    # candidates = candidates.annotate(
    #     num_ratings=Count("rating"),
    #     avg_rating=Avg("rating__rating"),
    #     **count_kwargs,
    # )

    # If user only wants to display a single column annotate it and return it's name
    # if column_display:
    #     candidates = candidates.annotate(
    #         selected_count=Count("rating", filter=Q(rating__classification__name=column_display)),
    #     )
    #     # # Filter data to only show candidates with at least one count
    #     # candidates = candidates.filter(selected_count__gte=1)
    #     selected_column = column_type_to_name[column_display]
    # else:
    #     selected_column = None

    # # Ratings filter
    # if rating_cutoff is not None:
    #     candidates = candidates.filter(avg_rating__gte=rating_cutoff)

    # Order by the column the user clicked or by avg_rating by default
    # candidates = candidates.order_by(asc_dec + order_by, "-avg_rating")

    # Obsid filter
    # if observation_id_filter is not None:
    #     candidates = candidates.filter(obs_id__observation=observation_id_filter)

    # Filter candidate by cone search of
    candidates = filter_candidates_by_coords(
        candidates,
        cand_ra_str,
        cand_dec_str,
        "ra",
        "dec",
        cand_arcmin_search_radius,
    )

    # Filter candidate by beam position
    candidates = filter_candidates_by_coords(
        candidates,
        beam_ra_str,
        beam_dec_str,
        "beam_ra",
        "beam_dec",
        beam_arcmin_search_radius,
    )

    # Filter candidate by deep position
    candidates = filter_candidates_by_coords(
        candidates,
        deep_ra_str,
        deep_dec_str,
        "deep_ra",
        "deep_dec",
        deep_arcmin_search_radius,
    )

    # Paginate
    paginator = Paginator(candidates, 25)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    content = {
        "page_obj": page_obj,
        "form": form,
        "project_name": project,
        "cand_values": cand_values,
        "filtered_columns": filtered_columns,
    }
    return render(request, "candidate_app/candidate_table.html", content)


@login_required(login_url="/")
def session_settings(request):
    # Get session data to keep filters when changing page
    session_settings = request.session.get("session_settings", 0)
    # print(session_settings)

    # Check filter form
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = forms.SessionSettingsForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            cleaned_data = {**form.cleaned_data}
            request.session["session_settings"] = cleaned_data
            # print("here", cleaned_data)
    else:
        if session_settings != 0:
            # Prefil form with previous session results
            form = forms.SessionSettingsForm(
                initial=session_settings,
            )
        else:
            form = forms.SessionSettingsForm()
    context = {
        "form": form,
        "order_choices": form.fields["ordering"].choices,
        "filter_choices": form.fields["filtering"].choices,
        "project_choices": form.fields["project"].choices,
    }

    return render(request, "candidate_app/session_settings.html", context)


# def survey_status(request):
#     # Order by the column the user clicked or by observation_id by default
#     order_by = request.GET.get("order_by", "observation_id")
#     obs_list = (
#         models.Observation.objects.all()
#         .annotate(
#             candidates=Count("candidate"),
#             rated_candidates=Count("candidate", filter=Q(candidate__rating__isnull=False)),
#         )
#         .order_by(order_by)
#     )
#     context = {"obs": obs_list}
#     return render(request, "candidate_app/survey_status.html", context)


def download_csv(request, queryset, table):
    if not request.user.is_staff:
        raise PermissionDenied
    opts = queryset.model._meta
    response = HttpResponse(content_type="text/csv")
    # force download.
    response["Content-Disposition"] = f'attachment; filename="{table}.csv"'
    # the csv writer
    writer = csv.writer(response)
    field_names = [field.name for field in opts.fields]
    # Write a first row with header information
    writer.writerow(field_names)
    # Write data rows
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])
    return response


# Unused
def download_data(request, table):
    if table == "user":
        from django.contrib.auth import get_user_model

        this_model = get_user_model()
    elif table == "rating":
        this_model = models.Rating
    elif table == "candidate":
        this_model = models.Candidate
    elif table == "observation":
        this_model = models.Observation
    elif table == "filter":
        this_model = models.Filter
    response = download_fits(request, this_model.objects.all(), table)
    # response = download_csv(request, this_model.objects.all(), table)
    return response


def ratings(request: HttpRequest):
    """Render the ratings template."""

    # Compile a list of ratings for the page,
    # Paginate the ratings to x per page.

    # Make data for echarts to plot the ratings

    # Allow for a download button for the ratings for a project_obsID_subset, etc

    context = {}

    return render(request, "candidate_app/ratings.html", context)


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
                beam = models.Beam.objects.get(project=proj, observation=obs)
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
    """Display a summary details about each project, observatio and the space used internal to the webapp."""

    # Order by the column the user clicked or by observation_id by default
    # order_by = request.GET.get("order_by", "")

    print(
        f"************************** is user {request.user.id} staff: {request.user.is_staff} *********************************"
    )

    projects_obs = {}
    for project in models.Project.objects.all():

        obs_list = []
        for obs in models.Observation.objects.filter(project=project):

            temp = {}

            beams = models.Beam.objects.filter(project=project, observation=obs)
            candidates = models.Candidate.objects.filter(project=project, observation=obs)

            temp["obj"] = obs
            temp["num_beams"] = len(beams)
            temp["num_cands"] = len(candidates)

            obs_list.append(temp)

        projects_obs[project.id] = obs_list

    print("++++++++++++++++++++++++ project_obs ++++++++++++++++++++++++")
    print(projects_obs)

    # Get disk space used by projects
    total_disk_space, used_disk_space, free_disk_space = get_disk_space(MEDIA_ROOT)

    context = {
        "projects_obs": projects_obs,
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
