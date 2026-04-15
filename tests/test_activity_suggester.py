"""
test_activity_suggester.py — Unit tests for the activity suggestion engine.

Naming convention: [function] should [expected behavior] when [condition].
"""

import unittest

from app.activity_suggester import _DEFAULT_ACTIVITIES, suggest_activities


class TestSuggestActivities(unittest.TestCase):

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_suggest_activities_should_return_gym_activities_when_gym_tag_provided(self):
        result = suggest_activities(["gym"])
        self.assertIn("workout together", result)
        self.assertIn("spot each other", result)

    def test_suggest_activities_should_return_coding_activities_when_cs_tag_provided(self):
        result = suggest_activities(["cs"])
        self.assertIn("pair program", result)
        self.assertIn("hackathon", result)

    def test_suggest_activities_should_return_union_when_multiple_tags_provided(self):
        result = suggest_activities(["gym", "music"])
        # Should include activities from both tags
        gym_activities = {"workout together", "spot each other", "try a new class"}
        music_activities = {"jam session", "playlist swap", "concert"}
        self.assertTrue(gym_activities.intersection(result))
        self.assertTrue(music_activities.intersection(result))

    def test_suggest_activities_should_deduplicate_when_tags_share_activities(self):
        # "cs" and "coding" both map to "pair program" and "hackathon"
        result = suggest_activities(["cs", "coding"])
        # No duplicates
        self.assertEqual(len(result), len(set(result)))

    def test_suggest_activities_should_return_sorted_list(self):
        result = suggest_activities(["gym", "music"])
        self.assertEqual(result, sorted(result))

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_suggest_activities_should_return_defaults_when_empty_list(self):
        result = suggest_activities([])
        self.assertEqual(result, list(_DEFAULT_ACTIVITIES))

    def test_suggest_activities_should_return_defaults_when_unknown_tags_only(self):
        result = suggest_activities(["unicorn_hobby", "xyzzy"])
        self.assertEqual(result, list(_DEFAULT_ACTIVITIES))

    def test_suggest_activities_should_handle_mixed_known_and_unknown_tags(self):
        result = suggest_activities(["gym", "unknown_tag_xyz"])
        # Should still return gym activities (not defaults)
        self.assertIn("workout together", result)

    def test_suggest_activities_should_be_case_insensitive_for_lookup(self):
        """Tags arriving from DB are already lowercased, but test robustness."""
        result_lower = suggest_activities(["gym"])
        result_upper = suggest_activities(["GYM"])
        # Both should resolve the same (suggest_activities calls .lower())
        self.assertEqual(result_lower, result_upper)

    def test_suggest_activities_should_not_modify_input_list(self):
        interests = ["gym", "music"]
        original = list(interests)
        suggest_activities(interests)
        self.assertEqual(interests, original)

    def test_suggest_activities_should_return_list_type(self):
        result = suggest_activities(["gym"])
        self.assertIsInstance(result, list)

    def test_suggest_activities_should_return_non_empty_list_for_every_known_tag(self):
        from app.activity_suggester import INTEREST_ACTIVITIES
        for tag in INTEREST_ACTIVITIES:
            result = suggest_activities([tag])
            self.assertGreater(len(result), 0, f"Empty result for tag: {tag}")

    def test_suggest_activities_should_handle_single_char_tag_gracefully(self):
        result = suggest_activities(["a"])
        # Unknown tag — should fall back to defaults without raising
        self.assertEqual(result, list(_DEFAULT_ACTIVITIES))

    def test_suggest_activities_should_handle_max_interests_without_error(self):
        from app.activity_suggester import INTEREST_ACTIVITIES
        all_tags = list(INTEREST_ACTIVITIES.keys())
        result = suggest_activities(all_tags)
        self.assertGreater(len(result), 0)


if __name__ == "__main__":
    unittest.main()
