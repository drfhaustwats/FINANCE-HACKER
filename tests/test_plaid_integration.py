import base64
import hashlib
import json
import os
import unittest
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


TEST_FERNET_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="


# server.py initializes its clients at import time. Force inert, test-only settings
# before importing it so this suite never reads local credentials or connects to a
# real MongoDB/Plaid environment.
os.environ["MONGO_URL"] = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=1"
os.environ["DB_NAME"] = "finance_hacker_unit_tests"
os.environ["SECRET_KEY"] = "plaid-tests-only"
os.environ["PLAID_CLIENT_ID"] = ""
os.environ["PLAID_SECRET"] = ""
os.environ["PLAID_ENV"] = "sandbox"
os.environ["PLAID_PRODUCTS"] = "transactions"
os.environ["PLAID_COUNTRY_CODES"] = "CA"
os.environ["PLAID_REDIRECT_URI"] = ""
os.environ["PLAID_WEBHOOK_URL"] = ""
os.environ["PLAID_TOKEN_ENCRYPTION_KEY"] = TEST_FERNET_KEY
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""
os.environ["GMAIL_EMAIL"] = ""
os.environ["GMAIL_APP_PASSWORD"] = ""

_real_load_dotenv = dotenv.load_dotenv
try:
    dotenv.load_dotenv = lambda *args, **kwargs: False
    from backend import server  # noqa: E402
finally:
    dotenv.load_dotenv = _real_load_dotenv


