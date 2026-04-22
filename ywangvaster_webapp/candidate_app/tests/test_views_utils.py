"""Tests for candidate_app.views_utils."""

import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import requests as requests_lib
from django.test import RequestFactory, SimpleTestCase, TestCase

from candidate_app.models import Candidate, Rating
from candidate_app.tests.factories import (
    make_atnf_pulsar,
    make_beam,
    make_candidate,
    make_observation,
    make_project,
    make_rating,
    make_tag,
    make_user,
)
from candidate_app.views_utils import (
    build_candidate_queryset,
    download_rating_csv_zip,
    filter_candidates_by_coords,
    get_atnf,
    get_das,
    get_new_values_diff,
    get_session_filter_data,
    get_simbad,
    get_upload_token,
)

# ---------------------------------------------------------------------------
# Shared mock defaults
#
# Mirrors the real default_inputs from get_candidate_form_defaults() but uses
# an empty float dict so no float range filters are applied unless a test
# explicitly overrides the patch. This avoids a dependency on the
# CandidateMinMaxStats materialised view, which is not managed by Django
# migrations and is not populated in the test database.
# ---------------------------------------------------------------------------
_MOCK_DEFAULT_INPUTS = {
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
}

_patch_defaults = patch(
    "candidate_app.views_utils.get_candidate_form_defaults",
    return_value=(_MOCK_DEFAULT_INPUTS, {}),
)


# ---------------------------------------------------------------------------
# get_new_values_diff
# ---------------------------------------------------------------------------


class TestGetNewValuesDiff(SimpleTestCase):
    def test_identical_dicts_returns_empty(self):
        original = {"a": 1, "b": "x"}
        self.assertEqual(get_new_values_diff(original, original.copy()), {})

    def test_one_changed_key(self):
        original = {"a": 1, "b": 2}
        new = {"a": 1, "b": 99}
        self.assertEqual(get_new_values_diff(original, new), {"b": 99})

    def test_multiple_changed_keys(self):
        original = {"a": 1, "b": 2, "c": 3}
        new = {"a": 10, "b": 20, "c": 3}
        self.assertEqual(get_new_values_diff(original, new), {"a": 10, "b": 20})

    def test_none_value_in_new_is_skipped(self):
        original = {"a": 1}
        new = {"a": None}
        self.assertEqual(get_new_values_diff(original, new), {})

    def test_key_missing_from_new_uses_original_value(self):
        original = {"a": 1, "b": 2}
        new = {"a": 10}
        # "a" changed → 10; "b" not in new → original value 2
        self.assertEqual(get_new_values_diff(original, new), {"a": 10, "b": 2})


# ---------------------------------------------------------------------------
# build_candidate_queryset
# ---------------------------------------------------------------------------


