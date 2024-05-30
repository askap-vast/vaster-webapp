# from mwa_trigger.parse_xml import parsed_VOEvent
import os
import re
import csv
import json
import logging
import random
from datetime import datetime, timedelta
from typing import List, Tuple

import voeventdb.remote.apiv1 as apiv1
import voeventparse
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
from .utils import download_fits

from django.http import HttpRequest
from django.views.generic import TemplateView, View
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
import base64
from django.http import JsonResponse, HttpResponseForbidden


from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from django.shortcuts import render
from .forms import RangeSliderForm

# from voeventdb.remote.apiv1 import FilterKeys, OrderValues

from . import forms, models, serializers

logger = logging.getLogger(__name__)


def home_page(request):
    return render(request, "candidate_app/home_page.html")


def cone_search_simbad(request):  # , ra_deg, dec_deg, dist_arcmin):
    ra_deg = 0
    dec_deg = 0
    dist_arcmin = 2
    if request.method == "POST":
        data = json.loads(request.body.decode())
        ra_deg = data.get("ra_deg", 0)
        dec_deg = data.get("dec_deg", 0)
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
        "candidate_app/simbad_table.html",
        context={"simbad_result_table": simbad_result_table},
    )


def cone_search(request):
    if request.method == "POST":
        data = json.loads(request.body.decode())
        ra_deg = data.get("ra_deg", 0)
        dec_deg = data.get("dec_deg", 0)
        dist_arcmin = data.get("dist_arcmin", 1)
        exclude = data.get("exclude_id", None)
        project = data.get("project", None)

        # Find nearby candidates
        table = models.Candidate.objects

        # Restrict project if given
        if project:
            table = table.filter(project__name=project)

        # if we are given a candidate ID then exclude it from the results
        if exclude:
            table = table.exclude(id=exclude)

        table = (
            table.filter(
                Q(
                    Q3CRadialQuery(
                        center_ra=ra_deg,
                        center_dec=dec_deg,
                        ra_col="ra_deg",
                        dec_col="dec_deg",
                        radius=float(dist_arcmin) / 60.0,
                    )
                )
            )
            .annotate(  # do the distance calcs in the db
                sep=Q3CDist(
                    ra1=F("ra_deg"),
                    dec1=F("dec_deg"),
                    ra2=ra_deg,
                    dec2=dec_deg,
                )
                * 60  # arcsec -> degrees
            )
            .order_by("sep")
        )

        table = table.values()
    else:
        table = []
    return render(
        request,
        "candidate_app/cone_search_table.html",
        context={"table": table},
    )


