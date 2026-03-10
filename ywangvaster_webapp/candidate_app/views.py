import csv
import json
import logging
from uuid import uuid4
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash

from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator
from django.views.generic import TemplateView, View
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.authtoken.models import Token

from ywangvaster_webapp.settings import MEDIA_ROOT

from .utils import get_disk_space
from . import forms, models, serializers
from .views_utils import (
    CONFIDENCE_MAPPING,
    DEFAULT_RATINGS_INPUT,
    DOWNLOAD_CANDIDATE_FIELDS,
    FILTER_CAND_VAR_MAPPING,
    PROJECT_COLOURS,
    get_simbad,
    get_atnf,
    filter_candidates_by_coords,
    build_candidate_queryset,
    get_new_values_diff,
    download_rating_csv_zip,
    get_upload_token,
    get_session_filter_data,
)

logger = logging.getLogger(__name__)


DELETABLE_MODELS = {
    "project": models.Project,
    "observation": models.Observation,
    "beam": models.Beam,
    "candidate": models.Candidate,
    "rating": models.Rating,
}


def home(request):
    """Render the home page html."""
    staging_details = None
    if settings.STAGING:
        staging_details_path = settings.BASE_DIR / "staging-details.html"
        if staging_details_path.exists():
            staging_details = staging_details_path.read_text()
    print(staging_details)

    return render(
        request, "candidate_app/home.html", {"staging_details": staging_details}
    )


def nearby_objects_table(request: HttpRequest):
    """Render a table of nearby objects from the local DB (filtered by
    project), Simbad and ATNF pulsars."""

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

    # Sort results by separation
    sorted_results = sorted(result, key=lambda x: x["sep"], reverse=False)

    return render(
        request,
        "candidate_app/nearby_objects_table.html",
        context={"result_table": sorted_results},
    )


@login_required(login_url="/")
def create_tag(request: HttpRequest):
    if request.method == "POST":
        new_tag = forms.CreateTagForm(request.POST)

        print(f"Attempting to create new tag with request.POST: {request.POST}")

        if new_tag.is_valid():
            print(f"New tag is valid! Adding {request.POST['name']} DB.")

            new_tag.save()

            return redirect(request.META["HTTP_REFERER"])


@login_required(login_url="/")
def next_candidate(request):
    """Redirect the user to an unrated candidate, respecting session filters."""

    selected_project_hash_id = request.session.get("selected_project_hash_id")

    session_data, _, _, _ = get_session_filter_data(request)

    candidates = build_candidate_queryset(
        session_data, selected_project_hash_id, unrated_only=True
    )

    candidate = candidates.first()

    if candidate:
        return redirect(f"/candidate_rating/{str(candidate.hash_id)}")
    else:
        messages.error(request, "No unrated candidates found.")
        return redirect("/")


