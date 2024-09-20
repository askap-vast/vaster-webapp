import os
import uuid
from django.utils import timezone

from django.db import models
from django.conf import settings
from django.utils.functional import cached_property


POSSIBLE_RATINGS = (
    ("T", "true"),
    ("F", "false"),
    ("U", "unsure"),
)


# Funtion for defining paths to filse.
def beam_upload_path(instance, filename):
    """Define a file path for beam files project_id/obs_id/beam_id/filename."""

    return os.path.join(f"{instance.project.id}", f"{instance.observation.id}", f"{instance.index}", filename)


def cand_upload_path(instance, filename):
    """Define a file path for candidate project_id/obs_id/beam_id/filename."""

    return os.path.join(f"{instance.project.id}", f"{instance.obs_id}", f"{instance.beam.index}", filename)


class Upload(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name="upload",
        default=None,
    )
    date = models.DateTimeField(default=timezone.now, blank=True)


class Project(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    id = models.CharField(verbose_name="id", max_length=64, blank=True, null=True, unique=True)
    name = models.CharField(verbose_name="Project name", max_length=64, blank=True, null=True)
    description = models.CharField(verbose_name="Description", max_length=256, blank=True, null=True)

    # Meta data for when the object was uploaded / created
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="proj_upload", default=None)

    def __str__(self):
        return f"{self.id}"

    @cached_property
    def total_file_size_gb(self):
        """Return the total size of all the files in gigabytes associated this record."""
        total_size = 0
        beams = Beam.objects.filter(project=self)
        candidates = Candidate.objects.filter(project=self)

        for beam in beams:
            total_size += beam.total_file_size_bytes

        for candidate in candidates:
            total_size += candidate.total_file_size_bytes

        return total_size / (1024.0**3)

    @cached_property
    def total_file_count(self):
        """Return the total number of files that are for this record."""
        total_file_count = 0
        beams = Beam.objects.filter(observation=self)
        candidates = Candidate.objects.filter(observation=self)

        for beam in beams:
            total_file_count += beam.total_file_count

        for candidate in candidates:
            total_file_count += candidate.total_file_count

        return total_file_count


class Observation(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # From upload
    proj_id = models.CharField(max_length=64)
    id = models.CharField()  # THis is the ID of the observation, eg. SB50230
    obs_start = models.DateTimeField(blank=True, null=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="obs_proj", default=None)

    # Meta data for when the object was uploaded
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="obs_upload", default=None)

    @cached_property
    def total_file_size_gb(self):
        """Return the total size of all the files in gigabytes associated with this record."""
        total_size = 0
        beams = Beam.objects.filter(observation=self)
        candidates = Candidate.objects.filter(observation=self)

        for beam in beams:
            total_size += beam.total_file_size_bytes

        for candidate in candidates:
            total_size += candidate.total_file_size_bytes

        return total_size / (1024.0**3)

    @cached_property
    def total_file_count(self):
        """Return the total number of files that are for this record."""
        total_file_count = 0
        beams = Beam.objects.filter(observation=self)
        candidates = Candidate.objects.filter(observation=self)

        for beam in beams:
            total_file_count += beam.total_file_count

        for candidate in candidates:
            total_file_count += candidate.total_file_count

        return total_file_count

    def __str__(self):
        return f"{self.id} ({self.project.id})"