class TestBuildCandidateQueryset(TestCase):
    def setUp(self):
        user = make_user()
        project = make_project(user)
        self.obs = make_observation(project)
        self.beam = make_beam(self.obs)

    # --- is_best_beam ---
    #
    # Both candidates are within 5 arcsec (~0.34 arcsec apart) so they share a
    # rerank group. c_best wins (lower beam_sep_deg) and is set to True; c_other
    # is set to False. Explicit reranking + refresh_from_db ensures the DB state
    # is correct regardless of any side effects from create().

    @_patch_defaults
    def test_is_best_beam_true_filters_to_best_only(self, _mock):
        c_best = make_candidate(self.beam, ra=10.0, dec=20.0, beam_sep_deg=0.1)
        c_other = make_candidate(self.beam, ra=10.0001, dec=20.0, beam_sep_deg=0.5)
        c_best.rerank_best_beam_group()
        c_best.refresh_from_db()
        c_other.refresh_from_db()
        session = {**_MOCK_DEFAULT_INPUTS, "is_best_beam": "true"}
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertIn(c_best.pk, pks)
        self.assertNotIn(c_other.pk, pks)

    @_patch_defaults
    def test_is_best_beam_false_filters_to_non_best_only(self, _mock):
        c_best = make_candidate(self.beam, ra=10.0, dec=20.0, beam_sep_deg=0.1)
        c_other = make_candidate(self.beam, ra=10.0001, dec=20.0, beam_sep_deg=0.5)
        c_best.rerank_best_beam_group()
        c_best.refresh_from_db()
        c_other.refresh_from_db()
        session = {**_MOCK_DEFAULT_INPUTS, "is_best_beam": "false"}
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertNotIn(c_best.pk, pks)
        self.assertIn(c_other.pk, pks)

    @_patch_defaults
    def test_is_best_beam_empty_string_no_filter(self, _mock):
        c_best = make_candidate(self.beam, ra=10.0, dec=20.0, beam_sep_deg=0.1)
        c_other = make_candidate(self.beam, ra=10.0001, dec=20.0, beam_sep_deg=0.5)
        c_best.rerank_best_beam_group()
        c_best.refresh_from_db()
        c_other.refresh_from_db()
        session = {**_MOCK_DEFAULT_INPUTS, "is_best_beam": ""}
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertIn(c_best.pk, pks)
        self.assertIn(c_other.pk, pks)

    # --- rated ---

    @_patch_defaults
    def test_rated_true_returns_only_rated_candidates(self, _mock):
        user = make_user()
        c_rated = make_candidate(self.beam, ra=10.0, dec=20.0, is_best_beam=True)
        c_unrated = make_candidate(self.beam, ra=11.0, dec=20.0, is_best_beam=True)
        make_rating(c_rated, user)
        session = {**_MOCK_DEFAULT_INPUTS, "rated": "true"}
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertIn(c_rated.pk, pks)
        self.assertNotIn(c_unrated.pk, pks)

    @_patch_defaults
    def test_rated_false_returns_only_unrated_candidates(self, _mock):
        user = make_user()
        c_rated = make_candidate(self.beam, ra=10.0, dec=20.0, is_best_beam=True)
        c_unrated = make_candidate(self.beam, ra=11.0, dec=20.0, is_best_beam=True)
        make_rating(c_rated, user)
        session = {**_MOCK_DEFAULT_INPUTS, "rated": "false"}
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertNotIn(c_rated.pk, pks)
        self.assertIn(c_unrated.pk, pks)

    # --- observation ---

    @_patch_defaults
    def test_observation_filter(self, _mock):
        user = make_user()
        obs2 = make_observation(make_project(user))
        beam2 = make_beam(obs2)
        c1 = make_candidate(self.beam, ra=10.0, dec=20.0, is_best_beam=True)
        c2 = make_candidate(beam2, ra=11.0, dec=20.0, is_best_beam=True)
        session = {**_MOCK_DEFAULT_INPUTS, "observation": str(self.obs.pk)}
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertIn(c1.pk, pks)
        self.assertNotIn(c2.pk, pks)

    # --- beam_index ---

    @_patch_defaults
    def test_beam_index_filter(self, _mock):
        beam2 = make_beam(self.obs, index=1)
        c1 = make_candidate(self.beam, ra=10.0, dec=20.0, is_best_beam=True)
        c2 = make_candidate(beam2, ra=11.0, dec=20.0, is_best_beam=True)
        session = {**_MOCK_DEFAULT_INPUTS, "beam_index": 0}
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertIn(c1.pk, pks)
        self.assertNotIn(c2.pk, pks)

    # --- tag ---

    @_patch_defaults
    def test_tag_filter(self, _mock):
        user = make_user()
        tag1 = make_tag("real")
        tag2 = make_tag("rfi")
        c1 = make_candidate(self.beam, ra=10.0, dec=20.0, is_best_beam=True)
        c2 = make_candidate(self.beam, ra=11.0, dec=20.0, is_best_beam=True)
        make_rating(c1, user, tag=tag1)
        make_rating(c2, user, tag=tag2)
        session = {**_MOCK_DEFAULT_INPUTS, "tag": str(tag1.hash_id)}
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertIn(c1.pk, pks)
        self.assertNotIn(c2.pk, pks)

    # --- confidence ---

    @_patch_defaults
    def test_confidence_filter(self, _mock):
        user = make_user()
        c_true = make_candidate(self.beam, ra=10.0, dec=20.0, is_best_beam=True)
        c_false = make_candidate(self.beam, ra=11.0, dec=20.0, is_best_beam=True)
        make_rating(c_true, user, confidence="T")
        make_rating(c_false, user, confidence="F")
        session = {**_MOCK_DEFAULT_INPUTS, "confidence": "T"}
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertIn(c_true.pk, pks)
        self.assertNotIn(c_false.pk, pks)

    # --- float range ---

    def test_chi_square_gte_filter(self):
        float_defaults = {"chi_square__gte": 0.0, "chi_square__lte": 100.0}
        with patch(
            "candidate_app.views_utils.get_candidate_form_defaults",
            return_value=(_MOCK_DEFAULT_INPUTS, float_defaults),
        ):
            c_in = make_candidate(
                self.beam, ra=10.0, dec=20.0, chi_square=10.0, is_best_beam=True
            )
            c_out = make_candidate(
                self.beam, ra=11.0, dec=20.0, chi_square=2.0, is_best_beam=True
            )
            session = {**_MOCK_DEFAULT_INPUTS, "chi_square__gte": 5.0}
            pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
            self.assertIn(c_in.pk, pks)
            self.assertNotIn(c_out.pk, pks)

    # --- mJy → Jy conversion ---

    def test_deep_peak_flux_filter_converts_mjy_to_jy(self):
        # deep_peak_flux is stored in Jy; the filter session value is in mJy.
        # 5 mJy threshold → 0.005 Jy. Candidate at 0.01 Jy (10 mJy) passes;
        # candidate at 0.001 Jy (1 mJy) does not.
        float_defaults = {"deep_peak_flux__gte": 0.0, "deep_peak_flux__lte": 1000.0}
        with patch(
            "candidate_app.views_utils.get_candidate_form_defaults",
            return_value=(_MOCK_DEFAULT_INPUTS, float_defaults),
        ):
            c_in = make_candidate(
                self.beam, ra=10.0, dec=20.0, deep_peak_flux=0.01, is_best_beam=True
            )
            c_out = make_candidate(
                self.beam, ra=11.0, dec=20.0, deep_peak_flux=0.001, is_best_beam=True
            )
            session = {**_MOCK_DEFAULT_INPUTS, "deep_peak_flux__gte": 5.0}
            pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
            self.assertIn(c_in.pk, pks)
            self.assertNotIn(c_out.pk, pks)

    # --- cone search ---

    @_patch_defaults
    def test_cand_cone_search(self, _mock):
        # ra=10.0 deg = 00:40:00 — inside a 5 arcmin radius centred there.
        # ra=15.0 deg is 5 degrees away — well outside.
        c_in = make_candidate(self.beam, ra=10.0, dec=20.0, is_best_beam=True)
        c_out = make_candidate(self.beam, ra=15.0, dec=20.0, is_best_beam=True)
        session = {
            **_MOCK_DEFAULT_INPUTS,
            "cand_ra_str": "00:40:00.0",
            "cand_dec_str": "+20:00:00",
            "cand_arcmin_search_radius": 5.0,
        }
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertIn(c_in.pk, pks)
        self.assertNotIn(c_out.pk, pks)

    @_patch_defaults
    def test_deep_cone_search(self, _mock):
        c_in = make_candidate(
            self.beam,
            ra=10.0,
            dec=20.0,
            deep_ra_deg=10.0,
            deep_dec_deg=20.0,
            is_best_beam=True,
        )
        c_out = make_candidate(
            self.beam,
            ra=15.0,
            dec=20.0,
            deep_ra_deg=15.0,
            deep_dec_deg=20.0,
            is_best_beam=True,
        )
        session = {
            **_MOCK_DEFAULT_INPUTS,
            "deep_ra_str": "00:40:00.0",
            "deep_dec_str": "+20:00:00",
            "deep_arcmin_search_radius": 5.0,
        }
        pks = list(build_candidate_queryset(session).values_list("pk", flat=True))
        self.assertIn(c_in.pk, pks)
        self.assertNotIn(c_out.pk, pks)

    # --- sorting ---

    @_patch_defaults
    def test_sort_by_chi_square_asc(self, _mock):
        make_candidate(self.beam, ra=10.0, dec=20.0, chi_square=5.0, is_best_beam=True)
        make_candidate(self.beam, ra=11.0, dec=20.0, chi_square=1.0, is_best_beam=True)
        make_candidate(self.beam, ra=12.0, dec=20.0, chi_square=3.0, is_best_beam=True)
        session = {**_MOCK_DEFAULT_INPUTS, "sort_by": "chi_square", "sort_dir": "asc"}
        values = list(
            build_candidate_queryset(session).values_list("chi_square", flat=True)
        )
        self.assertEqual(values, sorted(values))

    @_patch_defaults
    def test_sort_by_chi_square_desc(self, _mock):
        make_candidate(self.beam, ra=10.0, dec=20.0, chi_square=5.0, is_best_beam=True)
        make_candidate(self.beam, ra=11.0, dec=20.0, chi_square=1.0, is_best_beam=True)
        session = {**_MOCK_DEFAULT_INPUTS, "sort_by": "chi_square", "sort_dir": "desc"}
        values = list(
            build_candidate_queryset(session).values_list("chi_square", flat=True)
        )
        self.assertEqual(values, sorted(values, reverse=True))

    @_patch_defaults
    def test_sort_by_name_asc(self, _mock):
        make_candidate(self.beam, ra=10.0, dec=20.0, is_best_beam=True)
        make_candidate(self.beam, ra=11.0, dec=20.0, is_best_beam=True)
        session = {**_MOCK_DEFAULT_INPUTS, "sort_by": "name", "sort_dir": "asc"}
        values = list(build_candidate_queryset(session).values_list("name", flat=True))
        self.assertEqual(values, sorted(values))