@login_required(login_url="/")
def candidate_rating(request, cand_hash_id, arcmin=2):
    candidate = get_object_or_404(models.Candidate, hash_id=cand_hash_id)

    # Convert time to readable format
    time = candidate.observation.obs_start

    # Grab the previous rating for this candidate and user
    try:
        prev_rating = models.Rating.objects.get(candidate=candidate)
    except Exception:
        prev_rating = None

    rate_form = forms.RateCandidateForm(initial={"confidence": "F", "tag": "None"})
    new_tag_form = forms.CreateTagForm()

    if request.method == "POST":
        rate_form = forms.RateCandidateForm(request.POST)

        if rate_form.is_valid():
            # Add tags to the rating (later there could be multiple tags per rating)
            tag_id = request.POST.get("tag")
            tag = models.Tag.objects.get(name=tag_id)

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
                tag=tag,
                date=timezone.now(),
            )

            if prev_rating:
                # Updating an existing rating: stay on the same page
                return redirect(request.META["HTTP_REFERER"])
            else:
                # New rating: go straight to the next unrated candidate
                return redirect("next_candidate")

    # Convert the lightcurve data to mJy and put into a form for Echarts to use.
    converted_lc = []
    if candidate.lightcurve_data is not None:
        converted_lc = []
        for row in candidate.lightcurve_data[1:]:
            try:
                val = float(row[1]) * 1000.0
                err = float(row[2]) * 1000.0
                converted_lc.append([row[0], str(val), str(err)])
            except ValueError as e:
                print(f"Value error: {e}")
                converted_lc.append([row[0], row[1], row[2]])

    session_data, _, _, default_all_values = get_session_filter_data(request)
    # Exclude 'rated' — next_candidate always overrides it to "false"
    filters_without_rated = {k: v for k, v in session_data.items() if k != "rated"}
    defaults_without_rated = {
        k: v for k, v in default_all_values.items() if k != "rated"
    }
    next_candidate_is_filtered = bool(
        get_new_values_diff(defaults_without_rated, filters_without_rated)
    )

    selected_project_hash_id = request.session.get("selected_project_hash_id")
    next_candidate_available = build_candidate_queryset(
        session_data, selected_project_hash_id, unrated_only=True
    ).exists()

    context = {
        "CONFIDENCE_MAPPING": CONFIDENCE_MAPPING,
        "candidate": candidate,
        "prev_rating": prev_rating,
        "time": time,
        "rate_form": rate_form,
        "new_tag_form": new_tag_form,
        "lightcurve_data": converted_lc,
        "arcmin_search": arcmin,
        "cand_type_choices": tuple((c.name, c.name) for c in models.Tag.objects.all()),
        "next_candidate_is_filtered": next_candidate_is_filtered,
        "next_candidate_available": next_candidate_available,
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
        except Exception:
            return JsonResponse(
                {"Error: Unable to create token for user": request.user}, status=500
            )


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

            request.session["selected_project_hash_id"] = request.POST[
                "selected_project_hash_id"
            ]

            print(
                f"setting selected_project_hash_id to {request.session['selected_project_hash_id']}"  # noqa: B950
            )

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


@login_required(login_url="/")
def candidate_table(request: HttpRequest):
    # Get session data to keep filters when changing page
    # This only holds what values are used for the filtering, not all.

    (
        candidate_table_session_data,
        default_inputs,
        default_float_values,
        default_all_values,
    ) = get_session_filter_data(request)

    selected_project_hash_id = request.session.get("selected_project_hash_id")

    if request.method == "GET" and request.GET:
        candidate_table_session_data.update(request.GET.dict())

        # Update the form values with the variables from url decode.
        if get_new_values_diff(default_all_values, candidate_table_session_data):
            form = forms.CandidateFilterForm(
                selected_project_hash_id=selected_project_hash_id,
                initial=candidate_table_session_data,
            )
        else:
            form = forms.CandidateFilterForm(
                selected_project_hash_id=selected_project_hash_id,
                initial=default_all_values,
            )

    # This is a filter request.
    if request.method == "POST":
        if get_new_values_diff(default_all_values, candidate_table_session_data):
            form = forms.CandidateFilterForm(
                request.POST,
                selected_project_hash_id=selected_project_hash_id,
                initial=candidate_table_session_data,
            )
        else:
            form = forms.CandidateFilterForm(
                request.POST,
                selected_project_hash_id=selected_project_hash_id,
                initial=default_all_values,
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

            print(f"Query url string: {query_string}")

            return redirect(f"{request.path}?{query_string}")
    else:
        if get_new_values_diff(default_all_values, candidate_table_session_data):
            form = forms.CandidateFilterForm(
                selected_project_hash_id=selected_project_hash_id,
                initial=candidate_table_session_data,
            )
        else:
            form = forms.CandidateFilterForm(
                selected_project_hash_id=selected_project_hash_id,
                initial=default_all_values,
            )

    inputs_to_filter = get_new_values_diff(default_inputs, candidate_table_session_data)
    floats_to_filter = get_new_values_diff(
        default_float_values, candidate_table_session_data
    )

    # Track filtered columns (display concern only) #

    filtered_columns = set()
    if floats_to_filter:
        filtered_columns = {key.split("__")[0] for key in floats_to_filter.keys()}

    confidence_filter = None
    if "confidence" in inputs_to_filter:
        filtered_columns.add("rating.confidence")
        confidence_filter = inputs_to_filter["confidence"]

    tag_filter_name = None
    if "tag" in inputs_to_filter:
        filtered_columns.add("rating.tag.name")
        tag_filter_name = models.Tag.objects.get(hash_id=inputs_to_filter["tag"]).name

    if "rated" in inputs_to_filter and inputs_to_filter["rated"] in ("true", "false"):
        filtered_columns.add("rating_count")

    if "observation" in inputs_to_filter:
        filtered_columns.add("observation.id")

    if "beam_index" in inputs_to_filter:
        filtered_columns.add("beam.index")

    if "deep_num" in inputs_to_filter:
        filtered_columns.add("deep_num")

    candidates = build_candidate_queryset(
        candidate_table_session_data, selected_project_hash_id
    )

    if (
        candidate_table_session_data["cand_ra_str"]
        and candidate_table_session_data["cand_dec_str"]
        and candidate_table_session_data["cand_arcmin_search_radius"]
    ):
        filtered_columns.add("cand_sep")

    if (
        candidate_table_session_data["beam_ra_str"]
        and candidate_table_session_data["beam_dec_str"]
        and candidate_table_session_data["beam_arcmin_search_radius"]
    ):
        filtered_columns.add("beam_sep")

    if (
        candidate_table_session_data["deep_ra_str"]
        and candidate_table_session_data["deep_dec_str"]
        and candidate_table_session_data["deep_arcmin_search_radius"]
    ):
        filtered_columns.add("deep_sep")

    # Paginate
    paginator = Paginator(candidates, 50)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    content = {
        "page_obj": page_obj,
        "form": form,
        "CONFIDENCE_MAPPING": CONFIDENCE_MAPPING,
        "default_float_values": default_float_values,
        "updated_float_values": candidate_table_session_data,
        "filtered_columns": filtered_columns,
        "column_labels": FILTER_CAND_VAR_MAPPING,
        "tag_filter_name": tag_filter_name,
        "confidence_filter": confidence_filter,
    }
    return render(request, "candidate_app/candidate_table.html", content)


@login_required(login_url="/")
def ratings_summary(request: HttpRequest):
    """Render the rating summary template."""

    selected_project_hash_id = request.session.get("selected_project_hash_id")
    print(f"selected_project_hash_id - {selected_project_hash_id}")

    current_ratings_filter = request.session.get(
        "current_ratings_filter", DEFAULT_RATINGS_INPUT
    )

    if selected_project_hash_id:
        ratings = models.Rating.objects.filter(
            candidate__project=selected_project_hash_id
        )
    else:
        ratings = models.Rating.objects.all()

    # Ratings table #

    # From the URL for the filter
    if request.method == "GET" and request.GET:
        current_ratings_filter.update(request.GET.dict())

        # Update the form values with the variables from url decode.
        form = forms.RatingFilterForm(
            selected_project_hash_id=selected_project_hash_id,
            initial=current_ratings_filter,
        )

    # Handle the filter form
    if request.method == "POST":
        form = forms.RatingFilterForm(
            request.POST, selected_project_hash_id=selected_project_hash_id
        )

        if form.is_valid():
            cleaned_data = {**form.cleaned_data}
            request.session["current_ratings_filter"] = cleaned_data
            current_ratings_filter = cleaned_data

            # Filter the  inputs, see if they are different from the default values.
            url_dictionary = get_new_values_diff(DEFAULT_RATINGS_INPUT, cleaned_data)

            # Make the query string
            query_string = urlencode(url_dictionary)

            print(f"Query url string: {query_string}")

            return redirect(f"{request.path}?{query_string}")

    else:
        form = forms.RatingFilterForm(
            selected_project_hash_id=selected_project_hash_id,
            initial=current_ratings_filter,
        )

    inputs_to_filter = get_new_values_diff(
        DEFAULT_RATINGS_INPUT, current_ratings_filter
    )

    # Filter the ratings
    if "observation" in inputs_to_filter:
        ratings = ratings.filter(candidate__observation=inputs_to_filter["observation"])

    if "tag" in inputs_to_filter:
        ratings = ratings.filter(tag=inputs_to_filter["tag"])

    if "confidence" in inputs_to_filter:
        ratings = ratings.filter(rating=inputs_to_filter["confidence"])

    if "user" in inputs_to_filter:
        ratings = ratings.filter(user__id=inputs_to_filter["user"])

    # Handle CSV download
    if request.method == "GET":
        if request.GET.get("download") == "csv":
            return download_rating_csv_zip(
                ratings, "ratings_summary", DOWNLOAD_CANDIDATE_FIELDS
            )

    # Echarts bar plots #

    # For echarts bar plots of ratings per user and ratings per tag.
    # Convert QuerySet to list of dictionaries for ratings per user
    ratings_per_user = list(
        ratings.values("user__username").annotate(count=Count("hash_id"))
    )

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

    return render(request, "candidate_app/ratings_summary.html", context)


@login_required(login_url="/")
def clear_ratings_filter(request: HttpRequest):
    if (
        "current_ratings_filter" in request.session
        or "clear_filter_data" in request.POST
    ):
        del request.session["current_ratings_filter"]

    return redirect("/ratings_summary/")


@api_view(["POST"])
@transaction.atomic
def upload_observation(request):
    if request.method == "POST":
        token, error_response = get_upload_token(request)
        if error_response:
            return error_response

        print(
            f" --------------- Observation uploaded by user: {token.user} --------------- "
        )
        try:
            # Pull out the project id
            project_id = request.data["proj_id"]

            print(f"++++++++ project_id: {project_id} ++++++++ ")

            # Create the project if it doesn't already exist.
            if not models.Project.objects.filter(id=project_id).exists():
                uploaded_datetime = timezone.now()

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

            obs = serializers.ObservationSerializer(
                data=request.data, context={"user": token.user}
            )
            if models.Observation.objects.filter(
                project=project, id=request.data["id"]
            ).exists():
                return Response(
                    "Observation already created so skipping",
                    status=status.HTTP_201_CREATED,
                )
            if obs.is_valid():
                obs.save()
                print(f"Observation {request.data['id']} saved!")
                return Response(obs.data, status=status.HTTP_201_CREATED)
            logger.debug(request.data)
            return Response(obs.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            print("An exception occurred:", error)
            return Response(
                {"error-message": error}, status=status.HTTP_400_BAD_REQUEST
            )

    return Response(
        {"status": "error", "message": "Not a POST request."},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@transaction.atomic
def upload_beam(request):
    if request.method == "POST":
        token, error_response = get_upload_token(request)
        if error_response:
            return error_response

        print(f" --------------- Beam uploaded by user: {token.user} --------------- ")

        try:
            # Check if beam has already been uploaded before.
            proj = models.Project.objects.get(id=request.data["proj_id"])
            obs = models.Observation.objects.get(
                project=proj, id=request.data["obs_id"]
            )
            if models.Beam.objects.filter(
                project=proj, observation=obs, index=request.data["index"]
            ).exists():
                return Response(
                    f"Beam '{request.data['index']}' for obsservation '{request.data['obs_id']}' already created so skipping",  # noqa: B950
                    status=status.HTTP_200_OK,
                )

            print("before serialiser for beam")
            beam = serializers.BeamSerializer(
                data=request.data, context={"user": token.user}
            )

            if beam.is_valid():
                beam.save()
                print(
                    f"Beam {request.data['index']} saved to {request.data['obs_id']}!"
                )
                return Response(beam.data, status=status.HTTP_201_CREATED)
            logger.debug(request.data)
            return Response(beam.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            print("An exception occurred:", error)
            return Response(
                {"error-message": error}, status=status.HTTP_400_BAD_REQUEST
            )

    return Response(
        {"status": "error", "message": "Not a POST request."},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(["POST"])
@transaction.atomic
def upload_candidate(request):
    if request.method == "POST":
        token, error_response = get_upload_token(request)
        if error_response:
            return error_response

        print(
            f" --------------- Candidate uploaded by user: {token.user} --------------- "
        )

        try:
            proj = models.Project.objects.get(id=request.data["proj_id"])
            obs = models.Observation.objects.get(
                project=proj, id=request.data["obs_id"]
            )
            beam = models.Beam.objects.get(
                project=proj, observation=obs, index=request.data["beam_index"]
            )
            # cand_obj_id = f"{proj.id}_{obs.id}_{beam.index}_{request.data['name']}"
            if models.Candidate.objects.filter(
                project=proj,
                observation=obs,
                beam=beam,
                name=request.data["name"],
            ).exists():
                return Response(
                    f"Candidate {proj.id}_{obs.id}_{beam.index}_{request.data['name']} as already been uploaded/created so skipping",  # noqa: B950
                    status=status.HTTP_200_OK,
                )

            cand = serializers.CandidateSerializer(
                data=request.data, context={"user": token.user}
            )

            if cand.is_valid():
                cand.save()
                print(cand.data)
                return Response(
                    f"Data from - {cand.data}", status=status.HTTP_201_CREATED
                )

            logger.debug(request.data)
            return Response(f"{cand.errors}", status=status.HTTP_400_BAD_REQUEST)

        except Exception as error:
            print("An exception occurred:", error)
            return Response(
                {"status": "error", "message": f"Invalid or expired token - {error}"},
                status=status.HTTP_403_FORBIDDEN,
            )

    return Response(
        {"status": "error", "message": "Not a POST request."},
        status=status.HTTP_400_BAD_REQUEST,
    )


@login_required(login_url="/")
def site_admin(request):
    """Display details of each project, observation,
    and the space used internally to the webapp."""

    selected_project_hash_id = request.session.get("selected_project_hash_id")

    if selected_project_hash_id:
        selected_projects = [
            models.Project.objects.get(hash_id=selected_project_hash_id)
        ]
    else:
        selected_projects = models.Project.objects.all()

    # Get disk space used by projects
    total_disk_space, used_disk_space, free_disk_space = get_disk_space(MEDIA_ROOT)

    annotated_projects = []
    colour_count = 0
    for project in selected_projects:
        project_used_of_total = (
            (project.total_file_size_gb / total_disk_space) * 100
            if used_disk_space
            else 0
        )

        observations = project.obs_proj.annotate(
            candidate_count=Count("cand_obs"),
            rated_candidate_count=Count("cand_obs__rating__candidate", distinct=True),
            ratings_count=Count("cand_obs__rating"),
        )

        annotated_projects.append(
            {
                "project": project,
                "observations": observations,
                "project_used_of_total": project_used_of_total,
                "project_colour": PROJECT_COLOURS[
                    (colour_count + 1) % len(PROJECT_COLOURS)
                ],
            }
        )

        colour_count += 1

    context = {
        "annotated_projects": annotated_projects,
        "free_disk_space": free_disk_space,
        "used_disk_space": used_disk_space,
        "total_disk_space": total_disk_space,
    }

    return render(request, "candidate_app/site_admin.html", context)


@login_required(login_url="/")
def delete(request: HttpRequest):
    """Using a authorised POST request, delete records from the DB."""

    if request.user.is_staff and "recordType" in request.POST:
        record_type = request.POST.get("recordType")
        to_delete = request.POST.get("hashId")
        model_class = DELETABLE_MODELS.get(record_type)
        if model_class:
            try:
                model_class.objects.get(hash_id=to_delete).delete()
                return JsonResponse(
                    {"deleted_recordType": record_type, "deleted_hashId": to_delete},
                    status=201,
                )
            except Exception:
                return JsonResponse(
                    {"deleted_recordType": record_type, "deleted_hashId": to_delete},
                    status=500,
                )

    else:
        return JsonResponse(
            {"message": f"User {request.user} is not authorised to delete records."},
            status=401,
        )


@login_required(login_url="/")
def download_lightcurve_csv(request: HttpRequest, cand_hash_id: str):
    """Download path for the candidate lightcurve csv file."""

    if request.method == "GET":
        candidate = get_object_or_404(models.Candidate, hash_id=cand_hash_id)

        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{candidate.name}_lightcurve.csv"'
        )

        writer = csv.writer(response)

        for row in candidate.lightcurve_data:
            writer.writerow(row)

        return response


# Poor name but has to be different than "ChangePassword" because is used by Django.
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
            for _field, errors in pw_reset_form.errors.as_data().items():
                for error in errors:
                    message = (
                        error.message % error.params if error.params else error.message
                    )
                    messages.error(request, f"{message}")

        return redirect(request.META["HTTP_REFERER"])


class LoginView(TemplateView, View):
    def get(self, request, *args, **kwargs):
        return self.render_to_response({})

    def post(self, request, *args, **kwargs):
        user = authenticate(
            username=request.POST.get("username"), password=request.POST.get("password")
        )
        if user is not None:
            if user.is_active:
                login(request, user)
            else:
                messages.warning(
                    request, "The password is valid, but the account has been disabled!"
                )
        else:
            messages.warning(request, "The username or password were incorrect.")

        return redirect(request.POST.get("next", "/candidates/"))


class LogoutView(View):
    def post(self, request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("/")
        logout(request)
        messages.success(request, "You are now logged out!")
        return redirect("/")
