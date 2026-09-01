import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import dotenv


# Keep imports detached from local credentials and external services.
os.environ["MONGO_URL"] = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=1"
os.environ["DB_NAME"] = "finance_hacker_release_guard_unit_tests"
os.environ["SECRET_KEY"] = "release-guard-tests-only"
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


class RegistrationPolicyTests(unittest.IsolatedAsyncioTestCase):
    def test_registration_defaults_open_locally_and_closed_in_production(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(server.resolve_public_registration_enabled())
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            self.assertFalse(server.resolve_public_registration_enabled())
        with patch.dict(os.environ, {"RAILWAY_PROJECT_ID": "project-1"}, clear=True):
            self.assertFalse(server.resolve_public_registration_enabled())
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "PUBLIC_REGISTRATION_ENABLED": "true"},
            clear=True,
        ):
            self.assertTrue(server.resolve_public_registration_enabled())

    async def test_closed_registration_rejects_uninvited_email_before_user_lookup(self):
        invitations = SimpleNamespace(find_one=AsyncMock(return_value=None))
        users = SimpleNamespace(find_one=AsyncMock(), insert_one=AsyncMock())
        with (
            patch.object(server, "PUBLIC_REGISTRATION_ENABLED", False),
            patch.object(
                server,
                "db",
                SimpleNamespace(invitations=invitations, users=users),
            ),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.register_user(
                server.UserCreate(
                    email="Uninvited@Example.com",
                    password="test-password",
                    full_name="Uninvited User",
                )
            )

        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(raised.exception.detail, "Registration is currently invitation only.")
        lookup = invitations.find_one.await_args.args[0]
        self.assertEqual(lookup["email"], "uninvited@example.com")
        users.find_one.assert_not_awaited()
        users.insert_one.assert_not_awaited()

    async def test_valid_pending_invitation_allows_normalized_registration(self):
        invitations = SimpleNamespace(
            find_one=AsyncMock(return_value={"household_id": "household-1"})
        )
        households = SimpleNamespace(find_one=AsyncMock(return_value={"_id": "exists"}))
        users = SimpleNamespace(
            find_one=AsyncMock(return_value=None),
            insert_one=AsyncMock(),
        )
        with (
            patch.object(server, "PUBLIC_REGISTRATION_ENABLED", False),
            patch.object(
                server,
                "db",
                SimpleNamespace(
                    invitations=invitations,
                    households=households,
                    users=users,
                ),
            ),
            patch.object(server, "get_password_hash", return_value="password-hash"),
        ):
            user = await server.register_user(
                server.UserCreate(
                    email="Invited@Example.com",
                    password="test-password",
                    full_name="Invited User",
                )
            )

        self.assertEqual(user.email, "invited@example.com")
        inserted = users.insert_one.await_args.args[0]
        self.assertEqual(inserted["email"], "invited@example.com")
        self.assertEqual(inserted["username"], "invited")
        invitation_lookup = invitations.find_one.await_args.args[0]
        self.assertEqual(invitation_lookup["email"], "invited@example.com")
        self.assertEqual(invitation_lookup["status"], "pending")
        self.assertIn("$gt", invitation_lookup["expires_at"])

    async def test_google_new_user_is_blocked_without_invitation(self):
        google = SimpleNamespace(
            authorize_access_token=AsyncMock(
                return_value={
                    "userinfo": {
                        "email": "New.Google@Example.test",
                        "email_verified": True,
                        "name": "New Google User",
                    }
                }
            )
        )
        oauth_client = MagicMock()
        oauth_client.register.return_value = google
        invitations = SimpleNamespace(find_one=AsyncMock(return_value=None))
        users = SimpleNamespace(find_one=AsyncMock(), insert_one=AsyncMock())

        with (
            patch.object(server, "PUBLIC_REGISTRATION_ENABLED", False),
            patch.object(server, "google_oauth_ready", return_value=True),
            patch.object(server, "OAuth", return_value=oauth_client),
            patch.object(server, "get_user_by_email", AsyncMock(return_value=None)),
            patch.object(
                server,
                "db",
                SimpleNamespace(invitations=invitations, users=users),
            ),
            patch.object(server, "create_google_oauth_login_code", new_callable=AsyncMock) as code,
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.google_callback(SimpleNamespace())

        self.assertEqual(raised.exception.status_code, 403)
        users.insert_one.assert_not_awaited()
        code.assert_not_awaited()


class AiRequestGuardTests(unittest.IsolatedAsyncioTestCase):
    def test_guard_limits_concurrency_and_rate_without_identifier_leakage(self):
        now = [100.0]
        guard = server.InProcessAiRequestGuard(
            requests_per_window=2,
            window_seconds=60,
            max_concurrent_per_user=1,
            clock=lambda: now[0],
        )
        private_user_id = "private-user-id-123"

        first = guard.acquire(private_user_id)
        with self.assertRaises(server.HTTPException) as concurrent:
            guard.acquire(private_user_id)
        self.assertEqual(concurrent.exception.status_code, 429)
        self.assertNotIn(private_user_id, concurrent.exception.detail)
        self.assertEqual(concurrent.exception.headers["Retry-After"], "5")

        other_user = guard.acquire("other-user")
        other_user.release()
        first.release()
        second = guard.acquire(private_user_id)
        second.release()

        with self.assertRaises(server.HTTPException) as rate_limited:
            guard.acquire(private_user_id)
        self.assertEqual(rate_limited.exception.status_code, 429)
        self.assertNotIn(private_user_id, rate_limited.exception.detail)
        self.assertEqual(rate_limited.exception.headers["Retry-After"], "60")

        now[0] += 61
        guard.acquire(private_user_id).release()

    async def test_dependency_holds_and_releases_lease(self):
        guard = server.InProcessAiRequestGuard(
            requests_per_window=5,
            window_seconds=60,
            max_concurrent_per_user=1,
        )
        with patch.object(server, "AI_REQUEST_GUARD", guard):
            dependency = server.enforce_paid_ai_request_limits(
                current_user={"id": "user-1"}
            )
            await dependency.__anext__()
            with self.assertRaises(server.HTTPException) as raised:
                guard.acquire("user-1")
            self.assertEqual(raised.exception.status_code, 429)
            await dependency.aclose()
            guard.acquire("user-1").release()

    def test_all_paid_or_blocking_ai_routes_use_guard_dependency(self):
        expected_paths = {
            "/api/ai/insights/generate",
            "/api/ai/insights/month/{month_key}/generate",
            "/api/ai/detect-subscriptions",
            "/api/ai/recategorize",
            "/api/ai/insight-detail",
            "/api/ai/resolve-category",
            "/api/ai/search",
        }
        checked = set()
        for route in server.app.routes:
            if getattr(route, "path", None) not in expected_paths:
                continue
            dependency_calls = {
                dependency.call
                for dependency in getattr(route, "dependant").dependencies
            }
            self.assertIn(server.enforce_paid_ai_request_limits, dependency_calls)
            checked.add(route.path)
        self.assertEqual(checked, expected_paths)
        subscription_scan_routes = [
            route
            for route in server.app.routes
            if getattr(route, "path", None) == "/api/ai/detect-subscriptions"
        ]
        self.assertEqual(len(subscription_scan_routes), 1)
        self.assertIn("POST", subscription_scan_routes[0].methods)
        self.assertNotIn("GET", subscription_scan_routes[0].methods)


if __name__ == "__main__":
    unittest.main()
