import os
import uuid
from datetime import datetime

from django.db import models
from django.conf import settings


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


class Project(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    id = models.CharField(verbose_name="id", max_length=64, blank=True, null=True)
    name = models.CharField(verbose_name="Project name", max_length=64, blank=True, null=True, unique=True)
    description = models.CharField(verbose_name="Description", max_length=256, blank=True, null=True)

    def __str__(self):
        return f"{self.name}"


class Filter(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    id = models.CharField(verbose_name="id", max_length=64, blank=True, null=True)
    name = models.CharField(verbose_name="Short Name", max_length=64, blank=True, null=True)
    description = models.CharField(verbose_name="Description", max_length=256, blank=True, null=True)

    def __str__(self):
        return f"{self.name}"


class Upload(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="upload",
        default=None,
    )
    date = models.DateTimeField(default=datetime.now, blank=True)


class Observation(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # From upload
    proj_id = models.CharField(max_length=64)
    id = models.CharField()  # THis is the ID of the observation, eg. SB50230
    obs_start = models.DateTimeField(blank=True, null=True)

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="obs_proj", default=None)

    # Used a human unique identifier - <project_id>_<obs_id>
    obs_obj_id = models.CharField()

    # Meta data for when the object was uploaded
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="obs_upload", default=None)

    # User modified - if required
    obs_name = models.CharField(max_length=128, blank=True, null=True, verbose_name="Observation name")
    obs_description = models.CharField(max_length=1024, blank=True, null=True, verbose_name="Observation description")

    # starttime = models.BigIntegerField(verbose_name="Start Time (GPS sec)")
    # stoptime = models.BigIntegerField(verbose_name="Stop Time (GPS sec)")
    # ra_tile_dec = models.FloatField(blank=True, null=True, verbose_name="RA (deg)")
    # dec_tile_dec = models.FloatField(blank=True, null=True, verbose_name="Dec (deg)")
    # ra_tile_hms = models.CharField(max_length=32, blank=True, null=True, verbose_name="RA (HH:MM:SS)")
    # dec_tile_dms = models.CharField(max_length=32, blank=True, null=True, verbose_name="Dec (DD:MM:SS)")
    # projectid = models.CharField(max_length=16, blank=True, null=True)
    # azimuth = models.FloatField(blank=True, null=True, verbose_name="Azimuth (deg)")
    # elevation = models.FloatField(blank=True, null=True, verbose_name="Elevation (deg)")
    # frequency_channels = models.CharField(
    #     max_length=128,
    #     blank=True,
    #     null=True,
    #     verbose_name="Frequency Channels (x1.28 MHz)",
    # )
    # cent_freq = models.FloatField(blank=True, null=True, verbose_name="Centre Frequency (MHz)")
    # freq_res = models.IntegerField(blank=True, null=True, verbose_name="Frequency Resolution (KHz)")
    # int_time = models.FloatField(blank=True, null=True, verbose_name="Integration Time (s)")

    def __str__(self):
        return f"{self.id}"


class Beam(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Uploaded info
    obs_id = models.CharField()
    proj_id = models.CharField(max_length=64)
    index = models.IntegerField()  # This is for 00, 01, 02, 03 - for an observation or survey

    # Used a human unique identifier - <project_id>_<obs_id>_beam<beam_index>
    beam_obj_id = models.CharField(editable=False)

    # Meta data for when the object was uploaded
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="beam_upload", default=None)

    # Linking back to the observation object.
    observation = models.ForeignKey(Observation, on_delete=models.CASCADE, related_name="beam_obs", default=None)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="beam_proj", default=None)

    # Only if the user wants to add information to the beam.
    description = models.CharField(verbose_name="Description", max_length=1024, blank=True, null=True)

    # Save the files for each beam.
    final_cand_csv = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)

    std_fits = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)

    chisquare_map1_png = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)
    chisquare_map2_png = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)
    chisquare_fits = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)

    peak_map1_png = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)
    peak_map2_png = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)
    peak_fits = models.FileField(upload_to=beam_upload_path, max_length=1024, blank=True, null=True)

    def __str__(self):
        return f"{self.index}"


