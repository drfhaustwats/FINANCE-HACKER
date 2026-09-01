import os
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import dotenv
import httpx
from fastapi import Response


# Keep server import-time clients detached from local credentials and services.
os.environ["MONGO_URL"] = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=1"
os.environ["DB_NAME"] = "finance_hacker_cookie_auth_unit_tests"
os.environ["SECRET_KEY"] = "cookie-auth-tests-only"
os.environ["PLAID_CLIENT_ID"] = ""
os.environ["PLAID_SECRET"] = ""
os.environ["PLAID_TOKEN_ENCRYPTION_KEY"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""
os.environ["GMAIL_EMAIL"] = ""
os.environ["GMAIL_APP_PASSWORD"] = ""
os.environ["FRONTEND_URL"] = ""

_real_load_dotenv = dotenv.load_dotenv
try:
    dotenv.load_dotenv = lambda *args, **kwargs: False
    from backend import server  # noqa: E402
finally:
    dotenv.load_dotenv = _real_load_dotenv


class CookieAuthenticationTests(unittest.IsolatedAsyncioTestCase):
    def assert_secure_session_cookie(self, header: str, expected_value: str):
        normalized = header.lower()
        self.assertIn(
            f"{server.AUTH_COOKIE_NAME}={expected_value}".lower(),
            normalized,
        )
        self.assertIn("httponly", normalized)
        self.assertIn("secure", normalized)
        self.assertIn("samesite=lax", normalized)
        self.assertIn("path=/", normalized)
        self.assertIn(
            f"max-age={server.AUTH_COOKIE_MAX_AGE_SECONDS}",
            normalized,
        )
        self.assertNotIn("domain=", normalized)

    def test_cookie_is_secure_httponly_host_only_and_eight_hours(self):
        response = Response()
        with patch.object(server, "AUTH_COOKIE_SECURE", True):
            server.set_auth_cookie(response, "browser-jwt")

        self.assertEqual(server.ACCESS_TOKEN_EXPIRE_MINUTES, 8 * 60)
        self.assert_secure_session_cookie(
            response.headers["set-cookie"],
            "browser-jwt",
        )

    async def test_login_sets_cookie_and_keeps_bearer_response_compatibility(self):
        user = {
            "id": "user-1",
            "email": "user@example.test",
        }
        users = SimpleNamespace(update_one=AsyncMock())
        response = Response()

        with (
            patch.object(server, "authenticate_user", AsyncMock(return_value=user)),
            patch.object(server, "db", SimpleNamespace(users=users)),
            patch.object(server, "create_access_token", return_value="login-jwt"),
            patch.object(server, "AUTH_COOKIE_SECURE", True),
        ):
            token = await server.login_user(
                SimpleNamespace(username=user["email"], password="test-password"),
                response,
            )

        self.assertEqual(token.access_token, "login-jwt")
        self.assertEqual(token.token_type, "bearer")
        self.assert_secure_session_cookie(
            response.headers["set-cookie"],
            "login-jwt",
        )

    async def test_google_exchange_sets_same_cookie(self):
        raw_code = "single-use-google-oauth-code-1234567890abcdef"
        login_code = {
            "code_hash": server.hash_google_oauth_login_code(raw_code),
            "user_id": "user-1",
        }
        oauth_login_codes = SimpleNamespace(
            find_one_and_update=AsyncMock(return_value=login_code)
        )
        users = SimpleNamespace(
            find_one=AsyncMock(
                return_value={"id": "user-1", "email": "user@example.test"}
            )
        )
        response = Response()

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(oauth_login_codes=oauth_login_codes, users=users),
            ),
            patch.object(server, "create_access_token", return_value="google-jwt"),
            patch.object(server, "AUTH_COOKIE_SECURE", True),
        ):
            token = await server.exchange_google_oauth_login_code(
                server.GoogleOAuthCodeExchangeRequest(code=raw_code),
                response,
            )

        self.assertEqual(token.access_token, "google-jwt")
        self.assert_secure_session_cookie(
            response.headers["set-cookie"],
            "google-jwt",
        )

    async def test_cookie_auth_fallback_preserves_bearer_precedence(self):
        request = SimpleNamespace(
            cookies={server.AUTH_COOKIE_NAME: "cookie-jwt"}
        )

        cookie_token = await server.get_request_access_token(request, None)
        bearer_token = await server.get_request_access_token(request, "bearer-jwt")

        self.assertEqual(cookie_token, "cookie-jwt")
        self.assertEqual(bearer_token, "bearer-jwt")

    async def test_me_endpoint_accepts_cookie_without_authorization_header(self):
        user = {
            "id": "user-1",
            "email": "user@example.test",
            "username": "user",
            "full_name": "Example User",
            "role": "user",
            "household_id": None,
            "created_at": datetime.utcnow(),
            "last_login": None,
        }
        token = server.create_access_token({"sub": user["email"]})
        transport = httpx.ASGITransport(app=server.app)

        with patch.object(
            server,
            "get_user_by_email",
            AsyncMock(return_value=user),
        ):
            async with httpx.AsyncClient(
                transport=transport,
                base_url="https://api.fintrack.example.test",
                cookies={server.AUTH_COOKIE_NAME: token},
            ) as client:
                response = await client.get("/auth/me")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], user["id"])
        self.assertNotIn("authorization", response.request.headers)

    async def test_logout_expires_cookie_with_matching_scope(self):
        with patch.object(server, "AUTH_COOKIE_SECURE", True):
            response = await server.logout_user()

        normalized = response.headers["set-cookie"].lower()
        self.assertEqual(response.status_code, 204)
        self.assertIn(f"{server.AUTH_COOKIE_NAME}=", normalized)
        self.assertIn("max-age=0", normalized)
        self.assertIn("httponly", normalized)
        self.assertIn("secure", normalized)
        self.assertIn("samesite=lax", normalized)
        self.assertIn("path=/", normalized)
        self.assertNotIn("domain=", normalized)

    def test_default_jwt_expiration_is_eight_hours(self):
        issued = datetime.utcnow()
        token = server.create_access_token({"sub": "user@example.test"})
        payload = server.jwt.decode(
            token,
            server.SECRET_KEY,
            algorithms=[server.ALGORITHM],
        )
        expires = datetime.utcfromtimestamp(payload["exp"])

        self.assertGreater(expires, issued + timedelta(hours=7, minutes=59))
        self.assertLess(expires, issued + timedelta(hours=8, minutes=1))

    def test_real_password_hash_backend_round_trip(self):
        password = "production-login-regression-probe"
        password_hash = server.get_password_hash(password)

        self.assertTrue(server.verify_password(password, password_hash))
        self.assertFalse(server.verify_password("wrong-password", password_hash))


if __name__ == "__main__":
    unittest.main()
