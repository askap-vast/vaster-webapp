from django.contrib import admin
from .models import Project, Observation, Candidate, Rating, Classification, Filter


class CandidateAdmin(admin.ModelAdmin):
    search_help_text = "Filter by observation ID"
    search_fields = ["obs_id__observation_id"]
    list_display = ("name", "beam", "notes")
    model = Candidate


admin.site.register(Observation)
admin.site.register(Candidate, CandidateAdmin)
admin.site.register(Rating)
admin.site.register(Project)
admin.site.register(Classification)
