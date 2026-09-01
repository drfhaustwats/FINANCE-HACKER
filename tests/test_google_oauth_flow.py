import hashlib
import os
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import dotenv


# Keep server import-time clients detached from local credentials and services.
os.environ["MONGO_URL"] = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=1"
os.environ["DB_NAME"] = "finance_hacker_google_oauth_unit_tests"
os.environ["SECRET_KEY"] = "google-oauth-tests-only"
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


class GoogleOAuthLoginCodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_creation_persists_only_hash_with_two_minute_expiry(self):
        raw_code = "test-only-oauth-code-with-enough-entropy-123456789"
        oauth_login_codes = SimpleNamespace(insert_one=AsyncMock())

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(oauth_login_codes=oauth_login_codes),
            ),
            patch.object(server.secrets, "token_urlsafe", return_value=raw_code),
        ):
            returned_code = await server.create_google_oauth_login_code("user-1")

        self.assertEqual(returned_code, raw_code)
        stored = oauth_login_codes.insert_one.await_args.args[0]
        self.assertEqual(
            stored["code_hash"],
            hashlib.sha256(raw_code.encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("code", stored)
        self.assertNotIn(raw_code, repr(stored))
        self.assertIsNone(stored["used_at"])
        self.assertEqual(
            stored["expires_at"] - stored["created_at"],
            timedelta(seconds=120),
        )

    async def test_exchange_atomically_consumes_code_once_and_binds_user(self):
        raw_code = "single-use-google-oauth-code-1234567890abcdef"
        login_code = {
            "code_hash": server.hash_google_oauth_login_code(raw_code),
            "user_id": "user-1",
        }
        oauth_login_codes = SimpleNamespace(
            find_one_and_update=AsyncMock(side_effect=[login_code, None])
        )
        users = SimpleNamespace(
            find_one=AsyncMock(return_value={"id": "user-1", "email": "user@example.test"})
        )

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(oauth_login_codes=oauth_login_codes, users=users),
            ),
            patch.object(server, "create_access_token", return_value="issued-jwt") as issue_jwt,
        ):
            token = await server.exchange_google_oauth_login_code(
                server.GoogleOAuthCodeExchangeRequest(code=raw_code)
            )
            with self.assertRaises(server.HTTPException) as reused:
                await server.exchange_google_oauth_login_code(
                    server.GoogleOAuthCodeExchangeRequest(code=raw_code)
                )

        self.assertEqual(token.access_token, "issued-jwt")
        self.assertEqual(token.token_type, "bearer")
        self.assertEqual(reused.exception.status_code, 400)
        issue_jwt.assert_called_once()
        users.find_one.assert_awaited_once_with({"id": "user-1"})

        lookup, update = oauth_login_codes.find_one_and_update.await_args_list[0].args
        self.assertEqual(lookup["code_hash"], hashlib.sha256(raw_code.encode()).hexdigest())
        self.assertIsNone(lookup["used_at"])
        self.assertIn("$gt", lookup["expires_at"])
        self.assertIn("used_at", update["$set"])
        self.assertEqual(
            oauth_login_codes.find_one_and_update.await_args_list[0].kwargs["return_document"],
            server.ReturnDocument.BEFORE,
        )
        self.assertNotIn(raw_code, repr(oauth_login_codes.find_one_and_update.await_args_list))

    async def test_invalid_code_is_rejected_before_database_lookup(self):
        oauth_login_codes = SimpleNamespace(find_one_and_update=AsyncMock())
        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(oauth_login_codes=oauth_login_codes),
            ),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.exchange_google_oauth_login_code(
                server.GoogleOAuthCodeExchangeRequest(code="too-short")
            )

        self.assertEqual(raised.exception.status_code, 400)
        oauth_login_codes.find_one_and_update.assert_not_awaited()

    def test_redirect_places_code_in_fragment_not_query(self):
        raw_code = "fragment-only-google-code-1234567890abcdef"
        redirect_url = server.build_google_oauth_frontend_redirect(
            "https://fintrack.example.test/", raw_code
        )

        parsed = urlsplit(redirect_url)
        self.assertEqual(parsed.query, "")
        self.assertEqual(parse_qs(parsed.fragment), {"oauth_code": [raw_code]})

    async def test_callback_redirects_with_one_time_code_and_never_creates_jwt(self):
        raw_code = "callback-google-code-1234567890abcdef"
        existing_user = {
            "id": "user-1",
            "email": "user@example.test",
            "username": "user",
            "full_name": "Example User",
        }
        google = SimpleNamespace(
            authorize_access_token=AsyncMock(
                return_value={
                    "userinfo": {
                        "email": existing_user["email"],
                        "email_verified": True,
                        "name": existing_user["full_name"],
                    }
                }
            )
        )
        oauth_client = MagicMock()
        oauth_client.register.return_value = google
        users = SimpleNamespace(update_one=AsyncMock())

        with (
            patch.object(server, "google_oauth_ready", return_value=True),
            patch.object(server, "OAuth", return_value=oauth_client),
            patch.object(server, "get_user_by_email", AsyncMock(return_value=existing_user)),
            patch.object(server, "db", SimpleNamespace(users=users)),
            patch.object(
                server,
                "create_google_oauth_login_code",
                AsyncMock(return_value=raw_code),
            ) as create_login_code,
            patch.object(server, "create_access_token") as create_jwt,
            patch.object(
                server,
                "FRONTEND_URL",
                "https://fintrack.example.test",
            ),
        ):
            response = await server.google_callback(SimpleNamespace())

        location = response.headers["location"]
        parsed = urlsplit(location)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "fintrack.example.test")
        self.assertEqual(parsed.query, "")
        self.assertEqual(parse_qs(parsed.fragment), {"oauth_code": [raw_code]})
        create_login_code.assert_awaited_once_with("user-1")
        create_jwt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
