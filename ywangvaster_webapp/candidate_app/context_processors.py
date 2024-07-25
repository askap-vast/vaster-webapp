from . import models


def get_projects(request):
    return {"projects": models.Project.objects.all()}