class Beam(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Uploaded info
    obs_id = models.CharField()
    proj_id = models.CharField(max_length=64)
    index = models.IntegerField()  # This is for 00, 01, 02, 03 - for an observation or survey

    # Meta data for when the object was uploaded
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="beam_upload", default=None)

    # Linking back to the observation object.
    observation = models.ForeignKey(Observation, on_delete=models.CASCADE, related_name="beam_obs", default=None)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="beam_proj", default=None)

    # Only if the user wants to add information to the beam.
    description = models.CharField(verbose_name="Description", max_length=1024, blank=True, null=True)

    # Totals for files attached to the object
    total_file_count = models.IntegerField(blank=True, null=True)
    total_file_size_bytes = models.BigIntegerField(blank=True, null=True)

    # Save the files for each beam.
    final_cand_csv = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)

    std_fits = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)

    chisquare_map1_png = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)
    chisquare_map2_png = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)
    chisquare_fits = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)

    peak_map1_png = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)
    peak_map2_png = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)
    peak_fits = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)

    FILE_FIELDS = [
        "final_cand_csv",
        "std_fits",
        "chisquare_map1_png",
        "chisquare_map2_png",
        "chisquare_fits",
        "peak_map1_png",
        "peak_map2_png",
        "peak_fits",
    ]

    def delete(self, *args, **kwargs):
        # Delete associated files
        for field in self.FILE_FIELDS:
            file_field = getattr(self, field)
            if file_field:
                storage, path = file_field.storage, file_field.path
                storage.delete(path)

        # Call superclass delete method
        super(Beam, self).delete(*args, **kwargs)

    def __str__(self):
        return f"{self.index}"


