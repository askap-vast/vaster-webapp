from django.contrib import admin

from . import models


class CandidateAdmin(admin.ModelAdmin):
    search_fields = ["obs_id", "hash_id", "name"]
    list_display = ("name", "hash_id")
    model = models.Candidate


admin.site.register(models.Tag)
admin.site.register(models.Project)
admin.site.register(models.Observation)
admin.site.register(models.Beam)
admin.site.register(models.Candidate, CandidateAdmin)
admin.site.register(models.Rating)
