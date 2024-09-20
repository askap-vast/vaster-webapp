from django import forms
from django.contrib.auth import get_user_model

from . import models

DjangoUserModel = get_user_model()

confidence_choices = (
    (None, "----"),
    ("T", "True"),
    ("F", "False"),
    ("U", "Unsure"),
)


class CandidateFilterForm(forms.Form):

    def __init__(self, *args, **kwargs):
        # Extract the selected project from the kwargs
        selected_project_hash_id = kwargs.pop("selected_project_hash_id", None)
        super().__init__(*args, **kwargs)

        # Update the choices for observation_id based on the selected project
        if selected_project_hash_id:
            self.fields["observation"].queryset = models.Observation.objects.filter(project=selected_project_hash_id)
        else:
            self.fields["observation"].queryset = models.Observation.objects.all()

    def _post_clean(self):
        """Additional cleaning step after the form's clean method.

        Used to get the hash_id's out of the model choice fields for serialisation in later steps of the candidate_table page.
        """
        super()._post_clean()

        tag = self.cleaned_data.get("tag")
        if tag:
            self.cleaned_data["tag"] = str(tag.hash_id)

        observation = self.cleaned_data.get("observation")
        if observation:
            self.cleaned_data["observation"] = str(observation.hash_id)

    rated = forms.BooleanField(required=False)

    ratings_count = forms.IntegerField(required=False)

    tag = forms.ModelChoiceField(
        models.Tag.objects.all(),
        empty_label="All classification tags",
        required=False,
    )

    confidence = forms.ChoiceField(choices=confidence_choices, required=False, label="Confidence")

    observation = forms.ModelChoiceField(
        models.Observation.objects.none(),
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
        return cleaned_data


class RateCandidateForm(forms.Form):
    """To create a rating record for a candidate."""

    confidence = forms.ChoiceField(
        choices=confidence_choices,
        label="Confidence",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    tag = forms.ModelChoiceField(
        queryset=models.Tag.objects.all(),
        to_field_name="name",
        label="Tag",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    notes = forms.CharField(
        required=False,
        label="Notes",
    )


class CreateTagForm(forms.ModelForm):
    """Form to add a new classification tag to the DB.

    This can be done on the rate candidate page or in the Django admin page."""

    class Meta:
        model = models.Tag
        fields = "__all__"


class ProjectSelectForm(forms.Form):

    selected_project_hash_id = forms.ModelChoiceField(
        queryset=models.Project.objects.all(),
        to_field_name="hash_id",
        empty_label="All projects",
        label="Project",
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class RatingFilterForm(forms.Form):

    def __init__(self, *args, **kwargs):
        # Extract the selected project from the kwargs
        selected_project_hash_id = kwargs.pop("selected_project_hash_id", None)
        super().__init__(*args, **kwargs)

        # Update the choices for observation_id based on the selected project
        if selected_project_hash_id:
            self.fields["observation"].queryset = models.Observation.objects.filter(project=selected_project_hash_id)
        else:
            self.fields["observation"].queryset = models.Observation.objects.all()

    def _post_clean(self):
        """Additional cleaning step after the form's clean method.

        Used to get the hash_id's out of the model choice fields for serialisation in later steps of the candidate_table page.
        """
        super()._post_clean()

        tag = self.cleaned_data.get("tag")
        if tag:
            self.cleaned_data["tag"] = str(tag.hash_id)

        observation = self.cleaned_data.get("observation")
        if observation:
            self.cleaned_data["observation"] = str(observation.hash_id)

        user = self.cleaned_data.get("user")
        if user:
            self.cleaned_data["user"] = str(user.id)

    observation = forms.ModelChoiceField(
        models.Observation.objects.none(),
        empty_label="All observations",
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    tag = forms.ModelChoiceField(
        queryset=models.Tag.objects.all(),
        required=False,
        label="Tag",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    confidence = forms.ChoiceField(
        choices=confidence_choices,
        required=False,
        label="Confidence",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    user = forms.ModelChoiceField(
        queryset=DjangoUserModel.objects.all(),
        required=False,
        label="User",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
