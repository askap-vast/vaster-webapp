"""End-to-end view tests for candidate_app using Django's test client.

Each TestCase class focuses on one user-facing flow. The candidate_table and
ratings_summary views call get_candidate_form_defaults(), which reads from the
CandidateMinMaxStats materialised view. That view is automatically refreshed by
a trigger whenever candidates are inserted, so tests that create candidates via
setUpTestData can rely on it being populated. Tests that don't create candidates
patch the function to return safe defaults.
"""

import json
import uuid
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from candidate_app.models import Rating
from candidate_app.tests.factories import (
    make_beam,
    make_candidate,
    make_observation,
    make_project,
    make_rating,
    make_tag,
    make_user,
)

# Minimal mock for get_candidate_form_defaults — avoids reading the
# CandidateMinMaxStats view in tests that do not create candidates.
_MOCK_DEFAULTS = (
    {
        "is_best_beam": "true",
        "rated": "",
        "ratings_count": None,
        "tag": None,
        "confidence": "",
        "observation": None,
        "cand_ra_str": "",
        "cand_dec_str": "",
        "cand_arcmin_search_radius": 2.0,
        "beam_index": None,
        "beam_ra_str": "",
        "beam_dec_str": "",
        "beam_arcmin_search_radius": 2.0,
        "deep_num": None,
        "deep_ra_str": "",
        "deep_dec_str": "",
        "deep_arcmin_search_radius": 2.0,
        "sort_by": None,
        "sort_dir": "asc",
    },
    {},
)