# ---------------------------------------------------------------------------
# filter_candidates_by_coords
# ---------------------------------------------------------------------------


class TestFilterCandidatesByCoords(TestCase):
    def setUp(self):
        user = make_user()
        project = make_project(user)
        obs = make_observation(project)
        beam = make_beam(obs)
        self.c_in = make_candidate(beam, ra=10.0, dec=20.0)
        self.c_out = make_candidate(beam, ra=15.0, dec=20.0)
        self.qs = Candidate.objects.all()

    def test_empty_ra_returns_unfiltered(self):
        result = filter_candidates_by_coords(self.qs, "", "+20:00:00", "ra", "dec", 5.0)
        self.assertEqual(result.count(), self.qs.count())

    def test_empty_dec_returns_unfiltered(self):
        result = filter_candidates_by_coords(
            self.qs, "00:40:00.0", "", "ra", "dec", 5.0
        )
        self.assertEqual(result.count(), self.qs.count())

    def test_valid_coords_filters_by_radius(self):
        result = filter_candidates_by_coords(
            self.qs, "00:40:00.0", "+20:00:00", "ra", "dec", 5.0
        )
        pks = list(result.values_list("pk", flat=True))
        self.assertIn(self.c_in.pk, pks)
        self.assertNotIn(self.c_out.pk, pks)

    def test_annotate_true_with_sep_name(self):
        result = filter_candidates_by_coords(
            self.qs,
            "00:40:00.0",
            "+20:00:00",
            "ra",
            "dec",
            5.0,
            annotate=True,
            sep_name="my_sep",
        )
        self.assertIn("my_sep", result.query.annotations)

    def test_for_rating_table_annotates_from_db_local(self):
        result = filter_candidates_by_coords(
            self.qs,
            "00:40:00.0",
            "+20:00:00",
            "ra",
            "dec",
            5.0,
            for_rating_table=True,
        )
        rows = list(result)
        self.assertTrue(len(rows) > 0)
        self.assertTrue(all(row["from_db"] == "Local" for row in rows))


