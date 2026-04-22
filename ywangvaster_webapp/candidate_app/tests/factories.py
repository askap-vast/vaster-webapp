"""
Test data factories.

Each helper creates a fully-linked DB object with sensible defaults so that
individual test cases only have to supply the values they actually care about.
"""

import itertools

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from candidate_app import models

User = get_user_model()

# Module-level counter so every call within a test run gets a unique integer,
# regardless of which TestCase class it comes from.
_counter = itertools.count(1)


def _seq() -> int:
    return next(_counter)


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def make_user(username: str = None, staff: bool = False):
    """Create a User and a DRF Token for that user."""
    uid = _seq()
    username = username or f"user{uid}"
    user = User.objects.create_user(
        username=username,
        password="testpass123",
        is_staff=staff,
    )
    Token.objects.get_or_create(user=user)
    return user


def make_upload(user):
    """Create an Upload record owned by *user*."""
    return models.Upload.objects.create(user=user)


def make_project(user, id: str = None):
    """Create a Project (and its required Upload)."""
    uid = _seq()
    project_id = id or f"TEST-PROJ-{uid}"
    upload = make_upload(user)
    return models.Project.objects.create(
        id=project_id,
        name=f"Test Project {uid}",
        upload=upload,
    )


def make_observation(project, obs_id: str = None):
    """Create an Observation linked to *project*."""
    uid = _seq()
    obs_id = obs_id or f"SB{uid:05d}"  # noqa: E231
    upload = make_upload(project.upload.user)
    return models.Observation.objects.create(
        proj_id=project.id,
        id=obs_id,
        project=project,
        upload=upload,
    )


def make_beam(observation, index: int = 0):
    """Create a Beam linked to *observation* with zero file totals."""
    upload = make_upload(observation.upload.user)
    return models.Beam.objects.create(
        obs_id=observation.id,
        proj_id=observation.proj_id,
        index=index,
        observation=observation,
        project=observation.project,
        upload=upload,
        total_file_count=0,
        total_file_size_bytes=0,
    )


def make_candidate(beam, ra: float = 10.0, dec: float = 20.0, **kwargs):
    """Create a Candidate with all required fields populated.

    Pass keyword arguments to override any default value, e.g.::

        make_candidate(beam, ra=15.0, chi_square=5.0, is_best_beam=True)
    """
    uid = _seq()
    observation = beam.observation
    project = beam.project
    upload = make_upload(beam.upload.user)

    defaults = dict(
        proj_id=project.id,
        obs_id=observation.id,
        beam_index=beam.index,
        upload=upload,
        beam=beam,
        observation=observation,
        project=project,
        name=f"VAST_J{uid:06d}+00",  # noqa: E231
        ra_str="00:40:00.0",
        dec_str="+00:00:00",
        ra=ra,
        dec=dec,
        # Candidate model statistics
        chi_square=1.0,
        chi_square_log_sigma=1.0,
        chi_square_sigma=1.0,
        peak_map=1.0,
        peak_map_log_sigma=1.0,
        peak_map_sigma=1.0,
        std_map=1.0,
        bright_sep_arcmin=10.0,
        # Beam position
        beam_ra=ra,
        beam_dec=dec,
        beam_sep_deg=0.1,
        # Deep source match
        deep_ra_deg=ra,
        deep_dec_deg=dec,
        deep_sep_arcsec=1.0,
        deep_name="deep_src_1",
        deep_num=1,
        deep_peak_flux=0.001,
        deep_int_flux=0.001,
        md_deep=0.5,
        # File totals
        total_file_count=0,
        total_file_size_bytes=0,
        is_best_beam=False,
    )
    defaults.update(kwargs)
    return models.Candidate.objects.create(**defaults)


def make_tag(name: str = "real"):
    """Get-or-create a Tag by name."""
    tag, _ = models.Tag.objects.get_or_create(name=name, defaults={"description": ""})
    return tag


def make_rating(candidate, user, confidence: str = "T", tag=None, notes: str = ""):
    """Create a Rating for *candidate* by *user*."""
    return models.Rating.objects.create(
        candidate=candidate,
        user=user,
        rating=confidence,
        tag=tag,
        notes=notes,
    )


def make_atnf_pulsar(ra: float = 10.0, dec: float = 20.0, name: str = None):
    """Create an ATNFPulsar row."""
    uid = _seq()
    name = name or f"J{uid:04d}+00"  # noqa: E231
    return models.ATNFPulsar.objects.create(
        name=name,
        ra_str="00:40:00",
        dec_str="+20:00:00",
        raj=ra,
        decj=dec,
    )