_patch_defaults = patch(
    "candidate_app.views_utils.get_candidate_form_defaults",
    return_value=_MOCK_DEFAULTS,
)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestAuthentication(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_login_with_valid_credentials_redirects(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "testpass123"},
        )
        self.assertEqual(response.status_code, 302)

    def test_login_with_invalid_credentials_still_redirects(self):
        # LoginView always redirects; invalid credentials add a warning message
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "wrong"},
        )
        self.assertEqual(response.status_code, 302)

    def test_logout_redirects_to_home(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_unauthenticated_candidate_table_redirects(self):
        response = self.client.get(reverse("candidates"))
        # @login_required(login_url="/") redirects to "/?next=/candidates/"
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/"))

    def test_unauthenticated_ratings_summary_redirects(self):
        response = self.client.get(reverse("ratings_summary"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/"))


# ---------------------------------------------------------------------------
# Candidate table
# ---------------------------------------------------------------------------


class TestCandidateTable(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        project = make_project(cls.user)
        obs = make_observation(project)
        beam = make_beam(obs)
        # is_best_beam=True so the default filter (is_best_beam="true") finds it
        cls.cand = make_candidate(beam, ra=10.0, dec=20.0, is_best_beam=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_returns_200(self):
        response = self.client.get(reverse("candidates"))
        self.assertEqual(response.status_code, 200)

    def test_get_renders_candidate_table_template(self):
        response = self.client.get(reverse("candidates"))
        self.assertTemplateUsed(response, "candidate_app/candidate_table.html")

    def test_post_filter_redirects_with_query_string(self):
        response = self.client.post(
            reverse("candidates"),
            {"is_best_beam": "true", "rated": "", "confidence": ""},
        )
        # POST stores filter in session then redirects to GET with query params
        self.assertEqual(response.status_code, 302)
        self.assertIn("/candidates/", response["Location"])

    def test_filter_stored_in_session_after_post(self):
        self.client.post(
            reverse("candidates"),
            {"is_best_beam": "false", "rated": "", "confidence": ""},
        )
        self.assertIn("current_filter_data", self.client.session)

    def test_clear_filter_removes_session_data(self):
        self.client.post(
            reverse("candidates"),
            {"is_best_beam": "false", "rated": ""},
        )
        self.client.get(reverse("clear_candidates_filter"))
        self.assertNotIn("current_filter_data", self.client.session)


# ---------------------------------------------------------------------------
# Candidate rating
# ---------------------------------------------------------------------------


class TestCandidateRating(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        project = make_project(cls.user)
        obs = make_observation(project)
        beam = make_beam(obs)
        cls.cand = make_candidate(beam, is_best_beam=True)
        cls.tag = make_tag("real")

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("candidate_rating", args=[str(self.cand.hash_id)])

    def test_get_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_renders_rating_template(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "candidate_app/candidate_rating.html")

    def test_get_unknown_candidate_returns_404(self):
        url = reverse("candidate_rating", args=[str(uuid.uuid4())])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_post_creates_rating(self):
        self.client.post(
            self.url,
            {"confidence": "T", "tag": self.tag.name, "notes": ""},
        )
        self.assertTrue(
            Rating.objects.filter(candidate=self.cand, user=self.user).exists()
        )

    def test_post_valid_rating_redirects(self):
        response = self.client.post(
            self.url,
            {"confidence": "F", "tag": self.tag.name, "notes": ""},
        )
        self.assertEqual(response.status_code, 302)

    def test_second_rating_by_same_user_adds_new_record(self):
        # First rating: no prev_rating → redirects to next_candidate
        self.client.post(
            self.url, {"confidence": "T", "tag": self.tag.name, "notes": ""}
        )
        # Second rating: prev_rating exists → redirects to HTTP_REFERER
        self.client.post(
            self.url,
            {"confidence": "F", "tag": self.tag.name, "notes": ""},
            HTTP_REFERER=self.url,
        )
        self.assertEqual(
            Rating.objects.filter(candidate=self.cand, user=self.user).count(), 2
        )


# ---------------------------------------------------------------------------
# next_candidate
# ---------------------------------------------------------------------------


class TestNextCandidate(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        project = make_project(cls.user)
        obs = make_observation(project)
        beam = make_beam(obs)
        # is_best_beam=True so the default session filter (is_best_beam="true") finds it
        cls.cand = make_candidate(beam, is_best_beam=True)
        cls.tag = make_tag("rfi")

    def setUp(self):
        self.client.force_login(self.user)

    def test_redirects_to_unrated_candidate(self):
        response = self.client.get(reverse("next_candidate"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.cand.hash_id), response["Location"])

    def test_no_unrated_candidates_redirects_to_home(self):
        make_rating(self.cand, self.user, tag=self.tag)
        response = self.client.get(reverse("next_candidate"))
        self.assertRedirects(response, "/", fetch_redirect_response=False)


# ---------------------------------------------------------------------------
# Ratings summary
# ---------------------------------------------------------------------------


class TestRatingsSummary(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        project = make_project(cls.user)
        obs = make_observation(project)
        beam = make_beam(obs)
        cand = make_candidate(beam)
        tag = make_tag("real")
        make_rating(cand, cls.user, tag=tag)

    def setUp(self):
        self.client.force_login(self.user)

    def test_get_returns_200(self):
        response = self.client.get(reverse("ratings_summary"))
        self.assertEqual(response.status_code, 200)

    def test_get_renders_ratings_template(self):
        response = self.client.get(reverse("ratings_summary"))
        self.assertTemplateUsed(response, "candidate_app/ratings_summary.html")

    def test_post_filter_redirects(self):
        response = self.client.post(reverse("ratings_summary"), {"confidence": "T"})
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# Project select
# ---------------------------------------------------------------------------


class TestProjectSelect(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()
        cls.project = make_project(cls.user)

    def setUp(self):
        self.client.force_login(self.user)

    def test_post_stores_project_in_session(self):
        self.client.post(
            reverse("project_select"),
            {"selected_project_hash_id": str(self.project.hash_id)},
            HTTP_REFERER="/candidates/",
        )
        self.assertEqual(
            self.client.session.get("selected_project_hash_id"),
            str(self.project.hash_id),
        )


# ---------------------------------------------------------------------------
# Site admin
# ---------------------------------------------------------------------------


class TestSiteAdmin(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user()

    def setUp(self):
        self.client.force_login(self.user)

    @patch("candidate_app.views.get_disk_space", return_value=(100.0, 60.0, 40.0))
    def test_get_returns_200(self, _mock):
        response = self.client.get(reverse("site_admin"))
        self.assertEqual(response.status_code, 200)

    @patch("candidate_app.views.get_disk_space", return_value=(100.0, 60.0, 40.0))
    def test_renders_site_admin_template(self, _mock):
        response = self.client.get(reverse("site_admin"))
        self.assertTemplateUsed(response, "candidate_app/site_admin.html")

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(reverse("site_admin"))
        # @login_required(login_url="/") redirects to "/?next=/site_admin/"
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/"))


# ---------------------------------------------------------------------------
# Lightcurve CSV download
# ---------------------------------------------------------------------------


class TestDownloadLightcurveCSV(TestCase):
    @classmethod
    def setUpTestData(cls):
        from candidate_app.models import Candidate

        cls.user = make_user()
        project = make_project(cls.user)
        obs = make_observation(project)
        beam = make_beam(obs)
        cls.cand = make_candidate(beam)
        Candidate.objects.filter(hash_id=cls.cand.hash_id).update(
            lightcurve_data=[
                ["time", "flux", "err"],
                ["2023-01-01T00:00:00", "0.001", "0.0001"],
            ]
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_returns_csv_content_type(self):
        url = reverse("download_lightcurve_csv", args=[str(self.cand.hash_id)])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")

    def test_content_disposition_includes_candidate_name(self):
        url = reverse("download_lightcurve_csv", args=[str(self.cand.hash_id)])
        response = self.client.get(url)
        self.assertIn(self.cand.name, response["Content-Disposition"])

    def test_unknown_candidate_returns_404(self):
        url = reverse("download_lightcurve_csv", args=[str(uuid.uuid4())])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Nearby objects (POST only, external calls mocked)
# ---------------------------------------------------------------------------


class TestNearbyObjectsTable(TestCase):
    def _post(self, ra_str="10.0", dec_str="20.0", dist=2.0):
        return self.client.post(
            reverse("get_nearby_objects"),
            data=json.dumps(
                {"ra_str": ra_str, "dec_str": dec_str, "dist_arcmin": dist}
            ),
            content_type="application/json",
        )

    @patch("candidate_app.views_utils.get_simbad", return_value=[])
    @patch("candidate_app.views_utils.get_das", return_value=[])
    def test_post_returns_200(self, _das, _simbad):
        response = self._post()
        self.assertEqual(response.status_code, 200)

    def test_get_returns_400(self):
        response = self.client.get(reverse("get_nearby_objects"))
        self.assertEqual(response.status_code, 400)
