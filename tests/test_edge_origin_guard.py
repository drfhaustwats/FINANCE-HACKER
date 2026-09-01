import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import dotenv
import httpx


# Keep server import-time clients detached from local credentials and services.
os.environ["APP_ENV"] = "development"
os.environ["MONGO_URL"] = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=1"
os.environ["DB_NAME"] = "finance_hacker_edge_guard_unit_tests"
os.environ["SECRET_KEY"] = "edge-origin-guard-tests-only-secret-key"
os.environ["EDGE_ORIGIN_SECRET"] = ""
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


class EdgeOriginGuardTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, path, *, headers=None):
        transport = httpx.ASGITransport(app=server.app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(path, headers=headers)

    async def test_development_is_unaffected(self):
        with (
            patch.object(server, "APP_ENV", "development"),
            patch.object(server, "EDGE_ORIGIN_SECRET", "configured-edge-secret"),
        ):
            response = await self.request("/api/")

        self.assertEqual(response.status_code, 200)

    async def test_unconfigured_production_is_unaffected(self):
        with (
            patch.object(server, "APP_ENV", "production"),
            patch.object(server, "EDGE_ORIGIN_SECRET", ""),
        ):
            response = await self.request("/api/")

        self.assertEqual(response.status_code, 200)

    async def test_production_rejects_missing_and_wrong_secret_as_not_found(self):
        with (
            patch.object(server, "APP_ENV", "production"),
            patch.object(server, "EDGE_ORIGIN_SECRET", "configured-edge-secret"),
        ):
            missing = await self.request("/api/")
            wrong = await self.request(
                "/api/",
                headers={"X-Fintrack-Origin-Auth": "wrong-edge-secret"},
            )

        for response in (missing, wrong):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {"detail": "Not Found"})

    async def test_production_accepts_matching_secret(self):
        with (
            patch.object(server, "APP_ENV", "production"),
            patch.object(server, "EDGE_ORIGIN_SECRET", "configured-edge-secret"),
        ):
            response = await self.request(
                "/api/",
                headers={"X-Fintrack-Origin-Auth": "configured-edge-secret"},
            )

        self.assertEqual(response.status_code, 200)

    async def test_health_bypasses_guard(self):
        database = SimpleNamespace(command=AsyncMock(return_value={"ok": 1}))
        with (
            patch.object(server, "APP_ENV", "production"),
            patch.object(server, "EDGE_ORIGIN_SECRET", "configured-edge-secret"),
            patch.object(server, "db", database),
        ):
            response = await self.request("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        database.command.assert_awaited_once_with("ping")


if __name__ == "__main__":
    unittest.main()
