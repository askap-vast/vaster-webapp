from django.contrib import admin

from . import models


class CandidateAdmin(admin.ModelAdmin):
    search_help_text = "Filter by observation ID"
    search_fields = ["obs_id__observation_id"]
    list_display = ("name", "beam")
    model = models.Candidate


admin.site.register(models.Project)
admin.site.register(models.Observation)
admin.site.register(models.Beam)
admin.site.register(models.Candidate, CandidateAdmin)
admin.site.register(models.CandidateMinMaxStats)
admin.site.register(models.Tag)
admin.site.register(models.Rating)
admin.site.register(models.Upload)
