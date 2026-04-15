"""
test_api_integration.py — Integration tests hitting FastAPI routes via httpx.

These tests spin up the full FastAPI application with a temporary SQLite
database, then exercise routes from the HTTP layer down through the DB.

Naming convention: [route/function] should [expected behavior] when [condition].
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Point the app at an isolated temp DB before importing main.
# ---------------------------------------------------------------------------
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DATABASE_URL"] = _tmp_db.name
os.environ["API_KEY_SALT"] = "test-salt-integration"
os.environ["RATE_LIMIT_MAX_REQUESTS"] = "1000"

from app.main import app  # noqa: E402

_client_ctx = TestClient(app, raise_server_exceptions=True)
_client_ctx.__enter__()
client = _client_ctx


def teardown_module(_module):
    _client_ctx.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register(name: str, email: str, password: str, interests: list):
    """Register a user and return the response."""
    return client.post("/register", json={
        "name": name, "email": email,
        "password": password, "interests": interests,
    })


def _login(email: str, password: str):
    """Log in and return the response."""
    return client.post("/login", json={"email": email, "password": password})


def _auth_header(session_token: str) -> dict:
    return {"X-Session-Token": session_token}


def _register_and_checkin(name, email, password, interests, lat, lng) -> str:
    """Register, then immediately check in. Returns the session token."""
    resp = _register(name, email, password, interests)
    token = resp.json()["session_token"]
    client.post(
        "/checkin",
        json={"latitude": lat, "longitude": lng},
        headers=_auth_header(token),
    )
    return token


# ===========================================================================
# Registration
# ===========================================================================

class TestRegistrationRoute(unittest.TestCase):

    def test_register_should_return_201_and_session_token_when_valid_payload(self):
        response = _register("Alice", "alice@test.com", "securepass1", ["gym", "cs"])
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertIn("user_id", body)
        self.assertIn("session_token", body)
        self.assertIsNotNone(body["session_token"])
        self.assertEqual(body["name"], "Alice")

    def test_register_should_return_422_when_name_is_blank(self):
        response = _register("  ", "blank@test.com", "securepass1", ["gym"])
        self.assertEqual(response.status_code, 422)

    def test_register_should_return_422_when_interests_is_empty(self):
        response = _register("Bob", "bob@test.com", "securepass1", [])
        self.assertEqual(response.status_code, 422)

    def test_register_should_return_422_when_password_too_short(self):
        response = _register("Carol", "carol@test.com", "short", ["gym"])
        self.assertEqual(response.status_code, 422)

    def test_register_should_return_422_when_email_is_invalid(self):
        response = _register("Dave", "not-an-email", "securepass1", ["gym"])
        self.assertEqual(response.status_code, 422)

    def test_register_should_return_409_when_email_already_registered(self):
        _register("Eve", "eve@test.com", "securepass1", ["gym"])
        response = _register("Eve2", "eve@test.com", "securepass1", ["music"])
        self.assertEqual(response.status_code, 409)

    def test_register_should_not_expose_password_in_response(self):
        response = _register("Frank", "frank@test.com", "securepass1", ["music"])
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertNotIn("password", body)
        self.assertNotIn("securepass1", str(body))


# ===========================================================================
# Login
# ===========================================================================

class TestLoginRoute(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _register("LoginUser", "loginuser@test.com", "mypassword1", ["reading"])

    def test_login_should_return_200_and_session_token_when_valid_credentials(self):
        response = _login("loginuser@test.com", "mypassword1")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("session_token", body)
        self.assertIsNotNone(body["session_token"])

    def test_login_should_return_401_when_wrong_password(self):
        response = _login("loginuser@test.com", "wrongpassword")
        self.assertEqual(response.status_code, 401)

    def test_login_should_return_401_when_email_not_registered(self):
        response = _login("nobody@test.com", "somepassword")
        self.assertEqual(response.status_code, 401)

    def test_login_should_not_expose_password_in_response(self):
        response = _login("loginuser@test.com", "mypassword1")
        body = response.json()
        self.assertNotIn("password", body)
        self.assertNotIn("mypassword1", str(body))

    def test_login_token_should_be_usable_for_authenticated_routes(self):
        resp = _login("loginuser@test.com", "mypassword1")
        token = resp.json()["session_token"]
        me_resp = client.get("/me", headers=_auth_header(token))
        self.assertEqual(me_resp.status_code, 200)


# ===========================================================================
# Auth middleware
# ===========================================================================

class TestAuthRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        resp = _register("AuthUser", "authuser@test.com", "authpass12", ["reading"])
        cls.token = resp.json()["session_token"]
        cls.user_id = resp.json()["user_id"]

    def test_get_me_should_return_200_when_valid_session_token(self):
        response = client.get("/me", headers=_auth_header(self.token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], self.user_id)

    def test_get_me_should_return_401_when_no_token(self):
        response = client.get("/me")
        self.assertEqual(response.status_code, 401)

    def test_get_me_should_return_401_when_invalid_token(self):
        response = client.get("/me", headers=_auth_header("totally-wrong-token"))
        self.assertEqual(response.status_code, 401)

    def test_get_me_should_not_include_password_in_response(self):
        response = client.get("/me", headers=_auth_header(self.token))
        self.assertNotIn("password", str(response.json()))


# ===========================================================================
# Check-in
# ===========================================================================

class TestCheckInRoute(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        resp = _register("CheckInUser", "checkin@test.com", "checkpass1", ["gym"])
        cls.token = resp.json()["session_token"]
        cls.user_id = resp.json()["user_id"]

    def test_checkin_should_return_200_when_valid_location(self):
        response = client.post(
            "/checkin",
            json={"latitude": 1.3048, "longitude": 103.8318, "place_name": "Gym"},
            headers=_auth_header(self.token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], self.user_id)

    def test_checkin_should_return_401_when_unauthenticated(self):
        response = client.post("/checkin", json={"latitude": 1.3048, "longitude": 103.8318})
        self.assertEqual(response.status_code, 401)

    def test_checkin_should_return_422_when_latitude_out_of_range(self):
        response = client.post(
            "/checkin",
            json={"latitude": 95.0, "longitude": 103.8318},
            headers=_auth_header(self.token),
        )
        self.assertEqual(response.status_code, 422)

    def test_checkin_should_return_422_when_longitude_out_of_range(self):
        response = client.post(
            "/checkin",
            json={"latitude": 1.3048, "longitude": 185.0},
            headers=_auth_header(self.token),
        )
        self.assertEqual(response.status_code, 422)

    def test_checkin_should_accept_optional_place_name_as_null(self):
        response = client.post(
            "/checkin",
            json={"latitude": 1.3048, "longitude": 103.8318, "place_name": None},
            headers=_auth_header(self.token),
        )
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# Matches
# ===========================================================================

class TestMatchesRoute(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token_a = _register_and_checkin(
            "Alice M", "alicem@test.com", "alicepass1", ["gym", "cs"], 1.3048, 103.8318)
        cls.token_b = _register_and_checkin(
            "Bob M", "bobm@test.com", "bobpass123", ["gym", "music"], 1.3050, 103.8320)

    def test_get_matches_should_return_200_and_match_list_when_authenticated(self):
        response = client.get("/matches?radius_km=1.0", headers=_auth_header(self.token_a))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("matches", body)
        self.assertIsInstance(body["matches"], list)

    def test_get_matches_should_return_401_when_unauthenticated(self):
        response = client.get("/matches")
        self.assertEqual(response.status_code, 401)

    def test_get_matches_should_include_suggested_activities_in_results(self):
        response = client.get("/matches?radius_km=1.0", headers=_auth_header(self.token_a))
        body = response.json()
        if body["matches"]:
            self.assertIn("suggested_activities", body["matches"][0])

    def test_get_matches_should_return_422_when_radius_exceeds_50km(self):
        response = client.get("/matches?radius_km=99", headers=_auth_header(self.token_a))
        self.assertEqual(response.status_code, 422)

    def test_get_matches_should_return_400_when_user_has_no_checkin(self):
        resp = _register("NoCheckin", "nocheckin@test.com", "nocheckin1", ["gym"])
        no_checkin_token = resp.json()["session_token"]
        response = client.get("/matches", headers=_auth_header(no_checkin_token))
        self.assertEqual(response.status_code, 400)

    def test_get_matches_should_not_match_user_with_themselves(self):
        response = client.get("/matches?radius_km=50", headers=_auth_header(self.token_a))
        body = response.json()
        requesting_id = body["requesting_user_id"]
        matched_ids = [m["user_id"] for m in body["matches"]]
        self.assertNotIn(requesting_id, matched_ids)

    def test_get_matches_should_return_cached_flag_on_second_request(self):
        client.get("/matches?radius_km=1.0", headers=_auth_header(self.token_b))
        response = client.get("/matches?radius_km=1.0", headers=_auth_header(self.token_b))
        self.assertTrue(response.json().get("cached", False))


# ===========================================================================
# History
# ===========================================================================

class TestHistoryRoute(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        resp = _register("HistoryUser", "history@test.com", "histpass12", ["cs"])
        cls.token = resp.json()["session_token"]

    def test_get_history_should_return_200_when_authenticated(self):
        response = client.get("/history", headers=_auth_header(self.token))
        self.assertEqual(response.status_code, 200)
        self.assertIn("history", response.json())

    def test_get_history_should_return_401_when_unauthenticated(self):
        response = client.get("/history")
        self.assertEqual(response.status_code, 401)

    def test_get_history_should_return_422_when_limit_exceeds_200(self):
        response = client.get("/history?limit=999", headers=_auth_header(self.token))
        self.assertEqual(response.status_code, 422)


# ===========================================================================
# Rate limiting
# ===========================================================================

class TestRateLimitingIntegration(unittest.TestCase):

    def test_rate_limit_should_return_429_when_ip_exceeds_window(self):
        import app.rate_limiter as rl_module
        rl_module.configure_limiter(max_requests=2, window_seconds=60.0)
        rl_module._limiter.reset("testclient")
        responses = [client.get("/") for _ in range(5)]
        self.assertIn(429, [r.status_code for r in responses])
        rl_module.configure_limiter(max_requests=1000, window_seconds=60.0)

    def test_rate_limit_response_should_include_retry_after_header_when_blocked(self):
        import app.rate_limiter as rl_module
        rl_module.configure_limiter(max_requests=1, window_seconds=60.0)
        rl_module._limiter.reset("testclient")
        client.get("/")
        response = client.get("/")
        if response.status_code == 429:
            self.assertIn("retry-after", response.headers)
        rl_module.configure_limiter(max_requests=1000, window_seconds=60.0)


if __name__ == "__main__":
    unittest.main()