class Candidate(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    proj_id = models.CharField(max_length=64)
    obs_id = models.CharField()
    beam_index = models.IntegerField()

    # Used a human unique identifier -  <project_id>_<obs_id>_beam<beam_index>_<cand_id>
    cand_obj_id = models.CharField()

    # Meta data for when the object was uploaded
    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="cand_upload", default=None)

    # Linking back to the observation and beam objects.
    beam = models.ForeignKey(Beam, on_delete=models.CASCADE, related_name="cand_beams", default=None)
    observation = models.ForeignKey(Observation, on_delete=models.CASCADE, related_name="cand_obs", default=None)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="cand_proj", default=None)

    # Lightcurve
    lightcurve_data = models.JSONField(null=True, blank=True)
    lightcurve_png = models.FileField(upload_to=cand_upload_path, null=True, blank=True)

    # Slices files
    slices_gif = models.FileField(upload_to=cand_upload_path, null=True, blank=True)
    slices_fits = models.FileField(upload_to=cand_upload_path, null=True, blank=True)

    # Deepcutout files
    deepcutout_png = models.FileField(upload_to=cand_upload_path, null=True, blank=True)
    deepcutout_fits = models.FileField(upload_to=cand_upload_path, null=True, blank=True)

    notes = models.CharField(verbose_name="Notes", max_length=1024, blank=True, null=True)

    # Comes from the candidadate file data uploaded
    # source_id = models.IntegerField() # not needed in this web app.
    name = models.CharField(max_length=100)
    ra_str = models.CharField(max_length=100)
    dec_str = models.CharField(max_length=100)
    ra = models.FloatField()
    dec = models.FloatField()
    chi_square = models.FloatField()
    chi_square_log_sigma = models.FloatField()
    chi_square_sigma = models.FloatField()
    peak_map = models.FloatField()
    peak_map_log_sigma = models.FloatField()
    peak_map_sigma = models.FloatField()
    gaussian_map = models.FloatField(null=True, blank=True)
    gaussian_map_sigma = models.FloatField(null=True, blank=True)
    std_map = models.FloatField()
    md_deep = models.FloatField()
    deep_sep_arcsec = models.FloatField()
    deep_num = models.IntegerField()
    bright_sep_arcmin = models.FloatField()
    beam_sep_deg = models.FloatField()
    beam_ra = models.FloatField()
    beam_dec = models.FloatField()
    deep_name = models.CharField(max_length=100)
    deep_ra_deg = models.FloatField()
    deep_dec_deg = models.FloatField()
    deep_peak_flux = models.FloatField()
    deep_int_flux = models.FloatField()

    # Old data structure from the gleam app.
    #
    # # Data in the fits file
    # x_pix = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Candidate island central x pixel coordinate",
    # )
    # y_pix = models.FloatField(blank=True, null=True, verbose_name="Candidate island central pixel coordinate")
    # ra_deg = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Candidate island central Right Ascension (deg)",
    # )
    # dec_deg = models.FloatField(blank=True, null=True, verbose_name="Candidate island central Declination (deg)")
    # cent_sep_deg = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Candidate separation from observation central pointing (deg)",
    # )
    # rad_pix = models.FloatField(blank=True, null=True, verbose_name="Candidate island radius in pixels")
    # rad_deg = models.FloatField(blank=True, null=True, verbose_name="Candidate island radius in degrees")
    # area_pix = models.FloatField(blank=True, null=True, verbose_name="Candidate island area in pixels^2")
    # can_peak_flux = models.FloatField(blank=True, null=True, verbose_name="Candidate peak flux in Jy")
    # can_fluence = models.FloatField(blank=True, null=True, verbose_name="Candidate fluence in Jy s")
    # can_beam = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Primary beam value at the candidate location",
    # )
    # can_det_stat = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Candidate detection statistic - arbitrary value returned by filter",
    # )
    # can_mod_ind = models.IntegerField(blank=True, null=True, verbose_name="Candidate modulation index")
    # nks_name = models.CharField(max_length=64, blank=True, null=True, verbose_name="Nearest known source name")
    # nks_x_pix = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Nearest known source x pixel coordinate in observation",
    # )
    # nks_y_pix = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Nearest known source y pixel coordinate in observation",
    # )
    # nks_ra_deg = models.FloatField(blank=True, null=True, verbose_name="Nearest known source Right Ascension (deg)")
    # nks_dec_deg = models.FloatField(blank=True, null=True, verbose_name="Nearest known source Declination (deg)")
    # nks_flux = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Nearest known source integrated flux density in Jy",
    # )
    # nks_res = models.FloatField(blank=True, null=True, verbose_name="")
    # nks_res_dif = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Nearest known source number of std above mean residual",
    # )
    # nks_det_stat = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Nearest known source detection statistic " "- arbitrary value returned by filter",
    # )
    # nks_sep_pix = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Separation between candidate and known in pixels",
    # )
    # nks_sep_deg = models.FloatField(
    #     blank=True,
    #     null=True,
    #     verbose_name="Separation between candidate and known in degrees",
    # )
    # can_nks_flux_rat = models.FloatField(blank=True, null=True, verbose_name="Ratio of candidate and known flux")
    # can_nks_is_close = models.BooleanField(null=True, verbose_name="")

    # # Coordinates converted to hms/dms
    # ra_hms = models.CharField(
    #     max_length=32,
    #     blank=True,
    #     null=True,
    #     verbose_name="Candidate Right Ascension (HH:MM:SS)",
    # )
    # dec_dms = models.CharField(
    #     max_length=32,
    #     blank=True,
    #     null=True,
    #     verbose_name="Candidate Declination (DD:MM:SS)",
    # )
    # nks_ra_hms = models.CharField(
    #     max_length=32,
    #     blank=True,
    #     null=True,
    #     verbose_name="Nearest known source Right Ascension (HH:MM:SS)",
    # )
    # nks_dec_dms = models.CharField(
    #     max_length=32,
    #     blank=True,
    #     null=True,
    #     verbose_name="Nearest known source Declination (DD:MM:SS)",
    # )

    # def __str__(self):
    #     return f"{self.id}_obs{self.obs_id.observation_id}_{self.filter.name}"


class Classification(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(verbose_name="Classification", max_length=64, blank=True, null=True, unique=True)
    description = models.CharField(verbose_name="Description", max_length=256, blank=True, null=True)

    def __str__(self):
        return f"{self.name}"


class Rating(models.Model):

    hash_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="rating", default=None)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rating",
        default=None,
    )

    rating = models.CharField(max_length=1, choices=POSSIBLE_RATINGS, default=None)

    tags = models.ManyToManyField(Classification, related_name="ratings", default=None)

    date = models.DateTimeField(default=datetime.now, blank=True)


class xml_ivorns(models.Model):
    id = models.AutoField(primary_key=True)
    ivorn = models.CharField(max_length=128, unique=True)


class ATNFPulsar(models.Model):

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(verbose_name="Pulsar Name", max_length=32, blank=False, unique=True)
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
