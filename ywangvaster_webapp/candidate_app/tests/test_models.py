from django.test import TestCase

from candidate_app.tests.factories import (
    make_beam,
    make_candidate,
    make_observation,
    make_project,
    make_user,
)

# ---------------------------------------------------------------------------
# Candidate.rerank_best_beam_group()
# ---------------------------------------------------------------------------


class TestRerankBestBeamGroup(TestCase):
    """Tests for Candidate.rerank_best_beam_group().

    Spatial geometry notes:
      BEST_BEAM_RADIUS_DEG = 5 / 3600 ≈ 0.001389 degrees.
      At dec=20°, an RA offset of 0.0001° ≈ 0.34 arcsec on sky — well inside
      the 5 arcsec radius.  An RA offset of 0.01° ≈ 34 arcsec — well outside.
    """

    def setUp(self):
        user = make_user()
        project = make_project(user)
        self.obs = make_observation(project)
        self.beam = make_beam(self.obs)

    def test_lowest_beam_sep_wins(self):
        """Candidate with smallest beam_sep_deg in the group gets is_best_beam=True."""
        c_high = make_candidate(self.beam, ra=10.0, dec=20.0, beam_sep_deg=0.3)
        c_best = make_candidate(self.beam, ra=10.0001, dec=20.0, beam_sep_deg=0.1)
        c_mid = make_candidate(self.beam, ra=10.0002, dec=20.0, beam_sep_deg=0.2)

        c_high.rerank_best_beam_group()

        c_high.refresh_from_db()
        c_best.refresh_from_db()
        c_mid.refresh_from_db()

        self.assertTrue(c_best.is_best_beam)
        self.assertFalse(c_high.is_best_beam)
        self.assertFalse(c_mid.is_best_beam)

    def test_exactly_one_best_beam(self):
        """Exactly one candidate in the group has is_best_beam=True after rerank."""
        candidates = [
            make_candidate(
                self.beam, ra=10.0 + i * 0.0001, dec=20.0, beam_sep_deg=float(i + 1)
            )
            for i in range(5)
        ]

        candidates[0].rerank_best_beam_group()

        best_count = sum(
            1 for c in candidates if (c.refresh_from_db() or True) and c.is_best_beam
        )
        self.assertEqual(best_count, 1)

    def test_candidate_outside_radius_unaffected(self):
        """A candidate >5 arcsec away is not included in the rerank group."""
        c_near = make_candidate(self.beam, ra=10.0, dec=20.0, beam_sep_deg=0.2)
        # ~34 arcsec away at dec=20 — well outside the 5 arcsec grouping radius
        c_far = make_candidate(
            self.beam, ra=10.01, dec=20.0, beam_sep_deg=0.05, is_best_beam=True
        )

        c_near.rerank_best_beam_group()

        c_far.refresh_from_db()
        self.assertTrue(c_far.is_best_beam)

    def test_tiebreak_by_hash_id(self):
        """When beam_sep_deg is equal, the lexicographically smaller hash_id wins."""
        c1 = make_candidate(self.beam, ra=10.0, dec=20.0, beam_sep_deg=0.1)
        c2 = make_candidate(self.beam, ra=10.0001, dec=20.0, beam_sep_deg=0.1)

        c1.rerank_best_beam_group()

        c1.refresh_from_db()
        c2.refresh_from_db()

        expected_winner, expected_loser = (
            (c1, c2) if str(c1.hash_id) < str(c2.hash_id) else (c2, c1)
        )
        self.assertTrue(expected_winner.is_best_beam)
        self.assertFalse(expected_loser.is_best_beam)

    def test_different_observations_not_grouped(self):
        """Candidates in different observations are never grouped, even at the same position."""
        user = make_user()
        project = make_project(user)
        obs2 = make_observation(project)
        beam2 = make_beam(obs2)

        c1 = make_candidate(self.beam, ra=10.0, dec=20.0, beam_sep_deg=0.2)
        # Same sky position but belongs to a different observation
        c2 = make_candidate(
            beam2, ra=10.0001, dec=20.0, beam_sep_deg=0.1, is_best_beam=True
        )

        c1.rerank_best_beam_group()

        c2.refresh_from_db()
        self.assertTrue(c2.is_best_beam)

    def test_single_candidate_becomes_best(self):
        """A lone candidate always becomes is_best_beam=True after reranking."""
        c = make_candidate(self.beam, ra=10.0, dec=20.0)
        self.assertFalse(c.is_best_beam)

        c.rerank_best_beam_group()
        c.refresh_from_db()

        self.assertTrue(c.is_best_beam)


# ---------------------------------------------------------------------------
# Project cached properties
# ---------------------------------------------------------------------------


class TestProjectFileSize(TestCase):
    def setUp(self):
        user = make_user()
        self.project = make_project(user)
        self.obs = make_observation(self.project)

    def test_total_file_size_gb_sums_beams_and_candidates(self):
        """total_file_size_gb correctly aggregates beam and candidate byte totals."""
        beam1 = make_beam(self.obs, index=0)
        beam1.total_file_size_bytes = 1 * 1024**3  # 1 GB
        beam1.save()

        beam2 = make_beam(self.obs, index=1)
        beam2.total_file_size_bytes = 2 * 1024**3  # 2 GB
        beam2.save()

        cand = make_candidate(beam1)
        cand.total_file_size_bytes = 512 * 1024**2  # 0.5 GB
        cand.save()

        # cached_property caches on the instance — use a fresh instance
        from candidate_app.models import Project

        fresh_project = Project.objects.get(pk=self.project.pk)
        self.assertAlmostEqual(fresh_project.total_file_size_gb, 3.5, places=5)

    def test_total_file_size_gb_zero_when_no_files(self):
        from candidate_app.models import Project

        fresh_project = Project.objects.get(pk=self.project.pk)
        self.assertEqual(fresh_project.total_file_size_gb, 0.0)


# ---------------------------------------------------------------------------
# Observation cached properties
# ---------------------------------------------------------------------------


class TestObservationFileStats(TestCase):
    def setUp(self):
        user = make_user()
        project = make_project(user)
        self.obs = make_observation(project)

    def test_total_file_size_gb(self):
        """total_file_size_gb sums across beams and candidates for this observation."""
        from candidate_app.models import Observation

        beam = make_beam(self.obs, index=0)
        beam.total_file_size_bytes = 1 * 1024**3  # 1 GB
        beam.save()

        cand = make_candidate(beam)
        cand.total_file_size_bytes = 1 * 1024**3  # 1 GB
        cand.save()

        fresh_obs = Observation.objects.get(pk=self.obs.pk)
        self.assertAlmostEqual(fresh_obs.total_file_size_gb, 2.0, places=5)

    def test_total_file_count(self):
        """total_file_count sums across beams and candidates for this observation."""
        from candidate_app.models import Observation

        beam = make_beam(self.obs, index=0)
        beam.total_file_count = 3
        beam.save()

        cand = make_candidate(beam)
        cand.total_file_count = 5
        cand.save()

        fresh_obs = Observation.objects.get(pk=self.obs.pk)
        self.assertEqual(fresh_obs.total_file_count, 8)


# ---------------------------------------------------------------------------
# __str__ methods
# ---------------------------------------------------------------------------


class TestStrMethods(TestCase):
    def setUp(self):
        user = make_user()
        self.project = make_project(user, id="PROJ-X")
        self.obs = make_observation(self.project, obs_id="SB99999")

    def test_project_str(self):
        self.assertEqual(str(self.project), "PROJ-X")

    def test_observation_str(self):
        self.assertEqual(str(self.obs), "SB99999 (PROJ-X)")