class Candidate(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    proj_id = models.CharField(max_length=64)
    obs_id = models.CharField()
    beam_index = models.IntegerField()

    # Used a human unique identifier -  <project_id>_<obs_id>_beam<beam_index>_<cand_id>
    # cand_obj_id = models.CharField(null=True, blank=True)

    # Meta data for when the object was uploaded
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="cand_upload", default=None)

    # Linking back to the observation and beam objects.
    beam = models.ForeignKey(Beam, on_delete=models.CASCADE, related_name="cand_beams", default=None)
    observation = models.ForeignKey(Observation, on_delete=models.CASCADE, related_name="cand_obs", default=None)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="cand_proj", default=None)

    # Totals for files attached to the object
    total_file_count = models.IntegerField(blank=True, null=True)
    total_file_size_bytes = models.BigIntegerField(blank=True, null=True)

    # Lightcurve
    lightcurve_data = models.JSONField(null=True, blank=True)
    lightcurve_png = models.FileField(upload_to=cand_upload_path, null=True, blank=True)

    # Slices files
    slices_gif = models.FileField(upload_to=cand_upload_path, null=True, blank=True)
    slices_fits = models.FileField(upload_to=cand_upload_path, null=True, blank=True)

    # Deepcutout files
    deepcutout_png = models.FileField(upload_to=cand_upload_path, null=True, blank=True)
    deepcutout_fits = models.FileField(upload_to=cand_upload_path, null=True, blank=True)

    # Comes from the candidadate file data uploaded
    # source_id = models.IntegerField() # not needed in this web app.
    name = models.CharField(max_length=100)
    ra_str = models.CharField(max_length=100)
    dec_str = models.CharField(max_length=100)
    ra = models.FloatField()
    dec = models.FloatField()

    # Candidate model stats
    chi_square = models.FloatField()
    chi_square_log_sigma = models.FloatField()
    chi_square_sigma = models.FloatField()
    peak_map = models.FloatField()
    peak_map_log_sigma = models.FloatField()
    peak_map_sigma = models.FloatField()
    gaussian_map = models.FloatField(null=True, blank=True)
    gaussian_map_sigma = models.FloatField(null=True, blank=True)
    std_map = models.FloatField()

    # Bright separation
    bright_sep_arcmin = models.FloatField()

    # Beam coords and separation
    beam_ra = models.FloatField()
    beam_dec = models.FloatField()
    beam_sep_deg = models.FloatField()

    # Deep coords and separation
    deep_ra_deg = models.FloatField()
    deep_dec_deg = models.FloatField()
    deep_sep_arcsec = models.FloatField()

    # Deep statistics
    deep_name = models.CharField(max_length=100)
    deep_num = models.IntegerField()
    deep_peak_flux = models.FloatField()
    deep_int_flux = models.FloatField()
    md_deep = models.FloatField()

    FILE_FIELDS = [
        "lightcurve_png",
        "slices_gif",
        "slices_fits",
        "deepcutout_png",
        "deepcutout_fits",
    ]

    def delete(self, *args, **kwargs):
        # Delete associated files
        for field in self.FILE_FIELDS:
            file_field = getattr(self, field)
            if file_field:
                storage, path = file_field.storage, file_field.path
                storage.delete(path)

        # Call superclass delete method
        super(Candidate, self).delete(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"


class Tag(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(verbose_name="Classification tag", max_length=256, blank=True, null=True, unique=True)
    description = models.CharField(verbose_name="Description", max_length=1024, blank=True, null=True)

    # Attach classifcations to a project or just them global?
    # project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="project")

    def __str__(self):
        return f"{self.name} - {self.description}"


class Rating(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="rating", default=None)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="rating",
        on_delete=models.DO_NOTHING,
        default=None,
    )
    rating = models.CharField(max_length=1, choices=POSSIBLE_RATINGS, default=None)
    tag = models.ForeignKey(Tag, on_delete=models.DO_NOTHING, related_name="rating", default=None)
    date = models.DateTimeField(default=timezone.now, blank=True)
    notes = models.CharField(max_length=1024)

    # TO-DO
    # Link to other resource?

    def __str__(self):
        return f"{self.rating}"


class ATNFPulsar(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(verbose_name="Pulsar Name", max_length=32, blank=False, unique=True)
    ra_str = models.CharField(max_length=32)
    dec_str = models.CharField(max_length=32)
    decj = models.FloatField(verbose_name="Declination epoch (J2000, deg)")
    raj = models.FloatField(verbose_name="Right Ascension epoch (J2000, deg)")
    DM = models.FloatField(verbose_name="Dispersion Measure (cm^-3 pc)", blank=True, null=True)
    p0 = models.FloatField(verbose_name="Barycentric period of the pulsar (s)", blank=True, null=True)
    s400 = models.FloatField(verbose_name="Mean flux density at 400 MHz (mJy)", blank=True, null=True)

    def __str__(self):
        return f"{self.name}"


### For displaying the mins and maxs for the filtering the candidate table page ###
class CandidateMinMaxStats(models.Model):
    """This is updated on a trigger for each insert update or delete for the candidate table."""

    # Statistics - floats that are done by min-max sliders
    min_chi_square = models.FloatField(null=True, blank=True)
    max_chi_square = models.FloatField(null=True, blank=True)

    min_chi_square_sigma = models.FloatField(null=True, blank=True)
    max_chi_square_sigma = models.FloatField(null=True, blank=True)

    min_chi_square_log_sigma = models.FloatField(null=True, blank=True)
    max_chi_square_log_sigma = models.FloatField(null=True, blank=True)

    min_peak_map = models.FloatField(null=True, blank=True)
    max_peak_map = models.FloatField(null=True, blank=True)

    min_peak_map_sigma = models.FloatField(null=True, blank=True)
    max_peak_map_sigma = models.FloatField(null=True, blank=True)

    min_peak_map_log_sigma = models.FloatField(null=True, blank=True)
    max_peak_map_log_sigma = models.FloatField(null=True, blank=True)

    # Gaussians are usually NaNs.
    min_gaussian_map = models.FloatField(null=True, blank=True)
    max_gaussian_map = models.FloatField(null=True, blank=True)

    min_gaussian_map_sigma = models.FloatField(null=True, blank=True)
    max_gaussian_map_sigma = models.FloatField(null=True, blank=True)

    min_std_map = models.FloatField(null=True, blank=True)
    max_std_map = models.FloatField(null=True, blank=True)

    min_bright_sep_arcmin = models.FloatField(null=True, blank=True)
    max_bright_sep_arcmin = models.FloatField(null=True, blank=True)

    min_beam_sep_deg = models.FloatField(null=True, blank=True)
    max_beam_sep_deg = models.FloatField(null=True, blank=True)

    min_deep_int_flux = models.FloatField(null=True, blank=True)
    max_deep_int_flux = models.FloatField(null=True, blank=True)

    min_deep_peak_flux = models.FloatField(null=True, blank=True)
    max_deep_peak_flux = models.FloatField(null=True, blank=True)

    min_deep_sep_arcsec = models.FloatField(null=True, blank=True)
    max_deep_sep_arcsec = models.FloatField(null=True, blank=True)

    min_md_deep = models.FloatField(null=True, blank=True)
    max_md_deep = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False  # No migrations will be created for this model
        db_table = "candidate_min_max_stats"
