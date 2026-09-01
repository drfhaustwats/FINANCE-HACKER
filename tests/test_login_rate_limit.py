import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import dotenv
from fastapi import HTTPException, Response


# Keep server import-time clients detached from local credentials and services.
os.environ["APP_ENV"] = "development"
os.environ["MONGO_URL"] = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=1"
os.environ["DB_NAME"] = "finance_hacker_login_limit_unit_tests"
os.environ["SECRET_KEY"] = "login-rate-limit-tests-only-secret-key"
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


class LoginRateLimitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        server.LOGIN_FAILURE_LIMITER.clear()

    def tearDown(self):
        server.LOGIN_FAILURE_LIMITER.clear()

    @staticmethod
    def request_from(ip_address):
        return SimpleNamespace(client=SimpleNamespace(host=ip_address))

    async def test_ten_normalized_failures_block_next_attempt(self):
        request = self.request_from("203.0.113.10")
        authenticate = AsyncMock(return_value=None)

        with patch.object(server, "authenticate_user", authenticate):
            for _ in range(server.LOGIN_MAX_FAILURES):
                with self.assertRaises(HTTPException) as failed:
                    await server.login_user(
                        SimpleNamespace(
                            username="  User@Example.Test  ",
                            password="wrong-password",
                        ),
                        Response(),
                        request,
                    )
                self.assertEqual(failed.exception.status_code, 401)

            with self.assertRaises(HTTPException) as blocked:
                await server.login_user(
                    SimpleNamespace(
                        username="user@example.test",
                        password="another-password",
                    ),
                    Response(),
                    request,
                )

        self.assertEqual(blocked.exception.status_code, 429)
        self.assertEqual(
            blocked.exception.detail,
            "Too many failed login attempts. Please try again later.",
        )
        self.assertGreaterEqual(int(blocked.exception.headers["Retry-After"]), 1)
        self.assertEqual(authenticate.await_count, server.LOGIN_MAX_FAILURES)

    async def test_limit_is_scoped_to_both_client_ip_and_email(self):
        first_request = self.request_from("203.0.113.11")
        other_request = self.request_from("203.0.113.12")
        authenticate = AsyncMock(return_value=None)
        form = SimpleNamespace(username="user@example.test", password="wrong")

        with patch.object(server, "authenticate_user", authenticate):
            for _ in range(server.LOGIN_MAX_FAILURES):
                with self.assertRaises(HTTPException):
                    await server.login_user(form, Response(), first_request)

            with self.assertRaises(HTTPException) as other_ip:
                await server.login_user(form, Response(), other_request)
            with self.assertRaises(HTTPException) as other_email:
                await server.login_user(
                    SimpleNamespace(username="other@example.test", password="wrong"),
                    Response(),
                    first_request,
                )

        self.assertEqual(other_ip.exception.status_code, 401)
        self.assertEqual(other_email.exception.status_code, 401)
        self.assertEqual(authenticate.await_count, server.LOGIN_MAX_FAILURES + 2)

    async def test_success_resets_failures_and_request_is_optional(self):
        request = self.request_from("203.0.113.13")
        form = SimpleNamespace(username="user@example.test", password="password")
        authenticate = AsyncMock(return_value=None)

        with patch.object(server, "authenticate_user", authenticate):
            for _ in range(5):
                with self.assertRaises(HTTPException):
                    await server.login_user(form, Response(), request)

            authenticate.return_value = {
                "id": "user-1",
                "email": "user@example.test",
            }
            users = SimpleNamespace(update_one=AsyncMock())
            with (
                patch.object(server, "db", SimpleNamespace(users=users)),
                patch.object(server, "create_access_token", return_value="test-jwt"),
            ):
                token = await server.login_user(form, Response(), request)
            self.assertEqual(token.access_token, "test-jwt")

            authenticate.return_value = None
            for _ in range(6):
                with self.assertRaises(HTTPException) as failed:
                    await server.login_user(form, Response(), request)
                self.assertEqual(failed.exception.status_code, 401)

            # Existing direct callers can continue to omit a Request object.
            with self.assertRaises(HTTPException) as direct_call:
                await server.login_user(
                    SimpleNamespace(username="direct@example.test", password="wrong"),
                    Response(),
                )
            self.assertEqual(direct_call.exception.status_code, 401)

    def test_limiter_expires_failures_and_bounds_tracked_keys(self):
        now = [0.0]
        expiring = server.InProcessLoginFailureLimiter(
            max_failures=2,
            window_seconds=10,
            max_keys=2,
            clock=lambda: now[0],
        )
        key = ("203.0.113.20", "user@example.test")
        expiring.record_failure(key)
        expiring.record_failure(key)
        self.assertEqual(expiring.retry_after(key), 10)

        now[0] = 10.0
        self.assertEqual(expiring.retry_after(key), 0)
        self.assertEqual(len(expiring), 0)

        bounded = server.InProcessLoginFailureLimiter(
            max_failures=2,
            window_seconds=10,
            max_keys=2,
            clock=lambda: 0.0,
        )
        keys = [
            ("203.0.113.21", "one@example.test"),
            ("203.0.113.22", "two@example.test"),
            ("203.0.113.23", "three@example.test"),
        ]
        for tracked_key in keys:
            bounded.record_failure(tracked_key)
            bounded.record_failure(tracked_key)

        self.assertEqual(len(bounded), 2)
        self.assertEqual(bounded.retry_after(keys[0]), 0)
        self.assertEqual(bounded.retry_after(keys[1]), 10)
        self.assertEqual(bounded.retry_after(keys[2]), 10)


if __name__ == "__main__":
    unittest.main()
