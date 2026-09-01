import os
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import dotenv


# Keep the module import detached from local credentials and external services.
os.environ["MONGO_URL"] = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=1"
os.environ["DB_NAME"] = "finance_hacker_auth_exposure_unit_tests"
os.environ["SECRET_KEY"] = "auth-exposure-tests-only"
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


def update_result(*, matched=1, modified=1):
    return SimpleNamespace(matched_count=matched, modified_count=modified)


class HouseholdExposureTests(unittest.IsolatedAsyncioTestCase):
    def test_legacy_users_collection_routes_are_absent(self):
        exposed_methods = {
            (route.path, method)
            for route in server.app.routes
            for method in getattr(route, "methods", set())
        }

        self.assertNotIn(("/api/users", "GET"), exposed_methods)
        self.assertNotIn(("/api/users", "POST"), exposed_methods)

    async def test_invite_creates_pending_record_without_mutating_target_user(self):
        now = datetime(2026, 1, 1)
        households = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "id": "household-1",
                    "name": "Example household",
                    "created_by": "owner-1",
                    "members": ["owner-1"],
                    "created_at": now,
                }
            )
        )
        invitations = SimpleNamespace(
            update_many=AsyncMock(return_value=update_result()),
            insert_one=AsyncMock(),
        )
        users = SimpleNamespace(update_one=AsyncMock())

        with patch.object(
            server,
            "db",
            SimpleNamespace(
                households=households,
                invitations=invitations,
                users=users,
            ),
        ):
            invitation = await server.invite_household_member(
                server.HouseholdInvitationCreate(
                    email="target@example.com",
                    role="user",
                ),
                current_user={
                    "id": "owner-1",
                    "email": "owner@example.com",
                    "household_id": "household-1",
                },
            )

        self.assertEqual(invitation.email, "target@example.com")
        self.assertEqual(invitation.status, "pending")
        self.assertGreater(invitation.expires_at, now + timedelta(days=6))
        users.update_one.assert_not_awaited()
        invitations.insert_one.assert_awaited_once()

    async def test_wrong_authenticated_user_cannot_accept_invitation(self):
        invitations = SimpleNamespace(
            find_one=AsyncMock(return_value=None),
            update_one=AsyncMock(),
            update_many=AsyncMock(),
        )
        households = SimpleNamespace(find_one=AsyncMock(), update_one=AsyncMock())
        users = SimpleNamespace(update_one=AsyncMock())

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(
                    invitations=invitations,
                    households=households,
                    users=users,
                ),
            ),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.accept_household_invitation(
                "invitation-1",
                current_user={
                    "id": "intruder-1",
                    "email": "intruder@example.test",
                    "household_id": None,
                },
            )

        self.assertEqual(raised.exception.status_code, 404)
        lookup = invitations.find_one.await_args.args[0]
        self.assertEqual(lookup["id"], "invitation-1")
        self.assertEqual(lookup["email"], "intruder@example.test")
        self.assertEqual(lookup["status"], "pending")
        households.update_one.assert_not_awaited()
        users.update_one.assert_not_awaited()

    async def test_invited_authenticated_user_can_accept(self):
        now = datetime(2026, 1, 1)
        invitation_doc = {
            "id": "invitation-1",
            "email": "target@example.test",
            "household_id": "household-1",
            "invited_by": "owner-1",
            "role": "user",
            "status": "pending",
            "created_at": now,
            "expires_at": now + timedelta(days=7),
        }
        household_doc = {
            "id": "household-1",
            "name": "Example household",
            "created_by": "owner-1",
            "members": ["owner-1"],
            "created_at": now,
        }
        invitations = SimpleNamespace(
            find_one=AsyncMock(return_value=invitation_doc),
            update_one=AsyncMock(return_value=update_result()),
            update_many=AsyncMock(return_value=update_result()),
        )
        households = SimpleNamespace(
            find_one=AsyncMock(return_value=household_doc),
            update_one=AsyncMock(return_value=update_result()),
        )
        users = SimpleNamespace(update_one=AsyncMock(return_value=update_result()))

        with patch.object(
            server,
            "db",
            SimpleNamespace(
                invitations=invitations,
                households=households,
                users=users,
            ),
        ):
            household = await server.accept_household_invitation(
                "invitation-1",
                current_user={
                    "id": "target-1",
                    "email": "target@example.test",
                    "household_id": None,
                },
            )

        self.assertEqual(household.id, "household-1")
        user_filter, user_update = users.update_one.await_args.args
        self.assertEqual(user_filter["id"], "target-1")
        self.assertIn("$or", user_filter)
        self.assertEqual(user_update["$set"]["household_id"], "household-1")

        accepted_filter, accepted_update = invitations.update_one.await_args.args
        self.assertEqual(
            accepted_filter,
            {"id": "invitation-1", "status": "pending"},
        )
        self.assertEqual(accepted_update["$set"]["status"], "accepted")
        self.assertEqual(accepted_update["$set"]["accepted_by"], "target-1")


if __name__ == "__main__":
    unittest.main()
