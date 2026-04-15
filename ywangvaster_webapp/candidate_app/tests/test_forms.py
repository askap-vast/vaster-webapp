"""Tests for candidate_app forms."""

from django.test import TestCase

from candidate_app.forms import CandidateFilterForm, RateCandidateForm, RatingFilterForm
from candidate_app.tests.factories import (
    make_observation,
    make_project,
    make_tag,
    make_user,
)

# ---------------------------------------------------------------------------
# CandidateFilterForm
# ---------------------------------------------------------------------------


class TestCandidateFilterForm(TestCase):
    def setUp(self):
        user = make_user()
        self.project = make_project(user)
        other_project = make_project(user)
        self.obs = make_observation(self.project)
        self.other_obs = make_observation(other_project)

    def test_observation_queryset_scoped_to_project(self):
        form = CandidateFilterForm(selected_project_hash_id=self.project.hash_id)
        qs = form.fields["observation"].queryset
        self.assertIn(self.obs, qs)
        self.assertNotIn(self.other_obs, qs)

    def test_observation_queryset_all_when_no_project(self):
        form = CandidateFilterForm()
        qs = form.fields["observation"].queryset
        self.assertIn(self.obs, qs)
        self.assertIn(self.other_obs, qs)

    def test_post_clean_converts_observation_to_hash_id_string(self):
        form = CandidateFilterForm(
            data={"is_best_beam": "true", "observation": str(self.obs.hash_id)},
            selected_project_hash_id=self.project.hash_id,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["observation"], str(self.obs.hash_id))

    def test_post_clean_converts_tag_to_hash_id_string(self):
        tag = make_tag("rfi")
        form = CandidateFilterForm(
            data={"is_best_beam": "true", "tag": str(tag.hash_id)},
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["tag"], str(tag.hash_id))

    def test_post_clean_leaves_none_observation_alone(self):
        form = CandidateFilterForm(data={"is_best_beam": "true"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data.get("observation"))

    def test_valid_without_optional_fields(self):
        form = CandidateFilterForm(data={"is_best_beam": "true"})
        self.assertTrue(form.is_valid(), form.errors)


# ---------------------------------------------------------------------------
# RatingFilterForm
# ---------------------------------------------------------------------------


class TestRatingFilterForm(TestCase):
    def setUp(self):
        self.user = make_user()
        self.project = make_project(self.user)
        other_project = make_project(self.user)
        self.obs = make_observation(self.project)
        self.other_obs = make_observation(other_project)

    def test_observation_queryset_scoped_to_project(self):
        form = RatingFilterForm(selected_project_hash_id=self.project.hash_id)
        qs = form.fields["observation"].queryset
        self.assertIn(self.obs, qs)
        self.assertNotIn(self.other_obs, qs)

    def test_post_clean_converts_observation_to_hash_id_string(self):
        form = RatingFilterForm(
            data={"observation": str(self.obs.hash_id)},
            selected_project_hash_id=self.project.hash_id,
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["observation"], str(self.obs.hash_id))

    def test_post_clean_converts_tag_to_hash_id_string(self):
        tag = make_tag("pulsar")
        form = RatingFilterForm(data={"tag": str(tag.hash_id)})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["tag"], str(tag.hash_id))

    def test_post_clean_converts_user_to_id_string(self):
        form = RatingFilterForm(data={"user": str(self.user.pk)})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["user"], str(self.user.pk))

    def test_valid_with_empty_submission(self):
        form = RatingFilterForm(data={})
        self.assertTrue(form.is_valid(), form.errors)


# ---------------------------------------------------------------------------
# RateCandidateForm
# ---------------------------------------------------------------------------


class TestRateCandidateForm(TestCase):
    def setUp(self):
        self.tag = make_tag("real")

    def test_valid_with_confidence_and_tag(self):
        form = RateCandidateForm(
            data={"confidence": "T", "tag": self.tag.name, "notes": ""}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_with_notes(self):
        form = RateCandidateForm(
            data={"confidence": "F", "tag": self.tag.name, "notes": "looks like RFI"}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["notes"], "looks like RFI")

    def test_all_confidence_choices_are_valid(self):
        for code in ("T", "F", "U"):
            form = RateCandidateForm(
                data={"confidence": code, "tag": self.tag.name, "notes": ""}
            )
            self.assertTrue(form.is_valid(), f"confidence={code!r} should be valid")

    def test_invalid_without_confidence(self):
        form = RateCandidateForm(data={"tag": self.tag.name, "notes": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("confidence", form.errors)

    def test_invalid_without_tag(self):
        form = RateCandidateForm(data={"confidence": "T", "notes": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("tag", form.errors)
