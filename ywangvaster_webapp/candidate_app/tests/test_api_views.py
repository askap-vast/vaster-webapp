"""Tests for candidate_app API views (upload endpoints, get_token, delete)."""

import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from candidate_app.models import Beam, Candidate, Observation
from candidate_app.tests.factories import (
    make_beam,
    make_candidate,
    make_observation,
    make_project,
    make_user,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Minimal valid PNG header — satisfies the content_type + extension checks.
_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def _png_file(name="test.png"):
    return SimpleUploadedFile(name, _PNG_BYTES, content_type="image/png")


def _txt_file(name="test.txt"):
    return SimpleUploadedFile(name, b"not a png", content_type="text/plain")


def _candidate_payload(project, obs, beam, name="VAST_J000001+00"):
    """Minimal POST data for upload_candidate — mirrors the factory defaults."""
    return {
        "proj_id": project.id,
        "obs_id": obs.id,
        "beam_index": beam.index,
        "name": name,
        "ra_str": "00:40:00.0",
        "dec_str": "+00:00:00",
        "ra": 10.0,
        "dec": 20.0,
        "chi_square": 1.0,
        "chi_square_log_sigma": 1.0,
        "chi_square_sigma": 1.0,
        "peak_map": 1.0,
        "peak_map_log_sigma": 1.0,
        "peak_map_sigma": 1.0,
        "std_map": 1.0,
        "bright_sep_arcmin": 10.0,
        "beam_ra": 10.0,
        "beam_dec": 20.0,
        "beam_sep_deg": 0.1,
        "deep_ra_deg": 10.0,
        "deep_dec_deg": 20.0,
        "deep_sep_arcsec": 1.0,
        "deep_name": "deep_src_1",
        "deep_num": 1,
        "deep_peak_flux": 0.001,
        "deep_int_flux": 0.001,
        "md_deep": 0.5,
        "is_best_beam": False,
    }


# ---------------------------------------------------------------------------
# get_token
# ---------------------------------------------------------------------------


class TestGetToken(TestCase):
    def setUp(self):
        self.user = make_user()
        self.url = reverse("get_token")

    def test_logged_in_user_gets_token(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"create": "false"})
        self.assertEqual(response.status_code, 201)
        self.assertIn("token", response.json())

    def test_unauthenticated_redirects(self):
        response = Client().post(self.url, {"create": "false"})
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# upload_observation
# ---------------------------------------------------------------------------


