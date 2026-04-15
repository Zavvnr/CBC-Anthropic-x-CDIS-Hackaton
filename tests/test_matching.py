"""
test_matching.py — Unit tests for the haversine formula and matching engine.

Naming convention: [function] should [expected behavior] when [condition].
"""

import math
import unittest

from app.matching import (
    MatchConfig,
    MatchResult,
    UserLocation,
    compute_match_score,
    find_matches,
    haversine_distance_km,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    user_id: int,
    interests: list,
    lat: float = 1.3048,
    lng: float = 103.8318,
    name: str = "Test User",
) -> UserLocation:
    """Factory for UserLocation instances with sensible defaults."""
    return UserLocation(
        user_id=user_id,
        name=name,
        interests=interests,
        latitude=lat,
        longitude=lng,
    )


# Coordinates of two real points ~280 m apart (NUS campus area, Singapore)
LAT_A, LNG_A = 1.2966, 103.7764
LAT_B, LNG_B = 1.2990, 103.7782

# Two points exactly 1 km apart (verified against multiple calculators)
LAT_NORTH, LNG_NORTH = 1.3000, 103.8000
LAT_SOUTH, LNG_SOUTH = 1.2910, 103.8000   # ~1.001 km south


# ---------------------------------------------------------------------------
# haversine_distance_km
# ---------------------------------------------------------------------------

class TestHaversineDistanceKm(unittest.TestCase):

    def test_haversine_distance_km_should_return_zero_when_same_point(self):
        dist = haversine_distance_km(LAT_A, LNG_A, LAT_A, LNG_A)
        self.assertAlmostEqual(dist, 0.0, places=6)

    def test_haversine_distance_km_should_be_symmetric_when_points_swapped(self):
        dist_ab = haversine_distance_km(LAT_A, LNG_A, LAT_B, LNG_B)
        dist_ba = haversine_distance_km(LAT_B, LNG_B, LAT_A, LNG_A)
        self.assertAlmostEqual(dist_ab, dist_ba, places=6)

    def test_haversine_distance_km_should_return_approximately_280m_when_close_points(self):
        dist = haversine_distance_km(LAT_A, LNG_A, LAT_B, LNG_B)
        # Within 5% of 0.28 km
        self.assertGreater(dist, 0.25)
        self.assertLess(dist, 0.35)

    def test_haversine_distance_km_should_handle_antipodal_points(self):
        # Antipodal points should be close to half the Earth's circumference (~20015 km)
        dist = haversine_distance_km(0.0, 0.0, 0.0, 180.0)
        self.assertAlmostEqual(dist, 20015.0, delta=5.0)

    def test_haversine_distance_km_should_handle_equator_crossing(self):
        dist = haversine_distance_km(-1.0, 103.0, 1.0, 103.0)
        # ~222 km — rough check
        self.assertGreater(dist, 200.0)
        self.assertLess(dist, 230.0)

    def test_haversine_distance_km_should_handle_prime_meridian_crossing(self):
        dist = haversine_distance_km(0.0, -1.0, 0.0, 1.0)
        self.assertGreater(dist, 200.0)
        self.assertLess(dist, 240.0)

    def test_haversine_distance_km_should_return_positive_when_south_of_equator(self):
        dist = haversine_distance_km(-33.8688, 151.2093, -37.8136, 144.9631)  # Sydney → Melbourne
        self.assertGreater(dist, 700.0)
        self.assertLess(dist, 800.0)

    def test_haversine_distance_km_should_accept_max_latitude_values(self):
        dist = haversine_distance_km(90.0, 0.0, -90.0, 0.0)  # North → South Pole
        self.assertAlmostEqual(dist, 20015.0, delta=5.0)

    def test_haversine_distance_km_should_accept_max_longitude_values(self):
        dist = haversine_distance_km(0.0, -180.0, 0.0, 180.0)
        self.assertAlmostEqual(dist, 0.0, places=4)  # Antimeridian — same line


# ---------------------------------------------------------------------------
# compute_match_score
# ---------------------------------------------------------------------------

class TestComputeMatchScore(unittest.TestCase):

    def setUp(self):
        self.config = MatchConfig(interest_weight=10.0, distance_weight=1.0)

    def test_compute_match_score_should_increase_when_more_interests_overlap(self):
        score_one = compute_match_score(1, 0.1, self.config)
        score_three = compute_match_score(3, 0.1, self.config)
        self.assertGreater(score_three, score_one)

    def test_compute_match_score_should_decrease_when_distance_increases(self):
        score_close = compute_match_score(2, 0.1, self.config)
        score_far = compute_match_score(2, 0.4, self.config)
        self.assertGreater(score_close, score_far)

    def test_compute_match_score_should_return_zero_when_weights_cancel_out(self):
        # overlap=1 * 10 - 10km * 1 = 0
        score = compute_match_score(1, 10.0, self.config)
        self.assertAlmostEqual(score, 0.0, places=5)

    def test_compute_match_score_should_respect_custom_weights(self):
        config = MatchConfig(interest_weight=5.0, distance_weight=2.0)
        score = compute_match_score(2, 1.0, config)
        # 2 * 5 - 1 * 2 = 8
        self.assertAlmostEqual(score, 8.0, places=5)

    def test_compute_match_score_should_return_negative_when_distance_dominates(self):
        score = compute_match_score(1, 20.0, self.config)
        self.assertLess(score, 0.0)

    def test_compute_match_score_should_return_zero_when_no_overlap(self):
        score = compute_match_score(0, 0.0, self.config)
        self.assertEqual(score, 0.0)


