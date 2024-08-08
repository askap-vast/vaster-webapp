"""This is loaded into the context for every page and needs to be added to settings.py for each addition to the page context dictionary."""

from . import models, forms


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

    return {
        "project_form": project_form,
        "selected_project_id": selected_project_id,
        "selected_projects": selected_projects,
    }