class TestUploadObservation(TestCase):
    def setUp(self):
        from rest_framework.authtoken.models import Token

        self.user = make_user()
        self.token = Token.objects.get(user=self.user)
        self.url = reverse("upload_observation")

    def _post(self, data, token_key=None):
        headers = {"HTTP_AUTHORIZATION": token_key or self.token.key}
        return self.client.post(self.url, data, **headers)

    def test_valid_request_creates_observation(self):
        response = self._post({"proj_id": "OBS-PROJ", "id": "SB00001"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Observation.objects.filter(id="SB00001").exists())

    def test_missing_auth_header_returns_400(self):
        response = self.client.post(self.url, {"proj_id": "OBS-PROJ", "id": "SB00001"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_token_returns_403(self):
        response = self._post(
            {"proj_id": "OBS-PROJ", "id": "SB00001"}, token_key="badtoken"
        )
        self.assertEqual(response.status_code, 403)

    def test_duplicate_observation_not_created(self):
        data = {"proj_id": "OBS-PROJ", "id": "SB00001"}
        self._post(data)
        self._post(data)
        self.assertEqual(Observation.objects.filter(id="SB00001").count(), 1)


# ---------------------------------------------------------------------------
# upload_beam
# ---------------------------------------------------------------------------


class TestUploadBeam(TestCase):
    def setUp(self):
        from rest_framework.authtoken.models import Token

        self.user = make_user()
        self.token = Token.objects.get(user=self.user)
        self.url = reverse("upload_beam")
        self.project = make_project(self.user, id="BEAM-PROJ")
        self.obs = make_observation(self.project, obs_id="SB00002")

    def _post(self, data):
        return self.client.post(self.url, data, HTTP_AUTHORIZATION=self.token.key)

    def test_valid_request_creates_beam(self):
        response = self._post(
            {"proj_id": self.project.id, "obs_id": self.obs.id, "index": 0}
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Beam.objects.filter(observation=self.obs, index=0).exists())

    def test_duplicate_beam_not_created(self):
        data = {"proj_id": self.project.id, "obs_id": self.obs.id, "index": 0}
        self._post(data)
        self._post(data)
        self.assertEqual(Beam.objects.filter(observation=self.obs, index=0).count(), 1)


# ---------------------------------------------------------------------------
# upload_candidate
# ---------------------------------------------------------------------------


class TestUploadCandidate(TestCase):
    def setUp(self):
        from rest_framework.authtoken.models import Token

        self.user = make_user()
        self.token = Token.objects.get(user=self.user)
        self.url = reverse("upload_candidate")
        self.project = make_project(self.user, id="CAND-PROJ")
        self.obs = make_observation(self.project, obs_id="SB00003")
        self.beam = make_beam(self.obs, index=0)

    def _post(self, data):
        return self.client.post(self.url, data, HTTP_AUTHORIZATION=self.token.key)

    def test_valid_request_creates_candidate(self):
        data = _candidate_payload(self.project, self.obs, self.beam)
        response = self._post(data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Candidate.objects.filter(name=data["name"]).exists())

    def test_new_candidate_is_ranked_as_best_beam(self):
        data = _candidate_payload(self.project, self.obs, self.beam)
        self._post(data)
        cand = Candidate.objects.get(name=data["name"])
        self.assertTrue(cand.is_best_beam)

    def test_duplicate_candidate_not_created(self):
        data = _candidate_payload(self.project, self.obs, self.beam)
        self._post(data)
        self._post(data)
        self.assertEqual(Candidate.objects.filter(name=data["name"]).count(), 1)


# ---------------------------------------------------------------------------
# upload_dynamic_spectra
# ---------------------------------------------------------------------------


class TestUploadDynamicSpectra(TestCase):
    def setUp(self):
        from rest_framework.authtoken.models import Token

        self.user = make_user()
        self.token = Token.objects.get(user=self.user)
        self.url = reverse("upload_dynamic_spectra")
        project = make_project(self.user)
        obs = make_observation(project)
        beam = make_beam(obs)
        self.candidate = make_candidate(beam)

    def _post(self, data):
        return self.client.post(self.url, data, HTTP_AUTHORIZATION=self.token.key)

    def test_valid_png_by_hash_returns_200(self):
        response = self._post(
            {"hash": str(self.candidate.hash_id), "dynamic_spectra_png": _png_file()}
        )
        self.assertEqual(response.status_code, 200)

    def test_valid_png_by_name_returns_200(self):
        response = self._post(
            {"name": self.candidate.name, "dynamic_spectra_png": _png_file()}
        )
        self.assertEqual(response.status_code, 200)

    def test_non_png_file_returns_400(self):
        response = self._post(
            {"hash": str(self.candidate.hash_id), "dynamic_spectra_png": _txt_file()}
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_hash_returns_404(self):
        response = self._post(
            {"hash": str(uuid.uuid4()), "dynamic_spectra_png": _png_file()}
        )
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete(TestCase):
    def setUp(self):
        self.staff = make_user(staff=True)
        self.regular = make_user()
        self.url = reverse("delete")
        project = make_project(self.staff)
        obs = make_observation(project)
        beam = make_beam(obs)
        self.candidate = make_candidate(beam)

    def test_staff_can_delete_record(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            self.url,
            {"recordType": "candidate", "hashId": str(self.candidate.hash_id)},
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(
            Candidate.objects.filter(hash_id=self.candidate.hash_id).exists()
        )

    def test_non_staff_cannot_delete(self):
        self.client.force_login(self.regular)
        response = self.client.post(
            self.url,
            {"recordType": "candidate", "hashId": str(self.candidate.hash_id)},
        )
        self.assertEqual(response.status_code, 401)
        self.assertTrue(
            Candidate.objects.filter(hash_id=self.candidate.hash_id).exists()
        )

    def test_unknown_hash_returns_500(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            self.url,
            {"recordType": "candidate", "hashId": str(uuid.uuid4())},
        )
        self.assertEqual(response.status_code, 500)