def plaid_transaction(**overrides):
    values = {
        "transaction_id": "tx-1",
        "date": date(2026, 8, 30),
        "amount": 42.75,
        "merchant_name": "  Example   Market  ",
        "name": "EXAMPLE MARKET 123",
        "account_id": "account-1",
        "personal_finance_category": SimpleNamespace(
            primary="GENERAL_MERCHANDISE",
            detailed="GENERAL_MERCHANDISE_GROCERIES",
        ),
        "pending_transaction_id": None,
        "pending": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def plaid_account(**overrides):
    values = {
        "account_id": "account-1",
        "name": "Everyday",
        "official_name": "Everyday Chequing",
        "mask": "1234",
        "type": "depository",
        "subtype": "checking",
        "balances": SimpleNamespace(
            iso_currency_code="CAD",
            unofficial_currency_code=None,
        ),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakePlaidRequest:
    def __init__(self, **values):
        self.values = values


class FakePlaidApiException(Exception):
    def __init__(self, message, error_code="INTERNAL_SERVER_ERROR"):
        super().__init__(message)
        self.body = json.dumps(
            {
                "error_type": "API_ERROR",
                "error_code": error_code,
                "error_message": message,
            }
        )


class FakeBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, function, *args, **kwargs):
        self.tasks.append((function, args, kwargs))


class FakeWebhookRequest:
    def __init__(self, chunks, headers=None, client_host="127.0.0.1"):
        self.chunks = list(chunks)
        self.headers = headers or {}
        self.client = SimpleNamespace(host=client_host) if client_host else None
        self.stream_started = False

    async def stream(self):
        self.stream_started = True
        for chunk in self.chunks:
            yield chunk


class FakeAsyncCursor:
    def __init__(self, documents):
        self.documents = list(documents)
        self.sort_args = None

    def sort(self, *args):
        self.sort_args = args
        return self

    async def to_list(self, _limit):
        return list(self.documents)


class PlaidHelperTests(unittest.TestCase):
    def test_parse_plaid_error_prefers_structured_details(self):
        error = RuntimeError("opaque SDK error")
        error.body = json.dumps(
            {
                "error_type": "ITEM_ERROR",
                "error_code": "ITEM_LOGIN_REQUIRED",
                "error_message": "The login needs attention.",
            }
        )

        message, code = server.parse_plaid_error(error)

        self.assertEqual(message, "ITEM_ERROR: The login needs attention.")
        self.assertEqual(code, "ITEM_LOGIN_REQUIRED")

    def test_parse_plaid_error_falls_back_for_non_json_body(self):
        error = RuntimeError("plain SDK error")
        error.body = "not-json"

        message, code = server.parse_plaid_error(error)

        self.assertEqual(message, "plain SDK error")
        self.assertIsNone(code)

    def test_serialize_connection_removes_credentials_and_sync_lease(self):
        created_at = datetime(2026, 8, 30, 12, 5, tzinfo=timezone.utc)
        serialized = server.serialize_connection_document(
            {
                "_id": "mongo-id",
                "id": "connection-1",
                "access_token": "access-sandbox-secret",
                "access_token_ciphertext": "encrypted-secret",
                "sync_lease_id": "private-lease-id",
                "sync_lease_until": created_at,
                "accounts": [{"account_id": "one"}, {"account_id": "two"}],
                "created_at": created_at,
                "updated_at": None,
            }
        )

        self.assertNotIn("_id", serialized)
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("access_token_ciphertext", serialized)
        self.assertNotIn("sync_lease_id", serialized)
        self.assertNotIn("sync_lease_until", serialized)
        self.assertEqual(serialized["created_at"], created_at.isoformat())
        self.assertEqual(serialized["account_count"], 2)

    def test_category_mapping_prefers_detailed_plaid_category(self):
        self.assertEqual(
            server.map_plaid_category_hint(
                "GENERAL_MERCHANDISE",
                "FOOD_AND_DRINK_GROCERIES",
                "Neighbourhood Market",
            ),
            "Retail and Grocery",
        )
        self.assertEqual(
            server.map_plaid_category_hint("INCOME", "INCOME_WAGES", "Payroll"),
            "Income and Payroll",
        )
        self.assertEqual(
            server.map_plaid_category_hint(
                "TRANSPORTATION",
                "TRANSPORTATION_TAXIS_AND_RIDE_SHARES",
                "ANTHROPIC *CLAUDE.AI SUBSCRIPTION",
            ),
            "Professional and Financial Services",
        )
        self.assertEqual(
            server.map_plaid_category_hint(
                "TRANSFER_OUT",
                "TRANSFER_OUT_ACCOUNT_TRANSFER",
                "ANTHROPIC E-TRANSFER",
            ),
            "Transfers and Payments",
        )
        self.assertIsNone(server.map_plaid_category_hint("UNKNOWN", "UNKNOWN_OTHER", "Merchant"))

    def test_account_mapping_and_transfer_taxonomy_does_not_imply_ownership(self):
        self.assertEqual(server.map_plaid_account_type("credit", "credit card"), "credit_card")
        self.assertEqual(server.map_plaid_account_type("depository", "checking"), "debit")
        self.assertEqual(
            server.map_plaid_account_type(
                SimpleNamespace(value="credit"),
                SimpleNamespace(value="credit card"),
            ),
            "credit_card",
        )
        self.assertIsNone(
            server.infer_plaid_internal_transfer_flag(
                "TRANSFER_OUT",
                "TRANSFER_OUT_ACCOUNT_TRANSFER",
            )
        )
        self.assertIsNone(
            server.infer_plaid_internal_transfer_flag(
                "TRANSFER_IN",
                "TRANSFER_IN_ACCOUNT_TRANSFER",
            )
        )
        self.assertIsNone(
            server.infer_plaid_internal_transfer_flag("TRANSFER_OUT", "TRANSFER_OUT_OTHER")
        )

    def test_source_and_account_snapshot_have_stable_fallbacks(self):
        self.assertEqual(
            server.build_plaid_source_name(None, None),
            "Plaid - Connected Bank - Account",
        )
        snapshot = server.build_account_snapshot(plaid_account())
        self.assertEqual(snapshot["account_id"], "account-1")
        self.assertEqual(snapshot["mask"], "1234")
        self.assertEqual(snapshot["iso_currency_code"], "CAD")
        self.assertIsNone(snapshot["unofficial_currency_code"])
        self.assertNotIn("balances", snapshot)

        wrapped_snapshot = server.build_account_snapshot(SimpleNamespace(
            account_id="account-2",
            name="Wrapped Account",
            official_name=None,
            mask="4321",
            type=SimpleNamespace(value="depository"),
            subtype=SimpleNamespace(value="checking"),
        ))
        self.assertEqual(wrapped_snapshot["type"], "depository")
        self.assertEqual(wrapped_snapshot["subtype"], "checking")


class AuthCapabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_auth_capabilities_report_only_configured_feature_flags(self):
        with (
            patch.object(server, "GOOGLE_CLIENT_ID", "google-client-id"),
            patch.object(server, "GOOGLE_CLIENT_SECRET", "google-client-secret"),
            patch.object(server, "GMAIL_EMAIL", "sender@example.test"),
            patch.object(server, "GMAIL_APP_PASSWORD", "smtp-app-password"),
            patch.dict(os.environ, {"FRONTEND_URL": "https://app.example.test"}),
        ):
            enabled = await server.get_auth_capabilities()

        self.assertEqual(
            enabled,
            {
                "google_oauth_enabled": True,
                "password_reset_email_enabled": True,
                "public_registration_enabled": True,
            },
        )
        self.assertEqual(
            set(enabled),
            {
                "google_oauth_enabled",
                "password_reset_email_enabled",
                "public_registration_enabled",
            },
        )

        with (
            patch.object(server, "GOOGLE_CLIENT_ID", ""),
            patch.object(server, "GOOGLE_CLIENT_SECRET", ""),
            patch.object(server, "GMAIL_EMAIL", ""),
            patch.object(server, "GMAIL_APP_PASSWORD", ""),
            patch.dict(os.environ, {"FRONTEND_URL": ""}),
        ):
            disabled = await server.get_auth_capabilities()

        self.assertEqual(
            disabled,
            {
                "google_oauth_enabled": False,
                "password_reset_email_enabled": False,
                "public_registration_enabled": True,
            },
        )

    async def test_forgot_password_returns_503_before_user_lookup_when_smtp_is_unconfigured(self):
        get_user = AsyncMock()
        password_resets = SimpleNamespace(
            delete_many=AsyncMock(),
            insert_one=AsyncMock(),
        )
        send_email = AsyncMock()

        with (
            patch.object(server, "GMAIL_EMAIL", ""),
            patch.object(server, "GMAIL_APP_PASSWORD", ""),
            patch.object(server, "get_user_by_email", get_user),
            patch.object(
                server,
                "db",
                SimpleNamespace(password_resets=password_resets),
            ),
            patch.object(server, "send_email", send_email),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.forgot_password(
                server.PasswordResetRequest(email="akolaifa4@gmail.com")
            )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("not configured", raised.exception.detail)
        get_user.assert_not_awaited()
        password_resets.delete_many.assert_not_awaited()
        password_resets.insert_one.assert_not_awaited()
        send_email.assert_not_awaited()


class PlaidTokenSecurityTests(unittest.IsolatedAsyncioTestCase):
    def test_access_token_round_trip_uses_static_test_key(self):
        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("access-sandbox-test-token")
            plaintext = server.decrypt_plaid_access_token(ciphertext)

        self.assertNotEqual(ciphertext, "access-sandbox-test-token")
        self.assertNotIn("access-sandbox-test-token", ciphertext)
        self.assertEqual(plaintext, "access-sandbox-test-token")

    def test_invalid_ciphertext_is_rejected_without_disclosing_it(self):
        with (
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
            self.assertRaises(server.HTTPException) as raised,
        ):
            server.decrypt_plaid_access_token("not-a-fernet-token")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertNotIn("not-a-fernet-token", str(raised.exception.detail))

    async def test_legacy_plaintext_token_is_migrated_on_first_use(self):
        plaid_items = SimpleNamespace(update_one=AsyncMock())
        item_doc = {
            "id": "connection-1",
            "user_id": "user-1",
            "item_id": "item-1",
            "access_token": "legacy-plaintext-token",
        }

        with (
            patch.object(server, "db", SimpleNamespace(plaid_items=plaid_items)),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
        ):
            token = await server.load_plaid_access_token(item_doc)

        self.assertEqual(token, "legacy-plaintext-token")
        plaid_items.update_one.assert_awaited_once()
        update_filter, operation = plaid_items.update_one.await_args.args
        self.assertEqual(
            update_filter,
            {
                "id": "connection-1",
                "user_id": "user-1",
                "access_token": "legacy-plaintext-token",
            },
        )
        self.assertEqual(operation["$unset"], {"access_token": ""})
        ciphertext = operation["$set"]["access_token_ciphertext"]
        self.assertEqual(server.decrypt_plaid_access_token(ciphertext), "legacy-plaintext-token")
        self.assertNotIn("access_token", item_doc)
        self.assertEqual(item_doc["access_token_ciphertext"], ciphertext)

    async def test_encrypted_token_load_does_not_write_to_database(self):
        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("already-encrypted-token")
        plaid_items = SimpleNamespace(update_one=AsyncMock())

        with (
            patch.object(server, "db", SimpleNamespace(plaid_items=plaid_items)),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
        ):
            token = await server.load_plaid_access_token(
                {
                    "id": "connection-1",
                    "user_id": "user-1",
                    "access_token_ciphertext": ciphertext,
                }
            )

        self.assertEqual(token, "already-encrypted-token")
        plaid_items.update_one.assert_not_awaited()


class PlaidTransactionTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_plaid_transaction_is_updated_and_keeps_user_flags(self):
        transactions = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "id": "local-1",
                    "category": "Old Category",
                    "is_internal_transfer": False,
                    "is_internal_transfer_source": "user",
                    "is_inflow": True,
                }
            ),
            update_one=AsyncMock(),
            insert_one=AsyncMock(),
        )
        fake_db = SimpleNamespace(transactions=transactions)
        category_resolver = AsyncMock(return_value="Retail and Grocery")
        history = defaultdict(Counter)

        with (
            patch.object(server, "db", fake_db),
            patch.object(server, "resolve_transaction_category", category_resolver),
        ):
            result = await server.upsert_plaid_transaction_record(
                user_id="user-1",
                user_name="Test User",
                item_id="item-1",
                institution_name="Test Bank",
                plaid_transaction=plaid_transaction(),
                accounts_by_id={"account-1": plaid_account()},
                category_names=["Retail and Grocery"],
                merchant_history=history,
            )

        self.assertEqual(result, "modified")
        transactions.insert_one.assert_not_awaited()
        update_filter, update_operation = transactions.update_one.await_args.args
        self.assertEqual(update_filter, {"id": "local-1", "user_id": "user-1"})
        update_doc = update_operation["$set"]
        self.assertEqual(update_doc["description"], "Example Market")
        self.assertEqual(update_doc["date"], "2026-08-30")
        self.assertEqual(update_doc["account_type"], "debit")
        self.assertEqual(update_doc["source_type"], "plaid")
        self.assertFalse(update_doc["is_internal_transfer"])
        self.assertEqual(update_doc["is_internal_transfer_source"], "user")
        self.assertTrue(update_doc["is_inflow"])
        category_resolver.assert_awaited_once()

    async def test_legacy_provider_internal_flag_is_preserved_for_review(self):
        transactions = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "id": "local-1",
                    "plaid_transaction_id": "tx-1",
                    "is_internal_transfer": True,
                    "plaid_personal_finance_detailed": "TRANSFER_OUT_ACCOUNT_TRANSFER",
                }
            ),
            update_one=AsyncMock(),
            insert_one=AsyncMock(),
        )

        with (
            patch.object(server, "db", SimpleNamespace(transactions=transactions)),
            patch.object(
                server,
                "resolve_transaction_category",
                AsyncMock(return_value="Transfers and Payments"),
            ),
        ):
            result = await server.upsert_plaid_transaction_record(
                user_id="user-1",
                user_name="Test User",
                item_id="item-1",
                institution_name="Test Bank",
                plaid_transaction=plaid_transaction(
                    personal_finance_category=SimpleNamespace(
                        primary="TRANSFER_OUT",
                        detailed="TRANSFER_OUT_ACCOUNT_TRANSFER",
                    ),
                ),
                accounts_by_id={"account-1": plaid_account()},
                category_names=[],
                merchant_history=defaultdict(Counter),
            )

        self.assertEqual(result, "modified")
        update_doc = transactions.update_one.await_args.args[1]["$set"]
        self.assertTrue(update_doc["is_internal_transfer"])
        self.assertEqual(
            update_doc["is_internal_transfer_source"],
            "legacy_unverified",
        )

    async def test_plaid_refresh_preserves_user_category_and_description(self):
        transactions = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "id": "local-1",
                    "description": "My preferred merchant name",
                    "description_source": "user",
                    "merchant_signature": "preferred merchant",
                    "category": "My Custom Category",
                    "category_source": "user",
                }
            ),
            update_one=AsyncMock(),
            insert_one=AsyncMock(),
        )

        with (
            patch.object(server, "db", SimpleNamespace(transactions=transactions)),
            patch.object(
                server,
                "resolve_transaction_category",
                AsyncMock(return_value="Retail and Grocery"),
            ),
        ):
            result = await server.upsert_plaid_transaction_record(
                user_id="user-1",
                user_name="Test User",
                item_id="item-1",
                institution_name="Test Bank",
                plaid_transaction=plaid_transaction(
                    merchant_name="PLAID NORMALIZED MERCHANT",
                ),
                accounts_by_id={"account-1": plaid_account()},
                category_names=["Retail and Grocery", "My Custom Category"],
                merchant_history=defaultdict(Counter),
            )

        self.assertEqual(result, "modified")
        update_doc = transactions.update_one.await_args.args[1]["$set"]
        self.assertEqual(update_doc["description"], "My preferred merchant name")
        self.assertEqual(update_doc["description_source"], "user")
        self.assertEqual(update_doc["merchant_signature"], "preferred merchant")
        self.assertEqual(update_doc["category"], "My Custom Category")
        self.assertEqual(update_doc["category_source"], "user")

    async def test_pdf_shape_match_is_merged_without_overwriting_user_category(self):
        transactions = SimpleNamespace(
            find_one=AsyncMock(
                side_effect=[
                    None,
                    {
                        "id": "pdf-local-1",
                        "category": "User Corrected Category",
                        "is_internal_transfer": True,
                        "is_inflow": False,
                    },
                ]
            ),
            update_one=AsyncMock(),
            insert_one=AsyncMock(),
        )
        fake_db = SimpleNamespace(transactions=transactions)

        with (
            patch.object(server, "db", fake_db),
            patch.object(
                server,
                "resolve_transaction_category",
                AsyncMock(return_value="Retail and Grocery"),
            ),
        ):
            result = await server.upsert_plaid_transaction_record(
                user_id="user-1",
                user_name="Test User",
                item_id="item-1",
                institution_name="Test Bank",
                plaid_transaction=plaid_transaction(),
                accounts_by_id={"account-1": plaid_account()},
                category_names=[],
                merchant_history=defaultdict(Counter),
            )

        self.assertEqual(result, "merged")
        transactions.insert_one.assert_not_awaited()
        shape_query = transactions.find_one.await_args_list[1].args[0]
        self.assertEqual(shape_query["user_id"], "user-1")
        self.assertEqual(shape_query["date"], "2026-08-30")
        update_doc = transactions.update_one.await_args.args[1]["$set"]
        self.assertEqual(update_doc["category"], "User Corrected Category")
        self.assertTrue(update_doc["is_internal_transfer"])
        self.assertFalse(update_doc["is_inflow"])

    async def test_new_transaction_is_inserted_with_provider_metadata(self):
        transactions = SimpleNamespace(
            find_one=AsyncMock(side_effect=[None, None]),
            update_one=AsyncMock(),
            insert_one=AsyncMock(),
        )
        fake_db = SimpleNamespace(transactions=transactions)

        with (
            patch.object(server, "db", fake_db),
            patch.object(
                server,
                "resolve_transaction_category",
                AsyncMock(return_value="Retail and Grocery"),
            ),
        ):
            result = await server.upsert_plaid_transaction_record(
                user_id="user-1",
                user_name="Test User",
                item_id="item-1",
                institution_name="Test Bank",
                plaid_transaction=plaid_transaction(pending=True),
                accounts_by_id={"account-1": plaid_account()},
                category_names=[],
                merchant_history=defaultdict(Counter),
            )

        self.assertEqual(result, "added")
        inserted = transactions.insert_one.await_args.args[0]
        self.assertEqual(inserted["plaid_transaction_id"], "tx-1")
        self.assertEqual(inserted["plaid_item_id"], "item-1")
        self.assertEqual(inserted["source_provider"], "plaid")
        self.assertEqual(inserted["pdf_source"], "Plaid - Test Bank - Everyday Chequing")
        self.assertTrue(inserted["plaid_pending"])
        self.assertIn("id", inserted)
        self.assertIn("created_at", inserted)

    async def test_posted_transaction_reuses_pending_row_and_user_overrides(self):
        transactions = SimpleNamespace(
            find_one=AsyncMock(
                side_effect=[
                    None,
                    {
                        "id": "local-pending-row",
                        "plaid_transaction_id": "pending-tx",
                        "plaid_pending": True,
                        "category": "User Category",
                        "category_source": "user",
                        "is_internal_transfer": False,
                        "is_internal_transfer_source": "user",
                        "analytics_class_override": "expense",
                        "analytics_class_override_source": "user",
                    },
                ]
            ),
            update_one=AsyncMock(),
            insert_one=AsyncMock(),
        )
        posted = plaid_transaction(
            transaction_id="posted-tx",
            pending=False,
            pending_transaction_id="pending-tx",
        )

        with (
            patch.object(server, "db", SimpleNamespace(transactions=transactions)),
            patch.object(
                server,
                "resolve_transaction_category",
                AsyncMock(return_value="Retail and Grocery"),
            ),
        ):
            result = await server.upsert_plaid_transaction_record(
                user_id="user-1",
                user_name="Test User",
                item_id="item-1",
                institution_name="Test Bank",
                plaid_transaction=posted,
                accounts_by_id={"account-1": plaid_account()},
                category_names=[],
                merchant_history=defaultdict(Counter),
            )

        self.assertEqual(result, "modified")
        transactions.insert_one.assert_not_awaited()
        update_filter, update_operation = transactions.update_one.await_args.args
        self.assertEqual(
            update_filter,
            {"id": "local-pending-row", "user_id": "user-1"},
        )
        update_doc = update_operation["$set"]
        self.assertEqual(update_doc["plaid_transaction_id"], "posted-tx")
        self.assertEqual(update_doc["plaid_pending_transaction_id"], "pending-tx")
        self.assertFalse(update_doc["plaid_pending"])
        self.assertEqual(update_doc["category"], "User Category")
        self.assertFalse(update_doc["is_internal_transfer"])
        # The classifier override is intentionally absent from $set, so Mongo
        # preserves the existing proven user value on the reused row.
        self.assertNotIn("analytics_class_override", update_doc)

    async def test_existing_posted_row_removes_coexisting_pending_duplicate(self):
        transactions = SimpleNamespace(
            find_one=AsyncMock(
                side_effect=[
                    {
                        "id": "posted-row",
                        "plaid_transaction_id": "posted-tx",
                        "description": "Provider posted description",
                        "description_source": "plaid_sync",
                        "category": "Provider Category",
                        "category_source": "plaid_sync",
                        "classification_scope_overrides": {
                            "household:household-one": {
                                "internal_transfer": True,
                                "internal_transfer_source": "user",
                            },
                        },
                    },
                    {
                        "id": "pending-row",
                        "plaid_transaction_id": "pending-tx",
                        "plaid_pending": True,
                        "description": "User corrected description",
                        "description_source": "user",
                        "merchant_signature": "user corrected description",
                        "category": "User Category",
                        "category_source": "user",
                        "is_internal_transfer": False,
                        "is_internal_transfer_source": "user",
                        "analytics_class_override": "expense",
                        "analytics_class_override_source": "user",
                        "is_inflow": False,
                        "classification_scope_overrides": {
                            "user:user-1": {
                                "internal_transfer": False,
                                "internal_transfer_source": "user",
                            },
                        },
                    },
                ]
            ),
            update_one=AsyncMock(),
            delete_many=AsyncMock(),
            insert_one=AsyncMock(),
        )
        posted = plaid_transaction(
            transaction_id="posted-tx",
            pending=False,
            pending_transaction_id="pending-tx",
        )

        with (
            patch.object(server, "db", SimpleNamespace(transactions=transactions)),
            patch.object(
                server,
                "resolve_transaction_category",
                AsyncMock(return_value="Retail and Grocery"),
            ),
        ):
            result = await server.upsert_plaid_transaction_record(
                user_id="user-1",
                user_name="Test User",
                item_id="item-1",
                institution_name="Test Bank",
                plaid_transaction=posted,
                accounts_by_id={"account-1": plaid_account()},
                category_names=[],
                merchant_history=defaultdict(Counter),
            )

        self.assertEqual(result, "modified")
        transactions.insert_one.assert_not_awaited()
        update_filter, update_operation = transactions.update_one.await_args.args
        self.assertEqual(
            update_filter,
            {"id": "posted-row", "user_id": "user-1"},
        )
        update_doc = update_operation["$set"]
        self.assertEqual(update_doc["plaid_transaction_id"], "posted-tx")
        self.assertFalse(update_doc["plaid_pending"])
        self.assertEqual(update_doc["description"], "User corrected description")
        self.assertEqual(update_doc["description_source"], "user")
        self.assertEqual(update_doc["category"], "User Category")
        self.assertEqual(update_doc["category_source"], "user")
        self.assertFalse(update_doc["is_internal_transfer"])
        self.assertEqual(update_doc["is_internal_transfer_source"], "user")
        self.assertEqual(update_doc["analytics_class_override"], "expense")
        self.assertEqual(update_doc["analytics_class_override_source"], "user")
        self.assertFalse(update_doc["is_inflow"])
        self.assertEqual(
            update_doc["classification_scope_overrides"],
            {
                "user:user-1": {
                    "internal_transfer": False,
                    "internal_transfer_source": "user",
                },
                "household:household-one": {
                    "internal_transfer": True,
                    "internal_transfer_source": "user",
                },
            },
        )
        transactions.delete_many.assert_awaited_once_with({
            "id": "pending-row",
            "user_id": "user-1",
            "plaid_pending": True,
        })

    async def test_new_account_transfer_is_not_marked_internal_from_plaid_taxonomy(self):
        transactions = SimpleNamespace(
            find_one=AsyncMock(side_effect=[None, None]),
            update_one=AsyncMock(),
            insert_one=AsyncMock(),
        )
        account_transfer = plaid_transaction(
            merchant_name=None,
            name="E-TRANSFER external counterparty",
            personal_finance_category=SimpleNamespace(
                primary="TRANSFER_OUT",
                detailed="TRANSFER_OUT_ACCOUNT_TRANSFER",
            ),
        )

        with (
            patch.object(server, "db", SimpleNamespace(transactions=transactions)),
            patch.object(
                server,
                "resolve_transaction_category",
                AsyncMock(return_value="Transfers and Payments"),
            ),
        ):
            result = await server.upsert_plaid_transaction_record(
                user_id="user-1",
                user_name="Test User",
                item_id="item-1",
                institution_name="Test Bank",
                plaid_transaction=account_transfer,
                accounts_by_id={"account-1": plaid_account()},
                category_names=[],
                merchant_history=defaultdict(Counter),
            )

        self.assertEqual(result, "added")
        inserted = transactions.insert_one.await_args.args[0]
        self.assertIsNone(inserted["is_internal_transfer"])

    async def test_missing_transaction_identity_is_skipped_without_database_access(self):
        transactions = SimpleNamespace(
            find_one=AsyncMock(),
            update_one=AsyncMock(),
            insert_one=AsyncMock(),
        )

        with patch.object(server, "db", SimpleNamespace(transactions=transactions)):
            result = await server.upsert_plaid_transaction_record(
                user_id="user-1",
                user_name=None,
                item_id="item-1",
                institution_name=None,
                plaid_transaction=plaid_transaction(transaction_id=None),
                accounts_by_id={},
                category_names=[],
                merchant_history=defaultdict(Counter),
            )

        self.assertEqual(result, "skipped")
        transactions.find_one.assert_not_awaited()
        transactions.insert_one.assert_not_awaited()


class PlaidSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_decrypts_token_renews_lease_and_saves_cursor(self):
        page_one = SimpleNamespace(
            added=[plaid_transaction(transaction_id="added-1")],
            modified=[],
            removed=[],
            next_cursor="cursor-page-1",
            has_more=True,
        )
        page_two = SimpleNamespace(
            added=[],
            modified=[plaid_transaction(transaction_id="modified-1")],
            removed=[SimpleNamespace(transaction_id="removed-1")],
            next_cursor="cursor-final",
            has_more=False,
        )
        call_plaid_mock = AsyncMock(side_effect=[page_one, page_two])
        upsert_mock = AsyncMock(side_effect=["added", "modified"])
        transactions = SimpleNamespace(
            delete_many=AsyncMock(return_value=SimpleNamespace(deleted_count=1))
        )
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "status": "active",
                    "revoked_account_ids": [],
                    "sync_policy_generation": 4,
                }
            ),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1))
        )
        fake_db = SimpleNamespace(transactions=transactions, plaid_items=plaid_items)

        class FakeSyncRequest:
            def __init__(self, **values):
                self.values = values

        account = plaid_account()
        item = SimpleNamespace(institution_id="institution-1", institution_name=None)
        fake_client = SimpleNamespace(transactions_sync=object())
        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("fake-access-token")

        with (
            patch.object(server, "db", fake_db),
            patch.object(server, "require_plaid_client", return_value=fake_client),
            patch.object(
                server,
                "fetch_plaid_accounts_for_item",
                AsyncMock(return_value=([account], item)),
            ),
            patch.object(
                server,
                "resolve_plaid_institution_name",
                AsyncMock(return_value="Test Bank"),
            ),
            patch.object(server, "TransactionsSyncRequest", FakeSyncRequest),
            patch.object(server, "call_plaid", call_plaid_mock),
            patch.object(
                server,
                "load_user_category_context",
                AsyncMock(return_value=(["Retail and Grocery"], defaultdict(Counter))),
            ),
            patch.object(server, "upsert_plaid_transaction_record", upsert_mock),
        ):
            summary = await server.sync_single_plaid_item(
                {
                    "id": "connection-1",
                    "item_id": "item-1",
                    "access_token_ciphertext": ciphertext,
                    "cursor": "cursor-start",
                    "institution_id": "institution-1",
                    "sync_policy_generation": 4,
                },
                user_id="user-1",
                user_name="Test User",
                lease_id="lease-1",
            )

        requests = [call.args[1] for call in call_plaid_mock.await_args_list]
        self.assertTrue(all(request.values["access_token"] == "fake-access-token" for request in requests))
        self.assertEqual(requests[0].values["cursor"], "cursor-start")
        self.assertEqual(requests[1].values["cursor"], "cursor-page-1")
        self.assertEqual(summary["added_count"], 1)
        self.assertEqual(summary["modified_count"], 1)
        self.assertEqual(summary["removed_count"], 1)
        self.assertEqual(summary["next_cursor"], "cursor-final")
        transactions.delete_many.assert_awaited_once_with(
            {"user_id": "user-1", "plaid_transaction_id": "removed-1"}
        )
        # One renewal follows each Plaid page and each local mutation is bracketed
        # by renewals so a slow database operation cannot silently outlive its lease.
        self.assertEqual(plaid_items.update_one.await_count, 9)
        for renewal in plaid_items.update_one.await_args_list[:-1]:
            self.assertEqual(
                renewal.args[0],
                {"id": "connection-1", "user_id": "user-1", "sync_lease_id": "lease-1"},
            )
            self.assertIn("sync_lease_until", renewal.args[1]["$set"])
        final_filter, saved_update = plaid_items.update_one.await_args.args
        self.assertEqual(final_filter["sync_lease_id"], "lease-1")
        self.assertEqual(final_filter["sync_policy_generation"], 4)
        self.assertEqual(
            final_filter["status"],
            {
                "$nin": [
                    "permission_revoked",
                    "disconnected",
                    "disconnecting",
                    "disconnecting_cleanup",
                    "disconnect_cleanup_required",
                ]
            },
        )
        self.assertEqual(saved_update["$set"]["cursor"], "cursor-final")
        self.assertEqual(saved_update["$set"]["status"], "active")
        self.assertEqual(saved_update["$unset"], {"last_error": "", "last_error_at": ""})

    async def test_reauthorized_account_is_processed_before_cursor_is_saved(self):
        account_reauthorized = plaid_account(account_id="account-1")
        account_active = plaid_account(
            account_id="account-3",
            name="Savings",
            official_name="Savings",
            mask="9876",
        )
        reauthorized_transaction = plaid_transaction(
            transaction_id="reauthorized-tx",
            account_id="account-1",
        )
        still_revoked_transaction = plaid_transaction(
            transaction_id="revoked-tx",
            account_id="account-2",
        )
        sync_page = SimpleNamespace(
            added=[reauthorized_transaction, still_revoked_transaction],
            modified=[],
            removed=[],
            next_cursor="cursor-after-reauthorization",
            has_more=False,
        )
        operation_order = []

        async def record_item_update(_query, operation):
            if "cursor" in operation.get("$set", {}):
                operation_order.append("cursor_saved")
            return SimpleNamespace(matched_count=1)

        async def record_upsert(**kwargs):
            operation_order.append(
                f"upsert:{kwargs['plaid_transaction'].transaction_id}"
            )
            return "added"

        plaid_items = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "status": "update_required",
                    "revoked_account_ids": ["account-1", "account-2"],
                    "update_completion_pending": True,
                    "sync_policy_generation": 2,
                }
            ),
            update_one=AsyncMock(side_effect=record_item_update),
        )
        transactions = SimpleNamespace(
            delete_many=AsyncMock(return_value=SimpleNamespace(deleted_count=0))
        )
        fake_db = SimpleNamespace(plaid_items=plaid_items, transactions=transactions)
        upsert_mock = AsyncMock(side_effect=record_upsert)
        fake_client = SimpleNamespace(transactions_sync=object())
        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("fake-access-token")

        with (
            patch.object(server, "db", fake_db),
            patch.object(server, "require_plaid_client", return_value=fake_client),
            patch.object(
                server,
                "fetch_plaid_accounts_for_item",
                AsyncMock(
                    return_value=(
                        [account_reauthorized, account_active],
                        SimpleNamespace(institution_id="institution-1", institution_name=None),
                    )
                ),
            ),
            patch.object(
                server,
                "resolve_plaid_institution_name",
                AsyncMock(return_value="Test Bank"),
            ),
            patch.object(server, "TransactionsSyncRequest", FakePlaidRequest),
            patch.object(server, "call_plaid", AsyncMock(return_value=sync_page)),
            patch.object(
                server,
                "load_user_category_context",
                AsyncMock(return_value=([], defaultdict(Counter))),
            ),
            patch.object(server, "upsert_plaid_transaction_record", upsert_mock),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
        ):
            summary = await server.sync_single_plaid_item(
                {
                    "id": "connection-1",
                    "item_id": "item-1",
                    "status": "update_required",
                    "update_completion_pending": True,
                    "revoked_account_ids": ["account-1", "account-2"],
                    "access_token_ciphertext": ciphertext,
                    "cursor": "cursor-before-reauthorization",
                    "sync_policy_generation": 2,
                },
                user_id="user-1",
                user_name="Test User",
                lease_id="lease-1",
            )

        self.assertEqual(upsert_mock.await_count, 1)
        self.assertIs(
            upsert_mock.await_args.kwargs["plaid_transaction"],
            reauthorized_transaction,
        )
        self.assertEqual(summary["added_count"], 1)
        self.assertEqual(summary["next_cursor"], "cursor-after-reauthorization")
        final_operation = plaid_items.update_one.await_args.args[1]
        self.assertEqual(
            final_operation["$pullAll"],
            {"revoked_account_ids": ["account-1"]},
        )
        self.assertEqual(
            [account["account_id"] for account in final_operation["$set"]["accounts"]],
            ["account-1", "account-3"],
        )
        self.assertLess(
            operation_order.index("upsert:reauthorized-tx"),
            operation_order.index("cursor_saved"),
        )

    async def test_policy_generation_change_before_writes_aborts_without_advancing_cursor(self):
        sync_page = SimpleNamespace(
            added=[plaid_transaction(transaction_id="must-not-write")],
            modified=[],
            removed=[SimpleNamespace(transaction_id="must-not-delete")],
            next_cursor="cursor-uncommitted",
            has_more=False,
        )
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "status": "update_required",
                    "revoked_account_ids": ["account-1"],
                    "sync_policy_generation": 8,
                }
            ),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        )
        transactions = SimpleNamespace(delete_many=AsyncMock())
        upsert = AsyncMock()
        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("fake-access-token")

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(plaid_items=plaid_items, transactions=transactions),
            ),
            patch.object(
                server,
                "require_plaid_client",
                return_value=SimpleNamespace(transactions_sync=object()),
            ),
            patch.object(
                server,
                "fetch_plaid_accounts_for_item",
                AsyncMock(
                    return_value=(
                        [plaid_account()],
                        SimpleNamespace(institution_id="institution-1", institution_name=None),
                    )
                ),
            ),
            patch.object(
                server,
                "resolve_plaid_institution_name",
                AsyncMock(return_value="Test Bank"),
            ),
            patch.object(server, "TransactionsSyncRequest", FakePlaidRequest),
            patch.object(server, "call_plaid", AsyncMock(return_value=sync_page)),
            patch.object(server, "upsert_plaid_transaction_record", upsert),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
            self.assertRaises(server.PlaidSyncPolicyChanged),
        ):
            await server.sync_single_plaid_item(
                {
                    "id": "connection-1",
                    "item_id": "item-1",
                    "access_token_ciphertext": ciphertext,
                    "cursor": "cursor-committed",
                    "sync_policy_generation": 7,
                },
                user_id="user-1",
                user_name="Test User",
                lease_id="lease-1",
            )

        transactions.delete_many.assert_not_awaited()
        upsert.assert_not_awaited()
        self.assertTrue(
            all(
                "cursor" not in call.args[1].get("$set", {})
                for call in plaid_items.update_one.await_args_list
            )
        )

    async def test_policy_generation_change_is_reloaded_and_rerun_under_same_lease(self):
        initial_item = {
            "id": "connection-1",
            "item_id": "item-1",
            "user_id": "user-1",
            "status": "active",
            "cursor": "cursor-committed",
            "sync_policy_generation": 7,
        }
        refreshed_item = {
            **initial_item,
            "sync_lease_id": "lease-fixed",
            "sync_policy_generation": 8,
        }
        plaid_items = SimpleNamespace(
            update_one=AsyncMock(
                side_effect=[
                    SimpleNamespace(matched_count=1),
                    SimpleNamespace(matched_count=1),
                ]
            ),
            find_one_and_update=AsyncMock(
                side_effect=[
                    {**initial_item, "sync_lease_id": "lease-fixed"},
                    refreshed_item,
                    None,
                ]
            ),
            find_one=AsyncMock(),
        )
        sync_item = AsyncMock(
            side_effect=[
                server.PlaidSyncPolicyChanged(),
                {
                    "item_id": "item-1",
                    "accounts_synced": 1,
                    "added_count": 1,
                    "modified_count": 0,
                    "merged_count": 0,
                    "removed_count": 0,
                    "next_cursor": "cursor-after-rerun",
                },
            ]
        )

        with (
            patch.object(server, "db", SimpleNamespace(plaid_items=plaid_items)),
            patch.object(server.uuid, "uuid4", return_value="lease-fixed"),
            patch.object(server, "sync_single_plaid_item", sync_item),
        ):
            summary = await server.request_plaid_item_sync(
                initial_item,
                user_id="user-1",
                user_name="Test User",
            )

        self.assertEqual(sync_item.await_count, 2)
        self.assertEqual(sync_item.await_args_list[0].args[0]["sync_policy_generation"], 7)
        self.assertEqual(sync_item.await_args_list[1].args[0]["sync_policy_generation"], 8)
        self.assertEqual(
            [call.kwargs["lease_id"] for call in sync_item.await_args_list],
            ["lease-fixed", "lease-fixed"],
        )
        self.assertEqual(summary["next_cursor"], "cursor-after-rerun")
        self.assertEqual(summary["added_count"], 1)

    async def test_generation_change_at_final_cursor_cas_requests_a_rerun(self):
        sync_page = SimpleNamespace(
            added=[],
            modified=[],
            removed=[],
            next_cursor="cursor-uncommitted",
            has_more=False,
        )
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(
                side_effect=[
                    {
                        "status": "active",
                        "revoked_account_ids": [],
                        "sync_policy_generation": 7,
                    },
                    {"sync_lease_id": "lease-1", "sync_policy_generation": 8},
                ]
            ),
            update_one=AsyncMock(
                side_effect=[
                    SimpleNamespace(matched_count=1),
                    SimpleNamespace(matched_count=0),
                ]
            ),
        )
        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("fake-access-token")

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(
                    plaid_items=plaid_items,
                    transactions=SimpleNamespace(delete_many=AsyncMock()),
                ),
            ),
            patch.object(
                server,
                "require_plaid_client",
                return_value=SimpleNamespace(transactions_sync=object()),
            ),
            patch.object(
                server,
                "fetch_plaid_accounts_for_item",
                AsyncMock(
                    return_value=(
                        [plaid_account()],
                        SimpleNamespace(institution_id="institution-1", institution_name=None),
                    )
                ),
            ),
            patch.object(
                server,
                "resolve_plaid_institution_name",
                AsyncMock(return_value="Test Bank"),
            ),
            patch.object(server, "TransactionsSyncRequest", FakePlaidRequest),
            patch.object(server, "call_plaid", AsyncMock(return_value=sync_page)),
            patch.object(
                server,
                "load_user_category_context",
                AsyncMock(return_value=([], defaultdict(Counter))),
            ),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
            self.assertRaises(server.PlaidSyncPolicyChanged),
        ):
            await server.sync_single_plaid_item(
                {
                    "id": "connection-1",
                    "item_id": "item-1",
                    "access_token_ciphertext": ciphertext,
                    "cursor": "cursor-committed",
                    "sync_policy_generation": 7,
                },
                user_id="user-1",
                user_name="Test User",
                lease_id="lease-1",
            )

        final_filter, final_operation = plaid_items.update_one.await_args_list[-1].args
        self.assertEqual(final_filter["sync_policy_generation"], 7)
        self.assertEqual(final_operation["$set"]["cursor"], "cursor-uncommitted")
        self.assertEqual(
            plaid_items.find_one.await_args_list[-1].args,
            (
                {"id": "connection-1", "user_id": "user-1"},
                {"sync_lease_id": 1, "sync_policy_generation": 1},
            ),
        )


class PlaidWebhookVerificationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_es256_p256_jwt_and_jwk_round_trip(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_numbers = private_key.public_key().public_numbers()

        def base64url_coordinate(value):
            return base64.urlsafe_b64encode(value.to_bytes(32, "big")).rstrip(b"=").decode("ascii")

        jwk = {
            "kid": "generated-test-key",
            "alg": "ES256",
            "kty": "EC",
            "crv": "P-256",
            "use": "sig",
            "x": base64url_coordinate(public_numbers.x),
            "y": base64url_coordinate(public_numbers.y),
        }
        raw_body = b'{"webhook_type":"ITEM","webhook_code":"LOGIN_REPAIRED"}'
        issued_at = 1_700_000_000
        expected_claims = {
            "iat": issued_at,
            "request_body_sha256": hashlib.sha256(raw_body).hexdigest(),
        }
        signed_jwt = server.jwt.encode(
            expected_claims,
            private_pem,
            algorithm="ES256",
            headers={"kid": "generated-test-key"},
        )
        key_lookup = AsyncMock(return_value=jwk)

        with patch.object(server, "get_plaid_webhook_key", key_lookup):
            verified_claims = await server.verify_plaid_webhook(
                raw_body,
                signed_jwt,
                now=issued_at + 1,
            )

        self.assertEqual(verified_claims["iat"], issued_at)
        self.assertEqual(
            verified_claims["request_body_sha256"],
            expected_claims["request_body_sha256"],
        )
        key_lookup.assert_awaited_once_with("generated-test-key")

    async def test_webhook_verification_uses_exact_raw_body_digest(self):
        raw_body = b'{"webhook_type":"TRANSACTIONS","item_id":"item-1"}'
        public_key = {"kid": "key-1", "kty": "EC", "crv": "P-256"}
        claims = {
            "iat": 1_000,
            "request_body_sha256": hashlib.sha256(raw_body).hexdigest(),
        }
        get_key = AsyncMock(return_value=public_key)

        with (
            patch.object(
                server.jwt,
                "get_unverified_header",
                return_value={"kid": "key-1", "alg": "ES256"},
            ),
            patch.object(server.jwt, "decode", return_value=claims) as decode,
            patch.object(server, "get_plaid_webhook_key", get_key),
        ):
            verified = await server.verify_plaid_webhook(
                raw_body,
                "signed-webhook-jwt",
                now=1_001,
            )

        self.assertEqual(verified, claims)
        get_key.assert_awaited_once_with("key-1")
        decode.assert_called_once_with(
            "signed-webhook-jwt",
            public_key,
            algorithms=["ES256"],
            options={"verify_aud": False},
        )

    async def test_webhook_verification_rejects_a_changed_raw_body(self):
        signed_body = b'{"item_id":"item-1"}'
        received_body = b'{"item_id":"item-2"}'
        claims = {
            "iat": 1_000,
            "request_body_sha256": hashlib.sha256(signed_body).hexdigest(),
        }

        with (
            patch.object(
                server.jwt,
                "get_unverified_header",
                return_value={"kid": "key-1", "alg": "ES256"},
            ),
            patch.object(server.jwt, "decode", return_value=claims),
            patch.object(server, "get_plaid_webhook_key", AsyncMock(return_value={"kid": "key-1"})),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.verify_plaid_webhook(
                received_body,
                "signed-webhook-jwt",
                now=1_001,
            )

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.detail, "Plaid webhook body verification failed.")


class PlaidWebhookEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_webhook_deduplicates_and_persists_only_sanitized_fields(self):
        payload = {
            "webhook_type": "TRANSACTIONS",
            "webhook_code": "SYNC_UPDATES_AVAILABLE",
            "item_id": "item-1",
            "environment": "sandbox",
            "new_transactions": 2,
            "access_token": "must-never-be-persisted",
            "customer_name": "Private Person",
            "error": {
                "error_type": "ITEM_ERROR",
                "error_code": "ITEM_LOGIN_REQUIRED",
                "display_message": "Sensitive institution message",
            },
        }
        raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = FakeWebhookRequest([raw_body])
        background_tasks = FakeBackgroundTasks()
        webhook_events = SimpleNamespace(
            update_one=AsyncMock(
                side_effect=[
                    SimpleNamespace(upserted_id="inserted-event"),
                    SimpleNamespace(upserted_id=None),
                ]
            )
        )
        verifier = AsyncMock(return_value={"verified": True})

        with (
            patch.object(server, "db", SimpleNamespace(plaid_webhook_events=webhook_events)),
            patch.object(server, "verify_plaid_webhook", verifier),
            patch.object(server, "enforce_plaid_webhook_rate_limit"),
            patch.object(server, "PLAID_ENV", "sandbox"),
        ):
            first = await server.receive_plaid_webhook(
                request,
                background_tasks,
                plaid_verification="signed-jwt",
            )
            duplicate = await server.receive_plaid_webhook(
                request,
                background_tasks,
                plaid_verification="signed-jwt",
            )

        self.assertEqual(first, {"received": True, "duplicate": False, "queued": True})
        self.assertEqual(duplicate, {"received": True, "duplicate": True, "queued": True})
        self.assertEqual(verifier.await_count, 2)
        for verification_call in verifier.await_args_list:
            self.assertEqual(verification_call.args, (raw_body, "signed-jwt"))

        expected_delivery_id = hashlib.sha256(b"signed-jwt\0" + raw_body).hexdigest()
        for database_call in webhook_events.update_one.await_args_list:
            query, operation = database_call.args[:2]
            self.assertEqual(query, {"delivery_id": expected_delivery_id})
            self.assertTrue(database_call.kwargs["upsert"])
            persisted = operation["$setOnInsert"]
            self.assertEqual(persisted["delivery_id"], expected_delivery_id)
            self.assertEqual(persisted["safe_payload"]["item_id"], "item-1")
            persisted_json = json.dumps(persisted, default=str)
            self.assertNotIn("must-never-be-persisted", persisted_json)
            self.assertNotIn("Private Person", persisted_json)
            self.assertNotIn("Sensitive institution message", persisted_json)
            self.assertEqual(
                persisted["safe_payload"]["error"],
                {"error_type": "ITEM_ERROR", "error_code": "ITEM_LOGIN_REQUIRED"},
            )
        self.assertGreaterEqual(len(background_tasks.tasks), 1)
        self.assertIs(background_tasks.tasks[0][0], server.process_plaid_webhook_delivery)
        self.assertEqual(background_tasks.tasks[0][1], (expected_delivery_id,))

    async def test_declared_oversized_webhook_is_rejected_before_streaming(self):
        request = FakeWebhookRequest(
            [b"this chunk must never be read"],
            headers={"content-length": str(server.PLAID_WEBHOOK_MAX_BODY_BYTES + 1)},
        )
        verifier = AsyncMock()

        with (
            patch.object(server, "enforce_plaid_webhook_rate_limit"),
            patch.object(server, "verify_plaid_webhook", verifier),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.receive_plaid_webhook(
                request,
                FakeBackgroundTasks(),
                plaid_verification="signed-jwt",
            )

        self.assertEqual(raised.exception.status_code, 413)
        self.assertFalse(request.stream_started)
        verifier.assert_not_awaited()

    async def test_chunked_webhook_is_stopped_at_streaming_hard_cap(self):
        request = FakeWebhookRequest(
            [b"a" * server.PLAID_WEBHOOK_MAX_BODY_BYTES, b"b"],
        )
        verifier = AsyncMock()

        with (
            patch.object(server, "enforce_plaid_webhook_rate_limit"),
            patch.object(server, "verify_plaid_webhook", verifier),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.receive_plaid_webhook(
                request,
                FakeBackgroundTasks(),
                plaid_verification="signed-jwt",
            )

        self.assertEqual(raised.exception.status_code, 413)
        self.assertTrue(request.stream_started)
        verifier.assert_not_awaited()


class PlaidWebhookInboxTests(unittest.IsolatedAsyncioTestCase):
    async def test_drain_recovers_an_expired_processing_lease(self):
        cursor = FakeAsyncCursor([{"delivery_id": "expired-processing-delivery"}])
        find_calls = []

        def find_events(query, projection):
            find_calls.append((query, projection))
            return cursor

        webhook_events = SimpleNamespace(find=find_events)
        processor = AsyncMock()

        with (
            patch.object(server, "db", SimpleNamespace(plaid_webhook_events=webhook_events)),
            patch.object(server, "process_plaid_webhook_delivery", processor),
        ):
            await server.drain_plaid_webhook_inbox()

        self.assertEqual(len(find_calls), 1)
        query, projection = find_calls[0]
        processing_branch = next(
            branch
            for branch in query["$or"]
            if branch.get("status") == "processing"
        )
        self.assertIn("$lte", processing_branch["processing_lease_until"])
        self.assertEqual(projection, {"delivery_id": 1})
        self.assertEqual(cursor.sort_args, ("received_at", 1))
        processor.assert_awaited_once_with("expired-processing-delivery")

    async def test_missing_item_waits_before_retry(self):
        event_doc = {
            "delivery_id": "missing-item-delivery",
            "attempts": 2,
            "safe_payload": {
                "webhook_type": "TRANSACTIONS",
                "webhook_code": "SYNC_UPDATES_AVAILABLE",
                "item_id": "not-connected-yet",
            },
        }
        webhook_events = SimpleNamespace(
            find_one_and_update=AsyncMock(return_value=event_doc),
            update_one=AsyncMock(),
        )
        plaid_items = SimpleNamespace(find_one=AsyncMock(return_value=None))

        with patch.object(
            server,
            "db",
            SimpleNamespace(
                plaid_webhook_events=webhook_events,
                plaid_items=plaid_items,
            ),
        ):
            await server.process_plaid_webhook_delivery("missing-item-delivery")

        operation = webhook_events.update_one.await_args.args[1]
        self.assertEqual(operation["$set"]["status"], "awaiting_item")
        self.assertIn("next_attempt_at", operation["$set"])
        self.assertNotIn("expires_at", operation["$set"])
        self.assertEqual(
            operation["$unset"],
            {"processing_lease_id": "", "processing_lease_until": ""},
        )

    async def test_missing_item_is_dead_lettered_after_attempt_limit(self):
        event_doc = {
            "delivery_id": "missing-item-delivery",
            "attempts": 8,
            "safe_payload": {
                "webhook_type": "TRANSACTIONS",
                "webhook_code": "SYNC_UPDATES_AVAILABLE",
                "item_id": "never-connected",
            },
        }
        webhook_events = SimpleNamespace(
            find_one_and_update=AsyncMock(return_value=event_doc),
            update_one=AsyncMock(),
        )
        plaid_items = SimpleNamespace(find_one=AsyncMock(return_value=None))

        with patch.object(
            server,
            "db",
            SimpleNamespace(
                plaid_webhook_events=webhook_events,
                plaid_items=plaid_items,
            ),
        ):
            await server.process_plaid_webhook_delivery("missing-item-delivery")

        operation = webhook_events.update_one.await_args.args[1]
        self.assertEqual(operation["$set"]["status"], "dead_letter")
        self.assertIn("expires_at", operation["$set"])
        self.assertNotIn("next_attempt_at", operation["$set"])
        self.assertEqual(
            operation["$unset"],
            {"processing_lease_id": "", "processing_lease_until": ""},
        )


class PlaidWebhookStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_permission_revoked_state_is_terminal(self):
        plaid_items = SimpleNamespace(update_one=AsyncMock())
        terminal_item = {
            "id": "connection-1",
            "user_id": "user-1",
            "status": "permission_revoked",
        }

        with patch.object(server, "db", SimpleNamespace(plaid_items=plaid_items)):
            needs_sync = await server.apply_plaid_item_webhook_state(
                terminal_item,
                {"webhook_type": "ITEM", "webhook_code": "LOGIN_REPAIRED"},
            )

        self.assertFalse(needs_sync)
        plaid_items.update_one.assert_not_awaited()

    async def test_permission_revocation_clears_pending_sync_and_lease(self):
        plaid_items = SimpleNamespace(update_one=AsyncMock())
        transactions = SimpleNamespace(
            delete_many=AsyncMock(return_value=SimpleNamespace(deleted_count=2))
        )

        with patch.object(
            server,
            "db",
            SimpleNamespace(plaid_items=plaid_items, transactions=transactions),
        ):
            needs_sync = await server.apply_plaid_item_webhook_state(
                {
                    "id": "connection-1",
                    "item_id": "item-1",
                    "user_id": "user-1",
                    "status": "active",
                },
                {"webhook_type": "ITEM", "webhook_code": "USER_PERMISSION_REVOKED"},
        )

        self.assertFalse(needs_sync)
        self.assertEqual(plaid_items.update_one.await_count, 2)
        update_filter, operation = plaid_items.update_one.await_args_list[0].args
        self.assertEqual(update_filter, {"id": "connection-1"})
        self.assertEqual(operation["$set"]["status"], "permission_revoked")
        self.assertFalse(operation["$set"]["sync_pending"])
        self.assertEqual(operation["$set"]["accounts"], [])
        transactions.delete_many.assert_awaited_once_with(
            {"user_id": "user-1", "plaid_item_id": "item-1"}
        )
        self.assertEqual(
            operation["$unset"],
            {
                "access_token": "",
                "access_token_ciphertext": "",
                "cursor": "",
                "update_completion_pending": "",
                "update_mode_required": "",
                "update_reason": "",
                "new_accounts_available": "",
                "consent_expiration_time": "",
                "sync_lease_id": "",
                "sync_lease_until": "",
                "sync_started_at": "",
                "recurring_candidates_cache": "",
                "recurring_fetch_lease_id": "",
                "recurring_fetch_lease_until": "",
                "recurring_fetch_policy_hash": "",
                "recurring_fetch_retry_after": "",
            },
        )
        cleanup_filter, cleanup_operation = plaid_items.update_one.await_args_list[1].args
        self.assertEqual(
            cleanup_filter,
            {"id": "connection-1", "status": "permission_revoked"},
        )
        self.assertIn("revoked_data_deleted_at", cleanup_operation["$set"])

    async def test_terminal_item_delivery_is_processed_without_resync(self):
        event_doc = {
            "delivery_id": "delivery-1",
            "safe_payload": {
                "webhook_type": "ITEM",
                "webhook_code": "LOGIN_REPAIRED",
                "item_id": "item-1",
            },
        }
        webhook_events = SimpleNamespace(
            find_one_and_update=AsyncMock(return_value=event_doc),
            update_one=AsyncMock(),
        )
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(
                return_value={
                    "id": "connection-1",
                    "item_id": "item-1",
                    "user_id": "user-1",
                    "status": "permission_revoked",
                }
            ),
            update_one=AsyncMock(),
        )
        users = SimpleNamespace(find_one=AsyncMock())
        sync_request = AsyncMock()

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(
                    plaid_webhook_events=webhook_events,
                    plaid_items=plaid_items,
                    users=users,
                ),
            ),
            patch.object(server, "request_plaid_item_sync", sync_request),
        ):
            await server.process_plaid_webhook_delivery("delivery-1")

        sync_request.assert_not_awaited()
        users.find_one.assert_not_awaited()
        plaid_items.update_one.assert_not_awaited()
        terminal_update = webhook_events.update_one.await_args.args[1]
        self.assertEqual(terminal_update["$set"]["status"], "processed")
        self.assertEqual(terminal_update["$set"]["result"], {"action": "state_updated"})


class PlaidEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_reports_configuration_without_exposing_secrets(self):
        with (
            patch.object(server, "PLAID_SDK_AVAILABLE", True),
            patch.object(server, "plaid_client", object()),
            patch.object(server, "PLAID_CLIENT_ID", "client-id"),
            patch.object(server, "PLAID_SECRET", "secret"),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
            patch.object(server, "PLAID_WEBHOOK_URL", "https://api.example/plaid/webhook"),
            patch.object(server, "PLAID_ENV", "sandbox"),
            patch.object(server, "PLAID_PRODUCTS", ["transactions"]),
            patch.object(server, "PLAID_COUNTRY_CODES", ["CA"]),
        ):
            response = await server.get_plaid_status(current_user={"id": "user-1"})

        self.assertEqual(
            response,
            {
                "enabled": True,
                "sdk_available": True,
                "configured": True,
                "token_encryption_configured": True,
                "webhook_configured": True,
                "recurring_transactions_enabled": False,
                "environment": "sandbox",
                "products": ["transactions"],
                "country_codes": ["CA"],
            },
        )
        self.assertNotIn("client_id", response)
        self.assertNotIn("secret", response)

    async def test_status_reports_missing_security_configuration_as_booleans(self):
        with (
            patch.object(server, "PLAID_SDK_AVAILABLE", True),
            patch.object(server, "plaid_client", None),
            patch.object(server, "PLAID_CLIENT_ID", ""),
            patch.object(server, "PLAID_SECRET", ""),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", ""),
            patch.object(server, "PLAID_WEBHOOK_URL", None),
        ):
            response = await server.get_plaid_status(current_user={"id": "user-1"})

        self.assertIs(response["enabled"], False)
        self.assertIs(response["configured"], False)
        self.assertIs(response["token_encryption_configured"], False)
        self.assertIs(response["webhook_configured"], False)

    async def test_link_token_request_contains_user_and_configured_webhook(self):
        class FakeRequest:
            def __init__(self, **values):
                self.values = values

        class FakeUser:
            def __init__(self, client_user_id):
                self.client_user_id = client_user_id

        fake_client = SimpleNamespace(link_token_create=object())
        response = SimpleNamespace(
            link_token="link-sandbox-test",
            expiration=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc),
            request_id="request-1",
        )
        plaid_call = AsyncMock(return_value=response)

        with (
            patch.object(server, "require_plaid_client", return_value=fake_client),
            patch.object(server, "Products", lambda value: value),
            patch.object(server, "CountryCode", lambda value: f"country:{value}"),
            patch.object(server, "LinkTokenCreateRequest", FakeRequest),
            patch.object(server, "LinkTokenTransactions", FakePlaidRequest),
            patch.object(server, "LinkTokenCreateRequestUser", FakeUser),
            patch.object(server, "call_plaid", plaid_call),
            patch.object(server, "PLAID_PRODUCTS", ["transactions"]),
            patch.object(server, "PLAID_COUNTRY_CODES", ["CA"]),
            patch.object(server, "PLAID_CLIENT_NAME", "LifeTracker Test"),
            patch.object(server, "PLAID_TRANSACTION_DAYS_REQUESTED", 730),
            patch.object(server, "PLAID_REDIRECT_URI", "https://app.example/callback"),
            patch.object(server, "PLAID_WEBHOOK_URL", "https://api.example/plaid/webhook"),
        ):
            result = await server.create_plaid_link_token(
                current_user={"id": "user-1"}
            )

        request = plaid_call.await_args.args[1]
        self.assertEqual(request.values["products"], ["transactions"])
        self.assertEqual(request.values["transactions"].values["days_requested"], 730)
        self.assertEqual(request.values["country_codes"], ["country:CA"])
        self.assertEqual(request.values["user"].client_user_id, "user-1")
        self.assertEqual(request.values["webhook"], "https://api.example/plaid/webhook")
        self.assertEqual(request.values["redirect_uri"], "https://app.example/callback")
        self.assertEqual(result["link_token"], "link-sandbox-test")
        self.assertEqual(result["request_id"], "request-1")

    async def test_update_mode_link_token_uses_access_token_and_omits_products(self):
        class FakeUser:
            def __init__(self, client_user_id):
                self.client_user_id = client_user_id

        class FakeUpdate:
            def __init__(self, account_selection_enabled):
                self.account_selection_enabled = account_selection_enabled

        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("fake-access-token")
        item_doc = {
            "id": "connection-1",
            "user_id": "user-1",
            "item_id": "item-1",
            "access_token_ciphertext": ciphertext,
            "new_accounts_available": True,
        }
        plaid_items = SimpleNamespace(find_one=AsyncMock(return_value=item_doc))
        fake_client = SimpleNamespace(link_token_create=object())
        plaid_call = AsyncMock(
            return_value=SimpleNamespace(
                link_token="update-link-token",
                expiration=None,
                request_id="update-request-1",
            )
        )

        with (
            patch.object(server, "db", SimpleNamespace(plaid_items=plaid_items)),
            patch.object(server, "require_plaid_client", return_value=fake_client),
            patch.object(server, "CountryCode", lambda value: f"country:{value}"),
            patch.object(server, "LinkTokenCreateRequest", FakePlaidRequest),
            patch.object(server, "LinkTokenCreateRequestUser", FakeUser),
            patch.object(server, "LinkTokenCreateRequestUpdate", FakeUpdate),
            patch.object(server, "call_plaid", plaid_call),
            patch.object(server, "PLAID_COUNTRY_CODES", ["CA"]),
            patch.object(server, "PLAID_CLIENT_NAME", "LifeTracker Test"),
            patch.object(server, "PLAID_REDIRECT_URI", None),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
        ):
            result = await server.create_plaid_update_link_token(
                "item-1",
                user_id="user-1",
            )

        request = plaid_call.await_args.args[1]
        self.assertEqual(request.values["access_token"], "fake-access-token")
        self.assertNotIn("products", request.values)
        self.assertNotIn("transactions", request.values)
        self.assertTrue(request.values["update"].account_selection_enabled)
        self.assertEqual(request.values["user"].client_user_id, "user-1")
        self.assertEqual(result["link_token"], "update-link-token")
        self.assertTrue(result["update_mode"])

    async def test_exchange_persistence_failure_removes_only_a_confirmed_orphan(self):
        exchange_response = SimpleNamespace(
            item_id="item-1",
            access_token="access-sandbox-orphan",
        )
        plaid_calls = AsyncMock(
            side_effect=[
                exchange_response,
                SimpleNamespace(request_id="remove-request-1"),
            ]
        )
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(side_effect=[None, None]),
            update_one=AsyncMock(side_effect=RuntimeError("persistence unavailable")),
        )
        fake_client = SimpleNamespace(
            item_public_token_exchange=object(),
            item_remove=object(),
        )

        with (
            patch.object(server, "db", SimpleNamespace(plaid_items=plaid_items)),
            patch.object(server, "require_plaid_client", return_value=fake_client),
            patch.object(server, "ItemPublicTokenExchangeRequest", FakePlaidRequest),
            patch.object(server, "ItemRemoveRequest", FakePlaidRequest),
            patch.object(server, "call_plaid", plaid_calls),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.exchange_plaid_public_token(
                server.PlaidPublicTokenExchangeRequestBody(public_token="public-sandbox-test"),
                FakeBackgroundTasks(),
                current_user={"id": "user-1", "full_name": "Test User"},
            )

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(plaid_calls.await_count, 2)
        self.assertIs(plaid_calls.await_args_list[1].args[0], fake_client.item_remove)
        self.assertEqual(
            plaid_calls.await_args_list[1].args[1].values["access_token"],
            "access-sandbox-orphan",
        )
        self.assertEqual(
            plaid_items.find_one.await_args_list[1].args,
            ({"user_id": "user-1", "item_id": "item-1"}, {"id": 1}),
        )

    async def test_exchange_ambiguous_durable_lookup_never_removes_remote_item(self):
        plaid_calls = AsyncMock(
            return_value=SimpleNamespace(
                item_id="item-1",
                access_token="access-sandbox-ambiguous",
            )
        )
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(
                side_effect=[None, RuntimeError("durability lookup unavailable")]
            ),
            update_one=AsyncMock(side_effect=RuntimeError("persistence unavailable")),
        )
        fake_client = SimpleNamespace(
            item_public_token_exchange=object(),
            item_remove=object(),
        )

        with (
            patch.object(server, "db", SimpleNamespace(plaid_items=plaid_items)),
            patch.object(server, "require_plaid_client", return_value=fake_client),
            patch.object(server, "ItemPublicTokenExchangeRequest", FakePlaidRequest),
            patch.object(server, "ItemRemoveRequest", FakePlaidRequest),
            patch.object(server, "call_plaid", plaid_calls),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.exchange_plaid_public_token(
                server.PlaidPublicTokenExchangeRequestBody(public_token="public-sandbox-test"),
                FakeBackgroundTasks(),
                current_user={"id": "user-1", "full_name": "Test User"},
            )

        self.assertEqual(raised.exception.status_code, 500)
        plaid_calls.assert_awaited_once()
        self.assertIs(plaid_calls.await_args.args[0], fake_client.item_public_token_exchange)

    async def test_exchange_enrichment_failure_preserves_persisted_remote_item(self):
        exchange_response = SimpleNamespace(
            item_id="item-1",
            access_token="access-sandbox-durable",
        )
        latest_connection = {
            "id": "connection-1",
            "user_id": "user-1",
            "item_id": "item-1",
            "status": "active",
            "accounts": [],
        }
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(side_effect=[None, latest_connection]),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        )
        plaid_calls = AsyncMock(return_value=exchange_response)
        sync_summary = {
            "item_id": "item-1",
            "accounts_synced": 0,
            "added_count": 0,
            "modified_count": 0,
            "merged_count": 0,
            "removed_count": 0,
        }
        sync_request = AsyncMock(return_value=sync_summary)
        background_tasks = FakeBackgroundTasks()
        fake_client = SimpleNamespace(
            item_public_token_exchange=object(),
            item_remove=object(),
        )

        with (
            patch.object(server, "db", SimpleNamespace(plaid_items=plaid_items)),
            patch.object(server, "require_plaid_client", return_value=fake_client),
            patch.object(server.uuid, "uuid4", return_value="connection-1"),
            patch.object(server, "ItemPublicTokenExchangeRequest", FakePlaidRequest),
            patch.object(server, "ItemRemoveRequest", FakePlaidRequest),
            patch.object(server, "call_plaid", plaid_calls),
            patch.object(
                server,
                "fetch_plaid_accounts_for_item",
                AsyncMock(side_effect=RuntimeError("accounts enrichment unavailable")),
            ),
            patch.object(server, "request_plaid_item_sync", sync_request),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
        ):
            response = await server.exchange_plaid_public_token(
                server.PlaidPublicTokenExchangeRequestBody(public_token="public-sandbox-test"),
                background_tasks,
                current_user={"id": "user-1", "full_name": "Test User"},
            )

        plaid_calls.assert_awaited_once()
        self.assertIs(plaid_calls.await_args.args[0], fake_client.item_public_token_exchange)
        self.assertEqual(plaid_items.update_one.await_count, 2)
        pending_write = plaid_items.update_one.await_args_list[0].args[1]["$set"]
        active_write = plaid_items.update_one.await_args_list[1].args[1]["$set"]
        self.assertEqual(pending_write["status"], "exchange_pending")
        self.assertIn("access_token_ciphertext", pending_write)
        self.assertNotIn("access-sandbox-durable", pending_write["access_token_ciphertext"])
        self.assertEqual(active_write["status"], "active")
        self.assertEqual(active_write["accounts"], [])
        self.assertEqual(response["sync"], sync_summary)
        self.assertEqual(len(background_tasks.tasks), 1)

    async def test_disconnect_removes_remote_item_then_finalizes_hidden_tombstone(self):
        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("fake-access-token")
        existing_item = {
            "id": "connection-1",
            "user_id": "user-1",
            "item_id": "item-1",
            "status": "active",
            "access_token_ciphertext": ciphertext,
        }
        operation_order = []

        async def remove_remote_item(_request_fn, request):
            operation_order.append("remote")
            self.assertEqual(request.values["access_token"], "fake-access-token")
            return SimpleNamespace(request_id="remove-request-1")

        async def delete_local_transactions(_filter):
            operation_order.append("local")
            return SimpleNamespace(deleted_count=3)

        plaid_items = SimpleNamespace(
            find_one=AsyncMock(return_value=existing_item),
            find_one_and_update=AsyncMock(return_value={**existing_item, "status": "disconnecting"}),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
            delete_one=AsyncMock(),
            find=MagicMock(return_value=FakeAsyncCursor([])),
        )
        transactions = SimpleNamespace(
            delete_many=AsyncMock(side_effect=delete_local_transactions),
            update_many=AsyncMock(),
        )
        fake_db = SimpleNamespace(plaid_items=plaid_items, transactions=transactions)
        fake_client = SimpleNamespace(item_remove=object())

        with (
            patch.object(server, "db", fake_db),
            patch.object(server, "require_plaid_client", return_value=fake_client),
            patch.object(server, "ItemRemoveRequest", FakePlaidRequest),
            patch.object(server, "call_plaid", AsyncMock(side_effect=remove_remote_item)),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
        ):
            response = await server.disconnect_plaid_item(
                "item-1",
                remove_transactions=True,
                user_id="user-1",
            )
            visible_connections = await server.list_plaid_connections(user_id="user-1")

        expected_scope = {"user_id": "user-1", "item_id": "item-1"}
        plaid_items.find_one.assert_awaited_once_with(expected_scope)
        lease_id = plaid_items.find_one_and_update.await_args.args[1]["$set"]["sync_lease_id"]
        plaid_items.delete_one.assert_not_awaited()
        final_filter, final_operation = plaid_items.update_one.await_args_list[-1].args
        self.assertEqual(
            final_filter,
            {
                "id": "connection-1",
                "user_id": "user-1",
                "sync_lease_id": lease_id,
                "remote_removed_at": {"$ne": None},
            },
        )
        tombstone = final_operation["$set"]
        self.assertEqual(tombstone["status"], "disconnected")
        self.assertTrue(tombstone["disconnect_remove_transactions"])
        self.assertFalse(tombstone["sync_pending"])
        self.assertEqual(
            tombstone["tombstone_expires_at"] - tombstone["disconnected_at"],
            timedelta(days=7),
        )
        self.assertEqual(
            final_operation["$unset"],
            {"sync_lease_id": "", "sync_lease_until": "", "sync_started_at": ""},
        )
        self.assertEqual(operation_order, ["remote", "local"])
        transactions.delete_many.assert_awaited_once_with(
            {"user_id": "user-1", "plaid_item_id": "item-1"}
        )
        self.assertEqual(response["removed_transactions"], 3)
        self.assertEqual(response["request_id"], "remove-request-1")
        self.assertEqual(visible_connections, {"count": 0, "items": []})
        plaid_items.find.assert_called_once_with(
            {"user_id": "user-1", "status": {"$ne": "disconnected"}}
        )

    async def test_disconnect_retention_policy_marks_transactions_and_is_durable(self):
        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("fake-access-token")
        existing_item = {
            "id": "connection-1",
            "user_id": "user-1",
            "item_id": "item-1",
            "status": "active",
            "access_token_ciphertext": ciphertext,
        }
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(return_value=existing_item),
            find_one_and_update=AsyncMock(
                return_value={**existing_item, "status": "disconnecting"}
            ),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
            delete_one=AsyncMock(),
        )
        transactions = SimpleNamespace(
            delete_many=AsyncMock(),
            update_many=AsyncMock(),
        )

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(plaid_items=plaid_items, transactions=transactions),
            ),
            patch.object(
                server,
                "require_plaid_client",
                return_value=SimpleNamespace(item_remove=object()),
            ),
            patch.object(server, "ItemRemoveRequest", FakePlaidRequest),
            patch.object(
                server,
                "call_plaid",
                AsyncMock(return_value=SimpleNamespace(request_id="remove-request-1")),
            ),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
        ):
            response = await server.disconnect_plaid_item(
                "item-1",
                remove_transactions=False,
                user_id="user-1",
            )

        plaid_items.delete_one.assert_not_awaited()
        transactions.delete_many.assert_not_awaited()
        transaction_scope, retention_operation = transactions.update_many.await_args.args
        self.assertEqual(
            transaction_scope,
            {"user_id": "user-1", "plaid_item_id": "item-1"},
        )
        self.assertTrue(retention_operation["$set"]["plaid_connection_removed"])
        self.assertIsInstance(
            retention_operation["$set"]["plaid_disconnected_at"],
            datetime,
        )
        final_operation = plaid_items.update_one.await_args_list[-1].args[1]
        self.assertEqual(final_operation["$set"]["status"], "disconnected")
        self.assertFalse(final_operation["$set"]["disconnect_remove_transactions"])
        self.assertEqual(response["removed_transactions"], 0)

    async def test_stale_sync_cleanup_reapplies_durable_disconnect_policy(self):
        transactions = SimpleNamespace(
            delete_many=AsyncMock(),
            update_many=AsyncMock(),
        )
        disconnected_at = datetime(2026, 8, 31, 12, 0)
        base_item = {
            "id": "connection-1",
            "item_id": "item-1",
            "user_id": "user-1",
            "status": "disconnected",
            "disconnected_at": disconnected_at,
        }

        with patch.object(server, "db", SimpleNamespace(transactions=transactions)):
            await server.cleanup_disconnected_plaid_data(
                {**base_item, "disconnect_remove_transactions": True}
            )
            await server.cleanup_disconnected_plaid_data(
                {**base_item, "disconnect_remove_transactions": False}
            )

        transaction_scope = {"user_id": "user-1", "plaid_item_id": "item-1"}
        transactions.delete_many.assert_awaited_once_with(transaction_scope)
        transactions.update_many.assert_awaited_once_with(
            transaction_scope,
            {
                "$set": {
                    "plaid_connection_removed": True,
                    "plaid_disconnected_at": disconnected_at,
                }
            },
        )

    async def test_disconnect_remote_failure_preserves_local_connection(self):
        with patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY):
            ciphertext = server.encrypt_plaid_access_token("fake-access-token")
        existing_item = {
            "id": "connection-1",
            "user_id": "user-1",
            "item_id": "item-1",
            "status": "active",
            "access_token_ciphertext": ciphertext,
        }
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(return_value=existing_item),
            find_one_and_update=AsyncMock(return_value={**existing_item, "status": "disconnecting"}),
            update_one=AsyncMock(),
            delete_one=AsyncMock(),
        )
        transactions = SimpleNamespace(delete_many=AsyncMock())
        fake_client = SimpleNamespace(item_remove=object())

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(plaid_items=plaid_items, transactions=transactions),
            ),
            patch.object(server, "require_plaid_client", return_value=fake_client),
            patch.object(server, "ItemRemoveRequest", FakePlaidRequest),
            patch.object(
                server,
                "call_plaid",
                AsyncMock(side_effect=FakePlaidApiException("Plaid is unavailable")),
            ),
            patch.object(server, "plaid", SimpleNamespace(ApiException=FakePlaidApiException)),
            patch.object(server, "PLAID_TOKEN_ENCRYPTION_KEY", TEST_FERNET_KEY),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.disconnect_plaid_item(
                "item-1",
                remove_transactions=True,
                user_id="user-1",
            )

        self.assertEqual(raised.exception.status_code, 502)
        plaid_items.delete_one.assert_not_awaited()
        transactions.delete_many.assert_not_awaited()
        recovery_filter, recovery_operation = plaid_items.update_one.await_args.args
        self.assertEqual(recovery_filter["id"], "connection-1")
        self.assertEqual(recovery_filter["user_id"], "user-1")
        self.assertEqual(recovery_operation["$set"]["status"], "active")
        self.assertIn("Plaid disconnect failed", recovery_operation["$set"]["last_error"])
        self.assertEqual(
            recovery_operation["$unset"],
            {"sync_lease_id": "", "sync_lease_until": ""},
        )

    async def test_disconnect_unknown_item_returns_not_found_without_deleting(self):
        plaid_items = SimpleNamespace(
            find_one=AsyncMock(return_value=None),
            delete_one=AsyncMock(),
        )
        transactions = SimpleNamespace(delete_many=AsyncMock())

        with (
            patch.object(
                server,
                "db",
                SimpleNamespace(plaid_items=plaid_items, transactions=transactions),
            ),
            self.assertRaises(server.HTTPException) as raised,
        ):
            await server.disconnect_plaid_item(
                "unknown-item",
                remove_transactions=True,
                user_id="user-1",
            )

        self.assertEqual(raised.exception.status_code, 404)
        plaid_items.delete_one.assert_not_awaited()
        transactions.delete_many.assert_not_awaited()


def tearDownModule():
    server.client.close()


if __name__ == "__main__":
    unittest.main()
