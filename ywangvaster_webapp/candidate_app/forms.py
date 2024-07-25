from django import forms
from django.core.exceptions import ValidationError
from . import models

ORDER_BY_CHOICES = (
    ("id", "ID"),
    ("avg_rating", "Rating"),
    # ("num_ratings", "Count"),
    # ("notes", "Notes"),
    # ("transient_count", "N Tranisent"),
    # ("airplane_count", "N Airplane"),
    # ("rfi_count", "N RFI"),
    # ("sidelobe_count", "N Sidelobe"),
    # ("alias_count", "N Alias"),
    # ("chgcentre_count", "N CHG Center"),
    # ("scintillation_count", "N Scintillation"),
    # ("pulsar_count", "N Pulsar"),
    # ("other_count", "N Other"),
    ("ra_hms", "RA"),
    ("dec_dms", "Dec"),
    ("obs_id", "Obs ID"),
)

ASC_DEC_CHOICES = (("", "Ascending"), ("-", "Decending"))


class CandidateFilterForm(forms.Form):

    rated = forms.BooleanField(required=False)
    tags = forms.ModelChoiceField(
        models.Classification.objects.all(),
        empty_label="All classification tags",
        required=False,
    )
    project_id = forms.ChoiceField(required=False)
    observation_id = forms.ModelChoiceField(
        models.Observation.objects.all(),
        empty_label="All observations",
        required=False,
    )

    # Candidate details
    cand_ra_str = forms.CharField(required=False, max_length=64)
    cand_dec_str = forms.CharField(required=False, max_length=64)
    cand_arcmin_search_radius = forms.FloatField(required=False, initial=2)

    # Beam details
    beam_index = forms.IntegerField(required=False)
    beam_ra_str = forms.CharField(required=False)
    beam_dec_str = forms.CharField(required=False)
    beam_arcmin_search_radius = forms.FloatField(required=False, initial=2)

    # Deep details
    deep_num = forms.IntegerField(required=False)
    deep_ra_str = forms.CharField(required=False)
    deep_dec_str = forms.CharField(required=False)
    deep_arcmin_search_radius = forms.FloatField(required=False, initial=2)

    # Statistics - floats that are done by min-max sliders min = gte, max = lte
    chi_square__gte = forms.FloatField(required=False)
    chi_square__lte = forms.FloatField(required=False)

    chi_square_sigma__gte = forms.FloatField(required=False)
    chi_square_sigma__lte = forms.FloatField(required=False)

    chi_square_log_sigma__gte = forms.FloatField(required=False)
    chi_square_log_sigma__lte = forms.FloatField(required=False)

    peak_map__gte = forms.FloatField(required=False)
    peak_map__lte = forms.FloatField(required=False)

    peak_map_sigma__gte = forms.FloatField(required=False)
    peak_map_sigma__lte = forms.FloatField(required=False)

    peak_map_log_sigma__gte = forms.FloatField(required=False)
    peak_map_log_sigma__lte = forms.FloatField(required=False)

    # Gaussians are usually NaNs.
    gaussian_map__gte = forms.FloatField(required=False)
    gaussian_map__lte = forms.FloatField(required=False)

    gaussian_map_sigma__gte = forms.FloatField(required=False)
    gaussian_map_sigma__lte = forms.FloatField(required=False)

    std_map__gte = forms.FloatField(required=False)
    std_map__lte = forms.FloatField(required=False)

    bright_sep_arcmin__gte = forms.FloatField(required=False)
    bright_sep_arcmin__lte = forms.FloatField(required=False)

    beam_sep_deg__gte = forms.FloatField(required=False)
    beam_sep_deg__lte = forms.FloatField(required=False)

    deep_int_flux__gte = forms.FloatField(required=False)
    deep_int_flux__lte = forms.FloatField(required=False)

    deep_peak_flux__gte = forms.FloatField(required=False)
    deep_peak_flux__lte = forms.FloatField(required=False)

    deep_sep_arcsec__gte = forms.FloatField(required=False)
    deep_sep_arcsec__lte = forms.FloatField(required=False)

    md_deep__gte = forms.FloatField(required=False)
    md_deep__lte = forms.FloatField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        # if cleaned_data["column_display"]:
        #     cleaned_data["column_display"] = cleaned_data["column_display"].name
        return cleaned_data

    # rating_cutoff = forms.FloatField(required=False)
    # observation_id = forms.ModelChoiceField(
    #     models.Observation.objects.all(), empty_label="All observations", required=False
    # )
    # column_display = forms.ModelChoiceField(
    #     queryset=models.Classification.objects.all(),
    #     to_field_name="name",
    #     empty_label="All columns",
    #     required=False,
    # )
    # order_by = forms.ChoiceField(choices=ORDER_BY_CHOICES, required=False, initial="avg_rating")
    # asc_dec = forms.ChoiceField(choices=ASC_DEC_CHOICES, required=False, initial="-")
    # ra_hms = forms.CharField(required=False, max_length=64)
    # dec_dms = forms.CharField(required=False, max_length=64)
    # search_radius_arcmin = forms.FloatField(required=False, initial=2)


SESSION_ORDER_CHOICES = (
    ("rand", "Random"),
    ("new", "Newest"),
    ("old", "Oldest"),
    ("brig", "Brightest"),
    ("faint", "Faintest"),
)
SESSION_FILTER_CHOICES = (
    ("unrank", "Unranked Candidates"),
    ("old", "Candidates Not Ranked Recently"),
    ("all", "All Candidates"),
)


class SessionSettingsForm(forms.Form):
    ordering = forms.ChoiceField(choices=SESSION_ORDER_CHOICES, required=False, initial="rand")
    filtering = forms.ChoiceField(choices=SESSION_FILTER_CHOICES, required=False, initial="unrank")
    exclude_87 = forms.BooleanField(required=False)
    exclude_118 = forms.BooleanField(required=False)
    exclude_154 = forms.BooleanField(required=False)
    exclude_184 = forms.BooleanField(required=False)
    exclude_200 = forms.BooleanField(required=False)
    exclude_215 = forms.BooleanField(required=False)

    project = forms.ModelChoiceField(queryset=models.Project.objects.all(), to_field_name="name", empty_label=None)

    def clean(self):
        cleaned_data = super().clean()
        # replace the project object with it's name
        # since the project object will cause a "Not JSon serializable" error
        cleaned_data["project"] = cleaned_data["project"].name
        if cleaned_data.get("filtering") == "all" and cleaned_data.get("ordering") != "rand":
            raise ValidationError(
                "ERROR: You can not order all candidates by anything other than"
                "random as it will always give you the same candidate. "
                "Please either order randomly or filter by candidates not "
                "ranked recently."
            )


confidence_choices = (
    ("T", "True"),
    ("F", "False"),
    ("U", "Unsure"),
)


class RateCandidateForm(forms.Form):
    """To create a rating record for a candidate."""

    condifence = forms.ChoiceField(choices=confidence_choices)
    classification = forms.ModelChoiceField(
        queryset=models.Classification.objects.all(),
        to_field_name="name",
        label="Tags",
    )
    notes = forms.CharField(required=False, label="Notes")


class ClassificationForm(forms.Form):
    """Form to add a new classification to the DB"""

    name = forms.CharField(required=True)
    description = forms.CharField(required=True)