# ---------------------------------------------------------------------------
# get_atnf
# ---------------------------------------------------------------------------


class TestGetAtnf(TestCase):
    def test_returns_only_near_pulsar(self):
        near = make_atnf_pulsar(ra=10.0, dec=20.0)
        make_atnf_pulsar(ra=15.0, dec=20.0)  # ~5 degrees away — outside 5 arcmin
        result = get_atnf("00:40:00.0", "+20:00:00", dist_arcmin=5.0)
        names = [r["name"] for r in result]
        self.assertIn(near.name, names)
        self.assertEqual(len(result), 1)

    def test_result_contains_sep_field(self):
        make_atnf_pulsar(ra=10.0, dec=20.0)
        result = get_atnf("00:40:00.0", "+20:00:00", dist_arcmin=5.0)
        self.assertIn("sep", result[0])


# ---------------------------------------------------------------------------
# get_simbad
# ---------------------------------------------------------------------------


class TestGetSimbad(TestCase):
    @patch("candidate_app.views_utils.Simbad.query_region")
    def test_valid_result_is_parsed(self, mock_query):
        mock_query.return_value = [{"main_id": "Crab", "ra": 83.8221, "dec": 22.0145}]
        result = get_simbad("05:34:32.0", "+22:00:52", dist_arcmin=5.0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Crab")
        self.assertIn("ra_str", result[0])
        self.assertIn("dec_str", result[0])
        self.assertIn("sep", result[0])

    @patch("candidate_app.views_utils.Simbad.query_region", return_value=None)
    def test_none_result_returns_empty_list(self, _mock):
        result = get_simbad("05:34:32.0", "+22:00:52", dist_arcmin=5.0)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# get_das
# ---------------------------------------------------------------------------


class TestGetDas(TestCase):
    @patch("candidate_app.views_utils.requests.post")
    def test_valid_response_is_parsed(self, mock_post):
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {
            "status": "ok",
            "results": {
                "VIII/65": {
                    "offsets": [30.0],
                    "ra": [83.8221],
                    "dec": [22.0145],
                    "ids": ["NVSS J053457+220008"],
                    "object_url": "https://example.com/obj/",
                }
            },
        }
        result = get_das("05:34:32.0", "+22:00:52", dist_arcmin=5.0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "NVSS J053457+220008")
        self.assertIn("sep", result[0])
        self.assertIn("object_url", result[0])

    @patch(
        "candidate_app.views_utils.requests.post",
        side_effect=requests_lib.RequestException("timeout"),
    )
    def test_request_exception_returns_empty_list(self, _mock):
        result = get_das("05:34:32.0", "+22:00:52", dist_arcmin=5.0)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# download_rating_csv_zip
# ---------------------------------------------------------------------------


class TestDownloadRatingCsvZip(TestCase):
    def setUp(self):
        user = make_user()
        project = make_project(user)
        obs = make_observation(project)
        beam = make_beam(obs)
        tag = make_tag("real")
        c1 = make_candidate(beam, ra=10.0, dec=20.0)
        c2 = make_candidate(beam, ra=11.0, dec=20.0)
        # All ratings must have a tag — the CSV writer calls rating.tag.name
        # without a None guard.
        make_rating(c1, user, confidence="T", tag=tag)
        make_rating(c1, user, confidence="U", tag=tag)
        make_rating(c2, user, confidence="F", tag=tag)

    def _get_zip(self, table="test"):
        qs = Rating.objects.all()
        response = download_rating_csv_zip(qs, table)
        return zipfile.ZipFile(BytesIO(response.content))

    def test_response_content_type_is_zip(self):
        qs = Rating.objects.all()
        response = download_rating_csv_zip(qs, "test")
        self.assertEqual(response["Content-Type"], "application/zip")

    def test_zip_contains_ratings_and_tags_csvs(self):
        z = self._get_zip("test")
        self.assertIn("test_ratings.csv", z.namelist())
        self.assertIn("all_tags.csv", z.namelist())

    def test_ratings_csv_has_correct_row_count(self):
        z = self._get_zip("test")
        lines = z.read("test_ratings.csv").decode().strip().splitlines()
        # 1 header + 3 data rows
        self.assertEqual(len(lines), 4)


# ---------------------------------------------------------------------------
# get_upload_token
# ---------------------------------------------------------------------------


class TestGetUploadToken(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        from rest_framework.authtoken.models import Token

        self.user = make_user()
        self.token = Token.objects.get(user=self.user)

    def test_valid_token_returns_token_and_no_error(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION=self.token.key)
        token, err = get_upload_token(request)
        self.assertIsNotNone(token)
        self.assertIsNone(err)

    def test_missing_authorization_header_returns_400(self):
        request = self.factory.get("/")
        token, err = get_upload_token(request)
        self.assertIsNone(token)
        self.assertEqual(err.status_code, 400)

    def test_invalid_token_returns_403(self):
        request = self.factory.get("/", HTTP_AUTHORIZATION="notavalidtoken")
        token, err = get_upload_token(request)
        self.assertIsNone(token)
        self.assertEqual(err.status_code, 403)


# ---------------------------------------------------------------------------
# get_session_filter_data
# ---------------------------------------------------------------------------


class TestGetSessionFilterData(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @_patch_defaults
    def test_empty_session_returns_defaults(self, _mock):
        request = self.factory.get("/")
        request.session = {}
        session_data, default_inputs, default_float_values, default_all_values = (
            get_session_filter_data(request)
        )
        self.assertEqual(session_data, default_all_values)

    @_patch_defaults
    def test_session_with_data_is_returned_as_is(self, _mock):
        request = self.factory.get("/")
        custom = {"is_best_beam": "false", "rated": "true"}
        request.session = {"current_filter_data": custom}
        session_data, _, _, _ = get_session_filter_data(request)
        self.assertEqual(session_data, custom)