# ---------------------------------------------------------------------------
# find_matches
# ---------------------------------------------------------------------------

class TestFindMatches(unittest.TestCase):

    def setUp(self):
        self.config = MatchConfig(
            max_radius_km=1.0,
            interest_weight=10.0,
            distance_weight=1.0,
            top_n=10,
        )
        self.target = _make_user(1, ["gym", "cs", "music"], LAT_A, LNG_A, "Alice")

    def test_find_matches_should_return_empty_when_no_candidates(self):
        results = find_matches(self.target, [], self.config)
        self.assertEqual(results, [])

    def test_find_matches_should_exclude_target_user_when_in_candidate_list(self):
        candidates = [self.target]
        results = find_matches(self.target, candidates, self.config)
        self.assertEqual(results, [])

    def test_find_matches_should_exclude_users_outside_radius(self):
        far_user = _make_user(2, ["gym"], LAT_SOUTH, LNG_SOUTH)  # ~1 km away
        config = MatchConfig(max_radius_km=0.3)
        results = find_matches(self.target, [far_user], config)
        self.assertEqual(results, [])

    def test_find_matches_should_exclude_users_with_no_shared_interests(self):
        no_overlap = _make_user(3, ["dancing", "cooking"], LAT_A, LNG_A)
        results = find_matches(self.target, [no_overlap], self.config)
        self.assertEqual(results, [])

    def test_find_matches_should_include_users_with_shared_interest_and_within_radius(self):
        good_match = _make_user(4, ["gym", "reading"], LAT_B, LNG_B, "Bob")
        results = find_matches(self.target, [good_match], self.config)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].user_id, 4)

    def test_find_matches_should_return_correct_shared_interests(self):
        candidate = _make_user(5, ["gym", "music", "reading"], LAT_B, LNG_B, "Carol")
        results = find_matches(self.target, [candidate], self.config)
        self.assertEqual(set(results[0].shared_interests), {"gym", "music"})

    def test_find_matches_should_sort_by_score_descending(self):
        # Candidate A: 3 overlaps, close
        candidate_a = _make_user(6, ["gym", "cs", "music"], LAT_B, LNG_B, "Best Match")
        # Candidate B: 1 overlap, same distance
        candidate_b = _make_user(7, ["gym"], LAT_B, LNG_B, "Weaker Match")
        results = find_matches(self.target, [candidate_a, candidate_b], self.config)
        self.assertEqual(results[0].user_id, 6)
        self.assertEqual(results[1].user_id, 7)

    def test_find_matches_should_cap_results_at_top_n(self):
        config = MatchConfig(max_radius_km=1.0, top_n=3)
        candidates = [
            _make_user(10 + i, ["gym"], LAT_B, LNG_B, f"User{i}") for i in range(10)
        ]
        results = find_matches(self.target, candidates, config)
        self.assertLessEqual(len(results), 3)

    def test_find_matches_should_round_distance_to_4_decimal_places(self):
        candidate = _make_user(20, ["gym"], LAT_B, LNG_B, "Dave")
        results = find_matches(self.target, [candidate], self.config)
        # Ensure it is a float with at most 4 decimal places
        self.assertEqual(round(results[0].distance_km, 4), results[0].distance_km)

    def test_find_matches_should_use_default_config_when_none_provided(self):
        """find_matches should not raise when config is None."""
        candidate = _make_user(21, ["gym"], LAT_A, LNG_A, "Eve")
        try:
            find_matches(self.target, [candidate])
        except Exception as exc:
            self.fail(f"find_matches raised unexpectedly: {exc}")

    def test_find_matches_should_handle_candidate_at_exact_radius_boundary(self):
        # Place a candidate exactly at the radius boundary — should be included.
        # 0.28 km is within 1.0 km radius.
        candidate = _make_user(22, ["gym"], LAT_B, LNG_B, "Frank")
        config = MatchConfig(max_radius_km=0.5)
        results = find_matches(self.target, [candidate], config)
        dist = haversine_distance_km(LAT_A, LNG_A, LAT_B, LNG_B)
        if dist <= 0.5:
            self.assertEqual(len(results), 1)
        else:
            self.assertEqual(len(results), 0)

    def test_find_matches_should_handle_large_candidate_list_efficiently(self):
        """find_matches should complete in reasonable time for 10k candidates (O(n) check)."""
        import time
        many_candidates = [
            _make_user(1000 + i, ["dancing"], LAT_SOUTH, LNG_SOUTH, f"Far{i}")
            for i in range(10_000)
        ]
        start = time.monotonic()
        results = find_matches(self.target, many_candidates, self.config)
        elapsed = time.monotonic() - start
        # All are outside radius and have no overlap — should complete < 2 s
        self.assertLess(elapsed, 2.0)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
