"""Tests for candidate_app.utils (FITSTableType, download_fits, get_disk_space)."""

from io import BytesIO
from unittest.mock import patch

from astropy.io import fits
from django.test import RequestFactory, TestCase

from candidate_app.models import Candidate
from candidate_app.tests.factories import (
    make_beam,
    make_candidate,
    make_observation,
    make_project,
    make_user,
)
from candidate_app.utils import FITSTableType, download_fits, get_disk_space

# ---------------------------------------------------------------------------
# FITSTableType
# ---------------------------------------------------------------------------


class TestFITSTableType(TestCase):
    def test_bool_returns_L(self):
        self.assertEqual(FITSTableType(True), "L")
        self.assertEqual(FITSTableType(False), "L")

    def test_int_returns_J(self):
        self.assertEqual(FITSTableType(0), "J")
        self.assertEqual(FITSTableType(42), "J")

    def test_float_returns_E(self):
        self.assertEqual(FITSTableType(1.0), "E")
        self.assertEqual(FITSTableType(-3.14), "E")

    def test_str_returns_length_prefixed_A(self):
        self.assertEqual(FITSTableType("hello"), "5A")
        self.assertEqual(FITSTableType("ab"), "2A")

    def test_other_type_returns_5A(self):
        self.assertEqual(FITSTableType(None), "5A")
        self.assertEqual(FITSTableType([1, 2]), "5A")


# ---------------------------------------------------------------------------
# download_fits
# ---------------------------------------------------------------------------


class TestDownloadFits(TestCase):
    def setUp(self):
        user = make_user()
        project = make_project(user)
        obs = make_observation(project)
        beam = make_beam(obs)
        self.cand1 = make_candidate(beam, ra=10.0, dec=20.0)
        self.cand2 = make_candidate(beam, ra=11.0, dec=21.0)
        self.factory = RequestFactory()

    def _get_response(self, queryset):
        request = self.factory.get("/")
        return download_fits(request, queryset, "test_table")

    def test_response_content_type_is_octet_stream(self):
        qs = Candidate.objects.filter(
            hash_id__in=[self.cand1.hash_id, self.cand2.hash_id]
        )
        response = self._get_response(qs)
        self.assertEqual(response["Content-Type"], "application/octet-stream")

    def test_response_content_disposition_contains_filename(self):
        qs = Candidate.objects.filter(
            hash_id__in=[self.cand1.hash_id, self.cand2.hash_id]
        )
        response = self._get_response(qs)
        self.assertIn("test_table.fits", response["Content-Disposition"])

    def test_fits_table_has_correct_row_count(self):
        qs = Candidate.objects.filter(
            hash_id__in=[self.cand1.hash_id, self.cand2.hash_id]
        )
        response = self._get_response(qs)
        content = (
            b"".join(response.streaming_content)
            if hasattr(response, "streaming_content")
            else response.content
        )
        with fits.open(BytesIO(content)) as hdul:
            table = hdul[1]
            self.assertEqual(len(table.data), 2)

    def test_fits_content_starts_with_simple_keyword(self):
        qs = Candidate.objects.filter(hash_id=self.cand1.hash_id)
        response = self._get_response(qs)
        content = response.content
        # FITS files start with "SIMPLE  =" in the first 80-byte block
        self.assertTrue(content[:6] == b"SIMPLE")


# ---------------------------------------------------------------------------
# get_disk_space
# ---------------------------------------------------------------------------


class TestGetDiskSpace(TestCase):
    def test_returns_gb_values(self):
        gib = 1024**3
        mock_usage = (100 * gib, 60 * gib, 40 * gib)
        with patch("candidate_app.utils.shutil.disk_usage", return_value=mock_usage):
            total, used, free = get_disk_space("/some/path")
        self.assertAlmostEqual(total, 100.0)
        self.assertAlmostEqual(used, 60.0)
        self.assertAlmostEqual(free, 40.0)

    def test_passes_path_to_disk_usage(self):
        gib = 1024**3
        mock_usage = (10 * gib, 5 * gib, 5 * gib)
        with patch(
            "candidate_app.utils.shutil.disk_usage", return_value=mock_usage
        ) as mock_du:
            get_disk_space("/media/data")
        mock_du.assert_called_once_with("/media/data")
