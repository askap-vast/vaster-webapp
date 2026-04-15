"""Tests for candidate_app serializers."""

from django.test import TestCase

from candidate_app.models import Beam, Candidate, Observation
from candidate_app.serializers import (
    BeamSerializer,
    CandidateSerializer,
    ObservationSerializer,
)
from candidate_app.tests.factories import (
    make_beam,
    make_observation,
    make_project,
    make_user,
)

# ---------------------------------------------------------------------------
# ObservationSerializer
# ---------------------------------------------------------------------------


class TestObservationSerializer(TestCase):
    def setUp(self):
        self.user = make_user()
        self.project = make_project(self.user, id="SER-PROJ")

    def _save(self, obs_id):
        ser = ObservationSerializer(
            data={"proj_id": "SER-PROJ", "id": obs_id},
            context={"user": self.user},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        return ser.save()

    def test_create_returns_observation_instance(self):
        obs = self._save("SB99001")
        self.assertIsInstance(obs, Observation)

    def test_create_links_to_existing_project(self):
        obs = self._save("SB99002")
        self.assertEqual(obs.project, self.project)

    def test_create_upload_owned_by_context_user(self):
        obs = self._save("SB99003")
        self.assertEqual(obs.upload.user, self.user)

    def test_obs_id_stored_correctly(self):
        obs = self._save("SB99004")
        self.assertEqual(obs.id, "SB99004")
        self.assertEqual(obs.proj_id, "SER-PROJ")


# ---------------------------------------------------------------------------
# BeamSerializer
# ---------------------------------------------------------------------------


class TestBeamSerializer(TestCase):
    def setUp(self):
        self.user = make_user()
        self.project = make_project(self.user, id="BEAM-SER-PROJ")
        self.obs = make_observation(self.project, obs_id="SB98001")

    def _save(self, index):
        ser = BeamSerializer(
            data={"proj_id": self.project.id, "obs_id": self.obs.id, "index": index},
            context={"user": self.user},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        return ser.save()

    def test_create_returns_beam_linked_to_observation_and_project(self):
        beam = self._save(5)
        self.assertIsInstance(beam, Beam)
        self.assertEqual(beam.observation, self.obs)
        self.assertEqual(beam.project, self.project)
        self.assertEqual(beam.index, 5)

    def test_create_sets_zero_file_counts_when_no_files_uploaded(self):
        beam = self._save(6)
        self.assertEqual(beam.total_file_count, 0)
        self.assertEqual(beam.total_file_size_bytes, 0)

    def test_upload_owned_by_context_user(self):
        beam = self._save(7)
        self.assertEqual(beam.upload.user, self.user)


# ---------------------------------------------------------------------------
# CandidateSerializer
# ---------------------------------------------------------------------------


class TestCandidateSerializer(TestCase):
    def setUp(self):
        self.user = make_user()
        self.project = make_project(self.user, id="CAND-SER-PROJ")
        self.obs = make_observation(self.project, obs_id="SB97001")
        self.beam = make_beam(self.obs, index=0)

    def _data(self, name="VAST_J999999+00", **overrides):
        base = {
            "proj_id": self.project.id,
            "obs_id": self.obs.id,
            "beam_index": self.beam.index,
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
        base.update(overrides)
        return base

    def _save(self, name="VAST_J999999+00", **overrides):
        ser = CandidateSerializer(
            data=self._data(name, **overrides),
            context={"user": self.user},
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        return ser.save()

    def test_create_links_candidate_to_beam_observation_project(self):
        cand = self._save()
        self.assertIsInstance(cand, Candidate)
        self.assertEqual(cand.project, self.project)
        self.assertEqual(cand.observation, self.obs)
        self.assertEqual(cand.beam, self.beam)

    def test_lone_candidate_becomes_best_beam_after_rerank(self):
        cand = self._save()
        cand.refresh_from_db()
        self.assertTrue(cand.is_best_beam)

    def test_second_nearby_candidate_with_lower_sep_wins_best_beam(self):
        # First candidate — higher beam_sep so should lose
        cand1 = self._save("VAST_J000001+00", ra=10.0, dec=20.0, beam_sep_deg=0.3)
        # Second candidate — same sky position, lower beam_sep → wins
        cand2 = self._save("VAST_J000002+00", ra=10.0001, dec=20.0, beam_sep_deg=0.1)

        cand1.refresh_from_db()
        cand2.refresh_from_db()
        self.assertFalse(cand1.is_best_beam)
        self.assertTrue(cand2.is_best_beam)