def cone_search_pulsars(request):
    if request.method == "POST":
        data = json.loads(request.body.decode())
        print(data)
        ra_deg = float(data.get("ra_deg", 0))
        dec_deg = float(data.get("dec_deg", 0))
        dist_arcmin = float(data.get("dist_arcmin", 1))
        # Perform atnf query
        table = (
            models.ATNFPulsar.objects.filter(
                Q(
                    Q3CRadialQuery(
                        center_ra=ra_deg,
                        center_dec=dec_deg,
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
                    ra2=ra_deg,
                    dec2=dec_deg,
                )
                * 60  # arcsec -> degrees
            )
            .order_by("sep")
            .values()
        )

    else:
        table = []

    return render(
        request,
        "candidate_app/atnf_pulsar_table.html",
        context={"table": table},
    )


@login_required(login_url="/")
def candidate_rating(request, id, arcmin=2):
    candidate = get_object_or_404(models.Candidate, id=id)

    # Convert time to readable format
    time = Time(Time(candidate.obs_id.starttime, format="gps"), format="iso", scale="utc")

    # Grab any previous ratings
    u = request.user
    rating = models.Rating.objects.filter(candidate=candidate, user=u).first()

    # Convert seperation to arcminutes
    if candidate.nks_sep_deg is None:
        sep_arcmin = None
    else:
        sep_arcmin = candidate.nks_sep_deg * 60

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

    context = {
        "candidate": candidate,
        "rating": rating,
        "time": time,
        "sep_arcmin": sep_arcmin,
        "arcmin_search": arcmin,
        "cand_type_choices": tuple((c.name, c.name) for c in models.Classification.objects.all()),
        "voevents": voevents,
    }
    return render(request, "candidate_app/candidate_rating_form.html", context)


def voevent_view(request, id):
    ivorn = models.xml_ivorns.objects.filter(id=id).first().ivorn
    xml_packet = apiv1.packet_xml(ivorn)
    v = voeventparse.loads(xml_packet)
    xml_pretty_str = voeventparse.prettystr(v)
    return HttpResponse(xml_pretty_str, content_type="text/xml")


@login_required(login_url="/")
def token_manage(request):
    u = request.user
    print("username: ", u)
    token = Token.objects.filter(user=u).first()
    return render(request, "candidate_app/token_manage.html", {"token": token})


@login_required(login_url="/")
def token_create(request):
    u = request.user
    token = Token.objects.filter(user=u)
    if token.exists():
        token.delete()
    Token.objects.create(user=u)
    return redirect(reverse("token_manage"))


@login_required(login_url="/")
@api_view(["POST"])
@transaction.atomic
def candidate_update_rating(request, id):
    candidate = models.Candidate.objects.filter(id=id).first()
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


@login_required(login_url="/")
@api_view(["POST"])
@transaction.atomic
def candidate_update_catalogue_query(request, id):
    logger.debug(request.data)
    candidate = models.Candidate.objects.filter(id=id).first()
    if candidate is None:
        raise ValueError("Candidate not found")
    logger.debug("candidate obj %s", candidate)

    arcmin = request.data.get("arcmin", None)
    if arcmin:
        logger.debug(f"New query with {arcmin}")
        return candidate_rating(request, id, arcmin=arcmin)


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


def candidate_table(request):

    # Get session data to keep filters when changing page
    session_settings = request.session.get("session_settings", 0)
    candidate_table_session_data = request.session.get("current_filter_data", 0)
    print(candidate_table_session_data)

    # Check filter form
    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = forms.CandidateFilterForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            column_display = form.cleaned_data["column_display"]
            if form.cleaned_data["observation_id"] is None:
                observation_id_filter = None
            else:
                observation_id_filter = form.cleaned_data["observation_id"].observation_id
            rating_cutoff = form.cleaned_data["rating_cutoff"]
            order_by = form.cleaned_data["order_by"]
            asc_dec = form.cleaned_data["asc_dec"]
            cleaned_data = {**form.cleaned_data}
            cleaned_data["observation_id"] = observation_id_filter
            request.session["current_filter_data"] = cleaned_data
            ra_hms = form.cleaned_data["ra_hms"]
            dec_dms = form.cleaned_data["dec_dms"]
            search_radius_arcmin = form.cleaned_data["search_radius_arcmin"]
    else:
        if candidate_table_session_data != 0:
            # Prefil form with previous session results
            form = forms.CandidateFilterForm(
                initial=candidate_table_session_data,
            )
            column_display = candidate_table_session_data["column_display"]
            observation_id_filter = candidate_table_session_data["observation_id"]
            rating_cutoff = candidate_table_session_data["rating_cutoff"]
            order_by = candidate_table_session_data["order_by"]
            asc_dec = candidate_table_session_data["asc_dec"]
            ra_hms = candidate_table_session_data["ra_hms"]
            dec_dms = candidate_table_session_data["dec_dms"]
            search_radius_arcmin = candidate_table_session_data["search_radius_arcmin"]
        else:
            form = forms.CandidateFilterForm()
            column_display = None
            observation_id_filter = None
            rating_cutoff = None
            order_by = "avg_rating"
            asc_dec = "-"
            ra_hms = None
            dec_dms = None
            search_radius_arcmin = 2

    print(f"column_display: {column_display}")
    print(f"observation_id_filter: {observation_id_filter}")
    print(f"rating_cutoff: {rating_cutoff}")
    print(f"order_by: {order_by}")
    print(f"asc_dec: {asc_dec}")

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
    # Annotate with counts of different candidate type counts
    candidates = candidates.annotate(
        num_ratings=Count("rating"),
        avg_rating=Avg("rating__rating"),
        **count_kwargs,
    )

    # If user only wants to display a single column annotate it and return it's name
    if column_display:
        candidates = candidates.annotate(
            selected_count=Count("rating", filter=Q(rating__classification__name=column_display)),
        )
        # # Filter data to only show candidates with at least one count
        # candidates = candidates.filter(selected_count__gte=1)
        selected_column = column_type_to_name[column_display]
    else:
        selected_column = None

    # Ratings filter
    if rating_cutoff is not None:
        candidates = candidates.filter(avg_rating__gte=rating_cutoff)

    # Obsid filter
    if observation_id_filter is not None:
        candidates = candidates.filter(obs_id__observation_id=observation_id_filter)

    # Order by the column the user clicked or by avg_rating by default
    candidates = candidates.order_by(asc_dec + order_by, "-avg_rating")

    # Filter by position
    if not (None in (ra_hms, dec_dms) or ra_hms == "" or dec_dms == ""):
        ra_deg = Angle(ra_hms, unit=units.hour).deg
        dec_deg = Angle(dec_dms, unit=units.deg).deg
        candidates = candidates.filter(
            Q(
                Q3CRadialQuery(
                    center_ra=ra_deg,
                    center_dec=dec_deg,
                    ra_col="ra_deg",
                    dec_col="dec_deg",
                    radius=search_radius_arcmin / 60.0,
                )
            )
        )

    # Paginate
    paginator = Paginator(candidates, 25)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    form_slider = RangeSliderForm()

    # print(form_slider)

    content = {
        "page_obj": page_obj,
        "form": form,
        "selected_column": selected_column,
        "column_names": column_type_to_name,
        "project_name": project,
        # "form_slider": form_slider,
    }
    return render(request, "candidate_app/candidate_table.html", content)


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


@api_view(["POST"])
@transaction.atomic
def observation_create(request):
    obs = serializers.ObservationSerializer(data=request.data)
    if models.Observation.objects.filter(observation_id=request.data["observation_id"]).exists():
        return Response("Observation already created so skipping", status=status.HTTP_201_CREATED)
    if obs.is_valid():
        obs.save()
        return Response(obs.data, status=status.HTTP_201_CREATED)
    logger.debug(request.data)
    return Response(obs.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@transaction.atomic
def candidate_create(request):
    # Get or create filter
    filter_name = request.data.get("filter_id")
    if models.Filter.objects.filter(name=filter_name).exists():
        filter = models.Filter.objects.filter(name=filter_name).first()
    else:
        filter = models.Filter.objects.create(name=filter_name)
    request.data["filter"] = filter.id

    cand = serializers.CandidateSerializer(data=request.data)
    png_file = request.data.get("png")
    gif_file = request.data.get("gif")
    if cand.is_valid():
        # Find obsid
        # obs = models.Observation.objects.filter(observation_id=obsid).first()
        if png_file is None:
            return Response("Missing png file", status=status.HTTP_400_BAD_REQUEST)
        if gif_file is None:
            return Response("Missing gif file", status=status.HTTP_400_BAD_REQUEST)
        cand.save(png_path=png_file, gif_path=gif_file, filter=filter)
        return Response(cand.data, status=status.HTTP_201_CREATED)
    logger.debug(request.data)
    logger.error(cand.errors)
    return Response(cand.errors, status=status.HTTP_400_BAD_REQUEST)


def survey_status(request):
    # Order by the column the user clicked or by observation_id by default
    order_by = request.GET.get("order_by", "observation_id")
    obs_list = (
        models.Observation.objects.all()
        .annotate(
            candidates=Count("candidate"),
            rated_candidates=Count("candidate", filter=Q(candidate__rating__isnull=False)),
        )
        .order_by(order_by)
    )
    context = {"obs": obs_list}
    return render(request, "candidate_app/survey_status.html", context)


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


# Receive data from
@api_view(["POST"])
def upload_candidate(request):
    if request.method == "POST":

        # Get user specific data
        try:
            token_str = request.headers["Authorization"]

        except KeyError:
            return JsonResponse(
                {"status": "error", "message": f"Unable to pull out token of the request."},
                status=400,
            )

        try:
            # Find token in the db
            token = Token.objects.get(key=token_str)
            if token is not None:

                print(f" --------------- Candidate uploaded by user: {token.user} --------------- ")

                # Save the candidate data to DB.
                try:
                    cand_data = request.POST
                    project_id = cand_data["project_id"]
                    survey_id = cand_data["survey_id"]
                    beam_id = cand_data["beam_id"]
                    cand_id = cand_data["name"]

                    # Path for the candidate files.
                    upload_dir = f"/ywangvaster_media/{project_id}/{survey_id}/{beam_id}/{cand_id}/"
                    os.makedirs(upload_dir, exist_ok=True)

                    print(type(cand_data["lightcurve_local_rms"]))

                    # Save files to disk
                    for file, uploaded_file in request.FILES.items():
                        file_path = os.path.join(upload_dir, file)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.read())

                    print(f"Successfully saved candidate data to database - {survey_id}, {beam_id}, {cand_id}")

                    return JsonResponse(
                        {"status": "success", "survey_id": survey_id, "beam_id": beam_id, "cand_id": cand_id},
                        status=200,
                    )

                    # return JsonResponse({"status": "success", "message": "got data"}, status=200)
                except Exception as error:
                    print("An exception occurred:", error)
                    return JsonResponse({"status": "error", "message": error})

            else:
                return JsonResponse({"status": "error", "message": f"Token given does not match a user."})

        except Exception as error:
            print("An exception occurred:", error)
            return JsonResponse({"status": "error", "message": "Invalid or expired token"}, status=403)

    return HttpResponseForbidden()


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
