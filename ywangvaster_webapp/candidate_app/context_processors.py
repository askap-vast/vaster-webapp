"""This is loaded into the context for every page and needs to be added to settings.py for each addition to the page context dictionary."""

from . import models, forms

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect


def project_form(request):

    project_form = forms.ProjectSelectForm()

    # Get current selected project and put it on the header of each rendered page.
    selected_project_hash_id = request.session.get("selected_project_hash_id")

    if selected_project_hash_id is None or selected_project_hash_id == "":
        selected_project_id = "All projects"
        selected_projects = models.Project.objects.all()
    else:
        selected_projects = [models.Project.objects.get(hash_id=selected_project_hash_id)]
        selected_project_id = selected_projects[0].id

    # Empty pw reset form for header
    pw_reset_form = PasswordChangeForm(request.user)

    return {
        "project_form": project_form,
        "selected_project_id": selected_project_id,
        "selected_projects": selected_projects,
        "pw_reset_form": pw_reset_form,
    }
