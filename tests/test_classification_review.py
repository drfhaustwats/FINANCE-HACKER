"""
Tests for the Classification Review Center backend API.

Covers: multi-user scope isolation, name-independence, pending exclusion,
ambiguous-no-auto-match, resolved review counts, response privacy,
deterministic ordering/pagination, and update-conflict handling.
"""
import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# Configure environment before importing server so it never touches real services.
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=1")
os.environ.setdefault("DB_NAME", "finance_hacker_review_unit_tests")
os.environ.setdefault("SECRET_KEY", "review-tests-only-key-not-for-production")
os.environ.setdefault("PLAID_CLIENT_ID", "")
os.environ.setdefault("PLAID_SECRET", "")
os.environ.setdefault("PLAID_ENV", "sandbox")
os.environ.setdefault("PLAID_PRODUCTS", "transactions")
os.environ.setdefault("PLAID_COUNTRY_CODES", "CA")
os.environ.setdefault("PLAID_REDIRECT_URI", "")
os.environ.setdefault("PLAID_WEBHOOK_URL", "")
os.environ.setdefault(
    "PLAID_TOKEN_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
)
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("GOOGLE_CLIENT_ID", "")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "")
os.environ.setdefault("GMAIL_EMAIL", "")
os.environ.setdefault("GMAIL_APP_PASSWORD", "")

import dotenv

_real_load_dotenv = dotenv.load_dotenv
try:
    dotenv.load_dotenv = lambda *args, **kwargs: False
    from backend import server
finally:
    dotenv.load_dotenv = _real_load_dotenv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tx(
    tx_id,
    amount,
    *,
    date="2026-08-15",
    category="Transfers and Payments",
    description="Test transfer",
    user_id="user-a",
    account_type="debit",
    plaid_account_id=None,
    source_account_id=None,
    plaid_transaction_id=None,
    plaid_personal_finance_detailed=None,
    plaid_pending=False,
    is_internal_transfer=None,
    is_internal_transfer_source=None,
    classification_scope_overrides=None,
    analytics_class_override=None,
    analytics_class_override_source=None,
    **kwargs,
):
    """Build a minimal transaction document for tests."""
    doc = {
        "id": tx_id,
        "date": date,
        "amount": amount,
        "category": category,
        "description": description,
        "account_type": account_type,
        "user_id": user_id,
    }
    if plaid_account_id is not None:
        doc["plaid_account_id"] = plaid_account_id
    if source_account_id is not None:
        doc["source_account_id"] = source_account_id
    if plaid_transaction_id is not None:
        doc["plaid_transaction_id"] = plaid_transaction_id
    if plaid_personal_finance_detailed is not None:
        doc["plaid_personal_finance_detailed"] = plaid_personal_finance_detailed
    if plaid_pending:
        doc["plaid_pending"] = True
    if is_internal_transfer is not None:
        doc["is_internal_transfer"] = is_internal_transfer
    if is_internal_transfer_source is not None:
        doc["is_internal_transfer_source"] = is_internal_transfer_source
    if classification_scope_overrides is not None:
        doc["classification_scope_overrides"] = classification_scope_overrides
    if analytics_class_override is not None:
        doc["analytics_class_override"] = analytics_class_override
    if analytics_class_override_source is not None:
        doc["analytics_class_override_source"] = analytics_class_override_source
    doc.update(kwargs)
    return doc


def _legacy_tx(tx_id, amount, *, date="2026-08-15", user_id="user-a", **kwargs):
    """Build a transaction that has an unverified legacy internal-transfer flag."""
    return _tx(
        tx_id,
        amount,
        date=date,
        user_id=user_id,
        plaid_transaction_id=f"plaid-{tx_id}",
        plaid_personal_finance_detailed="TRANSFER_OUT_ACCOUNT_TRANSFER",
        is_internal_transfer=True,
        **kwargs,
    )


class AsyncCursor:
    """Streaming cursor that mimics Motor's async iteration."""

    def __init__(self, documents):
        self._iter = iter(list(documents))

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class FilteredFakeTransactions:
    """MongoDB transactions collection fake that applies user_id scope filters.

    Unlike a naive pass-through, this fake records and honours the ``user_id``
    filter supplied to ``find``, so adversarial tests can detect regressions
    where a backend change would return another user's rows.
    """

    def __init__(self, documents):
        self._documents = list(documents)

    def find(self, filter_dict, projection=None):
        uid_filter = filter_dict.get("user_id")
        if uid_filter is None:
            return AsyncCursor(self._documents)
        if isinstance(uid_filter, dict):
            # Support {"user_id": {"$in": [...]}} for household views.
            allowed = uid_filter.get("$in")
            if isinstance(allowed, (list, tuple)):
                docs = [d for d in self._documents if d.get("user_id") in allowed]
            else:
                docs = self._documents
        else:
            docs = [d for d in self._documents if d.get("user_id") == uid_filter]
        return AsyncCursor(docs)

    async def find_one(self, filter_dict, projection=None):
        uid_filter = filter_dict.get("user_id")
        tx_id_filter = filter_dict.get("id")
        for doc in self._documents:
            if uid_filter is not None and doc.get("user_id") != uid_filter:
                continue
            if tx_id_filter is not None and doc.get("id") != tx_id_filter:
                continue
            return dict(doc)
        return None

    async def update_one(self, filter_dict, update_op):
        return MagicMock(matched_count=1)


async def _call_review_queue(
    transactions,
    *,
    page=1,
    page_size=25,
    include_pending=False,
    user_id="user-a",
    household_id=None,
    view_user_id=None,
):
    """
    Call get_classification_review_queue with FilteredFakeTransactions and return
    the result.

    build_view_filter is patched to return {"user_id": user_id} so the fake
    collection applies real user-id scope isolation.  get_ai_scope_id is invoked
    with real logic so scope-isolation behaviour is exercised.
    """
    view_uid = view_user_id if view_user_id is not None else user_id
    current_user = {"id": user_id, "email": f"{user_id}@test.invalid", "household_id": household_id}
    scope_id = server.get_ai_scope_id(current_user, view_uid)

    # Pre-attach the scope_id that load_analytics_transactions would set.
    # FilteredFakeTransactions will filter the documents before yielding them;
    # load_analytics_transactions then overwrites _classification_scope_id with
    # the same value, so there is no double-application risk.
    scoped_transactions = [
        {**tx, "_classification_scope_id": scope_id} for tx in transactions
    ]

    with patch.object(
        server,
        "db",
        SimpleNamespace(transactions=FilteredFakeTransactions(scoped_transactions)),
    ):
        # Patch build_view_filter to avoid DB user lookup for household members.
        with patch(
            "backend.server.build_view_filter",
            new=AsyncMock(return_value={"user_id": user_id}),
        ):
            return await server.get_classification_review_queue(
                page=page,
                page_size=page_size,
                include_pending=include_pending,
                current_user=current_user,
                view_user_id=view_uid,
            )


# ---------------------------------------------------------------------------
# Unit tests: helper functions
# ---------------------------------------------------------------------------


class BuildReviewItemTests(unittest.TestCase):
    """_build_review_item must not expose private or scoped provenance."""

    def test_excludes_stable_account_identifiers(self):
        tx = _tx(
            "tx-priv",
            100.0,
            plaid_account_id="plaid-acct-secret",
            source_account_id="src-acct-secret",
            classification_scope_overrides={"user:user-a": {"internal_transfer": True}},
        )
        tx["_classification_scope_id"] = "user:user-a"
        item = server._build_review_item(tx, ["unresolved_legacy_transfer"])

        for forbidden in (
            "plaid_account_id",
            "source_account_id",
            "classification_scope_overrides",
            "_classification_scope_id",
            "user_id",
        ):
            self.assertNotIn(forbidden, item, f"Field {forbidden!r} must not be exposed")

    def test_required_fields_present(self):
        tx = _tx("tx-fields", 50.0)
        tx["_classification_scope_id"] = "user:user-a"
        item = server._build_review_item(tx, ["ambiguous_transfer_candidate"])

        for required in (
            "transaction_id",
            "date",
            "amount",
            "currency",
            "category",
            "description",
            "account_type",
            "review_reason",
            "review_reasons",
            "current_analytics_class",
            "current_internal_transfer_override",
            "classification_review_required",
            "expected_updated_at",
        ):
            self.assertIn(required, item, f"Field {required!r} must be present")

    def test_currency_and_optimistic_timestamp_are_preserved(self):
        tx = _tx(
            "tx-currency-version",
            50.0,
            iso_currency_code="USD",
            updated_at="2026-08-31T10:00:00",
        )
        tx["_classification_scope_id"] = "user:user-a"
        item = server._build_review_item(tx, ["ambiguous_transfer_candidate"])

        self.assertEqual(item["currency"], "USD")
        self.assertEqual(item["expected_updated_at"], "2026-08-31T10:00:00")

    def test_review_reason_propagated(self):
        tx = _tx("tx-reason", 50.0)
        tx["_classification_scope_id"] = "user:user-a"
        for reason in ("unresolved_legacy_transfer", "ambiguous_transfer_candidate"):
            item = server._build_review_item(tx, [reason])
            self.assertEqual(item["review_reason"], reason)
            self.assertEqual(item["review_reasons"], [reason])

    def test_multiple_reasons_propagated(self):
        tx = _tx("tx-multi-reason", 50.0)
        tx["_classification_scope_id"] = "user:user-a"
        reasons = ["unresolved_legacy_transfer", "ambiguous_transfer_candidate"]
        item = server._build_review_item(tx, reasons)
        self.assertEqual(item["review_reason"], "unresolved_legacy_transfer")
        self.assertEqual(item["review_reasons"], reasons)

    def test_internal_override_string_mapping(self):
        base = _tx("tx-map", 100.0)
        base["_classification_scope_id"] = "user:user-a"

        internal = {
            **base,
            "classification_scope_overrides": {
                "user:user-a": {"internal_transfer": True, "internal_transfer_source": "user"}
            },
        }
        external = {
            **base,
            "classification_scope_overrides": {
                "user:user-a": {"internal_transfer": False, "internal_transfer_source": "user"}
            },
        }

        self.assertEqual(
            server._build_review_item(internal, ["unresolved_legacy_transfer"])[
                "current_internal_transfer_override"
            ],
            "internal",
        )
        self.assertEqual(
            server._build_review_item(external, ["unresolved_legacy_transfer"])[
                "current_internal_transfer_override"
            ],
            "external",
        )
        self.assertEqual(
            server._build_review_item(base, ["unresolved_legacy_transfer"])[
                "current_internal_transfer_override"
            ],
            "auto",
        )


# ---------------------------------------------------------------------------
# Unit tests: classification helper functions
# ---------------------------------------------------------------------------


class ClassificationHelperTests(unittest.TestCase):
    def test_legacy_flag_detected_as_unresolved(self):
        tx = _legacy_tx("legacy-det", 200.0)
        tx["_classification_scope_id"] = "user:user-a"
        self.assertTrue(server.has_unverified_legacy_internal_transfer_flag(tx))
        self.assertTrue(server.has_unresolved_legacy_internal_transfer_review(tx))

    def test_scoped_override_resolves_legacy_review(self):
        tx = _legacy_tx(
            "legacy-resolved",
            200.0,
            classification_scope_overrides={
                "user:user-a": {
                    "internal_transfer": False,
                    "internal_transfer_source": "user",
                }
            },
        )
        tx["_classification_scope_id"] = "user:user-a"
        self.assertFalse(server.has_unresolved_legacy_internal_transfer_review(tx))

    def test_analytics_class_override_resolves_legacy_review(self):
        tx = _legacy_tx(
            "legacy-class-resolved",
            200.0,
            classification_scope_overrides={
                "user:user-a": {
                    "analytics_class": "expense",
                    "analytics_class_source": "user",
                }
            },
        )
        tx["_classification_scope_id"] = "user:user-a"
        self.assertFalse(server.has_unresolved_legacy_internal_transfer_review(tx))

    def test_scoped_auto_mode_resolves_legacy_review(self):
        """Explicit Automatic decision (internal_transfer_mode='auto') resolves legacy."""
        tx = _legacy_tx(
            "legacy-auto-resolved",
            200.0,
            classification_scope_overrides={
                "user:user-a": {
                    "internal_transfer_mode": "auto",
                }
            },
        )
        tx["_classification_scope_id"] = "user:user-a"
        self.assertFalse(server.has_unresolved_legacy_internal_transfer_review(tx))

    def test_name_independence_no_pair_without_account_ids(self):
        """Transfer matching must not use counterparty names to establish ownership."""
        tx_out = _tx("named-out", 500.0, description="E-TRANSFER to Counterparty Name")
        tx_in = _tx("named-in", -500.0, description="E-TRANSFER from Counterparty Name")
        result = server.detect_internal_transfer_analysis([tx_out, tx_in])
        self.assertEqual(result["matched_ids"], set())
        self.assertEqual(result["ambiguous_ids"], set())

    def test_ambiguous_no_auto_match(self):
        """Multiple equal-amount candidates must not be automatically paired."""
        outflow = _tx("amb-out", 300.0, plaid_account_id="chequing")
        inflow_a = _tx("amb-in-a", -300.0, plaid_account_id="savings")
        inflow_b = _tx("amb-in-b", -300.0, plaid_account_id="joint")
        result = server.detect_internal_transfer_analysis([outflow, inflow_a, inflow_b])
        self.assertEqual(result["matched_ids"], set())
        self.assertIn("amb-out", result["ambiguous_ids"])
        self.assertIn("amb-in-a", result["ambiguous_ids"])
        self.assertIn("amb-in-b", result["ambiguous_ids"])

    def test_personal_scope_override_invisible_in_household_scope(self):
        """A user's personal decision must not surface in the household scope."""
        tx = _tx(
            "scope-iso-tx",
            85.0,
            user_id="member-x",
            classification_scope_overrides={
                "user:member-x": {
                    "analytics_class": "expense",
                    "analytics_class_source": "user",
                }
            },
        )
        personal = {**tx, "_classification_scope_id": "user:member-x"}
        household = {**tx, "_classification_scope_id": "household:hh-99"}

        self.assertEqual(server.get_analytics_class_override(personal), "expense")
        self.assertIsNone(server.get_analytics_class_override(household))

    def test_household_scope_override_invisible_in_personal_scope(self):
        """A household decision must not surface in the personal scope."""
        tx = _tx(
            "hh-iso-tx",
            150.0,
            user_id="member-y",
            classification_scope_overrides={
                "household:hh-77": {
                    "internal_transfer": True,
                    "internal_transfer_source": "user",
                }
            },
        )
        personal = {**tx, "_classification_scope_id": "user:member-y"}
        household = {**tx, "_classification_scope_id": "household:hh-77"}

        self.assertIsNone(server.get_internal_transfer_override(personal))
        self.assertIs(server.get_internal_transfer_override(household), True)

    def test_has_explicit_scoped_auto_decision_true(self):
        """_has_explicit_scoped_auto_decision returns True for auto marker in scope."""
        tx = _tx(
            "auto-marker-tx",
            100.0,
            classification_scope_overrides={
                "user:user-a": {"internal_transfer_mode": "auto"}
            },
        )
        tx["_classification_scope_id"] = "user:user-a"
        self.assertTrue(server._has_explicit_scoped_auto_decision(tx))

    def test_has_explicit_scoped_auto_decision_false_no_marker(self):
        """_has_explicit_scoped_auto_decision returns False when no decision made."""
        tx = _tx("no-auto-tx", 100.0)
        tx["_classification_scope_id"] = "user:user-a"
        self.assertFalse(server._has_explicit_scoped_auto_decision(tx))

    def test_has_explicit_scoped_auto_decision_false_other_scope(self):
        """_has_explicit_scoped_auto_decision ignores another scope's auto marker."""
        tx = _tx(
            "other-scope-auto",
            100.0,
            classification_scope_overrides={
                "user:user-b": {"internal_transfer_mode": "auto"}
            },
        )
        tx["_classification_scope_id"] = "user:user-a"
        self.assertFalse(server._has_explicit_scoped_auto_decision(tx))

    def test_matched_ids_resolves_legacy_review(self):
        """has_unresolved_legacy_internal_transfer_review returns False when row is in matched_ids."""
        tx = _legacy_tx("matched-leg", 300.0)
        tx["_classification_scope_id"] = "user:user-a"
        # Without matched_ids the row still needs review
        self.assertTrue(server.has_unresolved_legacy_internal_transfer_review(tx))
        # With matched_ids containing this row's id, it is resolved
        self.assertFalse(
            server.has_unresolved_legacy_internal_transfer_review(
                tx, matched_ids={"matched-leg"}
            )
        )

    def test_matched_ids_empty_set_does_not_resolve(self):
        """An empty matched_ids set must not resolve an otherwise-unresolved legacy row."""
        tx = _legacy_tx("unmatched-leg", 150.0)
        tx["_classification_scope_id"] = "user:user-a"
        self.assertTrue(
            server.has_unresolved_legacy_internal_transfer_review(
                tx, matched_ids=set()
            )
        )

    def test_matched_ids_none_behaves_as_before(self):
        """Passing matched_ids=None preserves existing behaviour."""
        tx = _legacy_tx("none-matched-leg", 150.0)
        tx["_classification_scope_id"] = "user:user-a"
        self.assertTrue(
            server.has_unresolved_legacy_internal_transfer_review(tx, matched_ids=None)
        )


# ---------------------------------------------------------------------------
# Integration tests: endpoint behaviour
# ---------------------------------------------------------------------------


class ReviewQueueEndpointTests(unittest.IsolatedAsyncioTestCase):

    async def test_response_marks_shared_scope_read_only(self):
        transaction = _legacy_tx("shared-read-only", 100.0)
        personal = await _call_review_queue([transaction], view_user_id="user-a")
        shared = await _call_review_queue(
            [transaction],
            household_id="household-a",
            view_user_id="family_view",
        )

        self.assertFalse(personal["read_only"])
        self.assertTrue(shared["read_only"])

    async def test_legacy_unresolved_appears_in_queue(self):
        tx = _legacy_tx("leg-1", 100.0)
        result = await _call_review_queue([tx])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["unresolved_legacy_count"], 1)
        self.assertEqual(result["items"][0]["review_reason"], "unresolved_legacy_transfer")
        self.assertEqual(result["items"][0]["transaction_id"], "leg-1")

    async def test_pending_excluded_by_default(self):
        tx = _legacy_tx("pending-leg", 100.0, plaid_pending=True)
        result = await _call_review_queue([tx], include_pending=False)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["items"], [])

    async def test_pending_included_when_requested(self):
        tx = _legacy_tx("pending-inc", 100.0, plaid_pending=True)
        result = await _call_review_queue([tx], include_pending=True)
        self.assertEqual(result["total"], 1)

    async def test_resolved_legacy_not_in_queue(self):
        tx = _legacy_tx(
            "leg-resolved",
            100.0,
            classification_scope_overrides={
                "user:user-a": {
                    "internal_transfer": False,
                    "internal_transfer_source": "user",
                }
            },
        )
        result = await _call_review_queue([tx])
        self.assertEqual(result["total"], 0)

    async def test_ambiguous_transfer_appears_in_queue(self):
        outflow = _tx("amb-out", 300.0, plaid_account_id="chequing")
        inflow_a = _tx("amb-in-a", -300.0, plaid_account_id="savings")
        inflow_b = _tx("amb-in-b", -300.0, plaid_account_id="joint")
        result = await _call_review_queue([outflow, inflow_a, inflow_b])
        ids = {item["transaction_id"] for item in result["items"]}
        self.assertIn("amb-out", ids)
        self.assertIn("amb-in-a", ids)
        self.assertIn("amb-in-b", ids)
        self.assertEqual(result["ambiguous_transfer_count"], 3)

    async def test_ambiguous_with_explicit_external_override_not_in_queue(self):
        """Ambiguous row explicitly marked external by the user is resolved."""
        outflow = _tx(
            "amb-ext-out",
            300.0,
            plaid_account_id="chequing",
            classification_scope_overrides={
                "user:user-a": {
                    "internal_transfer": False,
                    "internal_transfer_source": "user",
                }
            },
        )
        inflow_a = _tx("amb-ext-in-a", -300.0, plaid_account_id="savings")
        inflow_b = _tx("amb-ext-in-b", -300.0, plaid_account_id="joint")
        result = await _call_review_queue([outflow, inflow_a, inflow_b])
        ids = {item["transaction_id"] for item in result["items"]}
        self.assertNotIn("amb-ext-out", ids)

    async def test_automatic_choice_resolves_ambiguous_from_queue(self):
        """Choosing Automatic (internal_transfer_mode='auto') removes the row."""
        outflow = _tx(
            "amb-auto-out",
            400.0,
            plaid_account_id="chq",
            classification_scope_overrides={
                "user:user-a": {"internal_transfer_mode": "auto"}
            },
        )
        inflow_a = _tx("amb-auto-in-a", -400.0, plaid_account_id="sav")
        inflow_b = _tx("amb-auto-in-b", -400.0, plaid_account_id="inv")
        result = await _call_review_queue([outflow, inflow_a, inflow_b])
        ids = {item["transaction_id"] for item in result["items"]}
        self.assertNotIn("amb-auto-out", ids,
            "Ambiguous row with explicit Automatic decision must leave the queue")

    async def test_response_privacy_no_account_identifiers(self):
        """Review items must never expose raw stable account or scope identifiers."""
        tx = _legacy_tx(
            "priv-tx",
            100.0,
            plaid_account_id="plaid-secret-acct",
            source_account_id="src-secret-acct",
        )
        result = await _call_review_queue([tx])
        self.assertGreater(result["total"], 0)
        for item in result["items"]:
            self.assertNotIn("plaid_account_id", item)
            self.assertNotIn("source_account_id", item)
            self.assertNotIn("classification_scope_overrides", item)
            self.assertNotIn("_classification_scope_id", item)
            self.assertNotIn("user_id", item)

    async def test_deterministic_ordering_date_desc_id_asc(self):
        """Results must be ordered by date descending, then transaction id ascending."""
        transactions = [
            _legacy_tx("tx-2026-01-b", 100.0, date="2026-01-15"),
            _legacy_tx("tx-2026-02", 100.0, date="2026-02-15"),
            _legacy_tx("tx-2026-01-a", 100.0, date="2026-01-15"),
        ]
        result = await _call_review_queue(transactions)
        ids = [item["transaction_id"] for item in result["items"]]
        # Newest first; within same date, id alphabetically ascending
        self.assertEqual(ids[0], "tx-2026-02")
        # "tx-2026-01-a" < "tx-2026-01-b" lexicographically
        self.assertEqual(ids[1], "tx-2026-01-a")
        self.assertEqual(ids[2], "tx-2026-01-b")

    async def test_deterministic_ordering_is_stable_across_calls(self):
        """Repeated calls with the same data produce the same ordering."""
        transactions = [_legacy_tx(f"tx-stable-{i}", 100.0, date="2026-05-01") for i in range(5)]
        result1 = await _call_review_queue(list(transactions))
        result2 = await _call_review_queue(list(transactions))
        ids1 = [item["transaction_id"] for item in result1["items"]]
        ids2 = [item["transaction_id"] for item in result2["items"]]
        self.assertEqual(ids1, ids2)

    async def test_pagination_first_page(self):
        transactions = [
            _legacy_tx(f"page-tx-{i:02d}", 100.0, date=f"2026-01-{i:02d}")
            for i in range(1, 6)
        ]
        result = await _call_review_queue(list(transactions), page=1, page_size=3)
        self.assertEqual(result["total"], 5)
        self.assertEqual(len(result["items"]), 3)
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["page_size"], 3)

    async def test_pagination_second_page(self):
        transactions = [
            _legacy_tx(f"page2-tx-{i:02d}", 100.0, date=f"2026-01-{i:02d}")
            for i in range(1, 6)
        ]
        result = await _call_review_queue(list(transactions), page=2, page_size=3)
        self.assertEqual(result["total"], 5)
        self.assertEqual(len(result["items"]), 2)

    async def test_pagination_no_overlap(self):
        transactions = [
            _legacy_tx(f"pg-no-ov-{i:02d}", 100.0, date=f"2026-01-{i:02d}")
            for i in range(1, 6)
        ]
        r1 = await _call_review_queue(list(transactions), page=1, page_size=3)
        r2 = await _call_review_queue(list(transactions), page=2, page_size=3)
        ids1 = {item["transaction_id"] for item in r1["items"]}
        ids2 = {item["transaction_id"] for item in r2["items"]}
        self.assertEqual(len(ids1 & ids2), 0, "Pages must not share items")

    async def test_resolved_review_count(self):
        """resolved_legacy_count reflects items that no longer require review."""
        tx_unresolved = _legacy_tx("count-unresl", 100.0)
        tx_resolved = _legacy_tx(
            "count-resl",
            100.0,
            classification_scope_overrides={
                "user:user-a": {
                    "internal_transfer": False,
                    "internal_transfer_source": "user",
                }
            },
        )
        result = await _call_review_queue([tx_unresolved, tx_resolved])
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["unresolved_legacy_count"], 1)

    # --- Finding 2: overlap regression ---

    async def test_overlap_row_counted_in_both_categories(self):
        """A row that is both unresolved legacy AND ambiguous appears in both counts."""
        # overlap-out: has legacy unverified flag + plaid_account_id → ambiguous candidate
        overlap_out = _tx(
            "overlap-out", 500.0,
            plaid_transaction_id="plaid-overlap-out",
            plaid_personal_finance_detailed="TRANSFER_OUT_ACCOUNT_TRANSFER",
            is_internal_transfer=True,
            plaid_account_id="acct-out",
        )
        candidate_in_1 = _tx("overlap-in-1", -500.0, plaid_account_id="acct-in-a")
        candidate_in_2 = _tx("overlap-in-2", -500.0, plaid_account_id="acct-in-b")

        result = await _call_review_queue([overlap_out, candidate_in_1, candidate_in_2])

        ids = {item["transaction_id"] for item in result["items"]}
        self.assertIn("overlap-out", ids)
        # Both counts must include the overlap row
        self.assertGreaterEqual(result["unresolved_legacy_count"], 1)
        self.assertGreaterEqual(result["ambiguous_transfer_count"], 1)

    async def test_overlap_row_has_both_review_reasons(self):
        """An overlap row's review_reasons list contains both applicable reasons."""
        overlap_out = _tx(
            "overlap-r-out", 600.0,
            plaid_transaction_id="plaid-overlap-r-out",
            plaid_personal_finance_detailed="TRANSFER_OUT_ACCOUNT_TRANSFER",
            is_internal_transfer=True,
            plaid_account_id="acct-r-out",
        )
        candidate_in_1 = _tx("overlap-r-in-1", -600.0, plaid_account_id="acct-r-in-a")
        candidate_in_2 = _tx("overlap-r-in-2", -600.0, plaid_account_id="acct-r-in-b")

        result = await _call_review_queue([overlap_out, candidate_in_1, candidate_in_2])

        overlap_item = next(
            (i for i in result["items"] if i["transaction_id"] == "overlap-r-out"), None
        )
        self.assertIsNotNone(overlap_item, "Overlap row must appear in queue")
        self.assertIn("unresolved_legacy_transfer", overlap_item["review_reasons"])
        self.assertIn("ambiguous_transfer_candidate", overlap_item["review_reasons"])

    async def test_overlap_count_matches_canonical_ambiguous_set(self):
        """ambiguous_transfer_count counts all ambiguous rows, including legacy-overlap ones."""
        legacy_ambiguous = _tx(
            "la-out", 250.0,
            plaid_transaction_id="plaid-la-out",
            plaid_personal_finance_detailed="TRANSFER_OUT_ACCOUNT_TRANSFER",
            is_internal_transfer=True,
            plaid_account_id="la-acct-out",
        )
        candidate_1 = _tx("la-in-1", -250.0, plaid_account_id="la-acct-in-a")
        candidate_2 = _tx("la-in-2", -250.0, plaid_account_id="la-acct-in-b")

        result = await _call_review_queue([legacy_ambiguous, candidate_1, candidate_2])
        # 3 rows in ambiguous_ids: la-out, la-in-1, la-in-2
        self.assertEqual(result["ambiguous_transfer_count"], 3)
        # la-out is also unresolved legacy
        self.assertEqual(result["unresolved_legacy_count"], 1)

    async def test_mixed_reasons_counted_separately(self):
        """unresolved_legacy_count and ambiguous_transfer_count are independent."""
        legacy = _legacy_tx("mix-legacy", 100.0)
        amb_out = _tx("mix-amb-out", 200.0, plaid_account_id="ch")
        amb_in_1 = _tx("mix-amb-in-1", -200.0, plaid_account_id="sv")
        amb_in_2 = _tx("mix-amb-in-2", -200.0, plaid_account_id="jo")
        result = await _call_review_queue([legacy, amb_out, amb_in_1, amb_in_2])
        self.assertEqual(result["unresolved_legacy_count"], 1)
        self.assertEqual(result["ambiguous_transfer_count"], 3)
        self.assertEqual(result["total"], 4)

    # --- Finding 3: adversarial scope isolation ---

    async def test_scope_isolation_adversarial_mixed_users(self):
        """FilteredFakeTransactions: user-a's personal view must not expose user-b's rows."""
        tx_a = _legacy_tx("adv-iso-a", 100.0, user_id="user-a")
        tx_b = _legacy_tx("adv-iso-b", 200.0, user_id="user-b")

        # Both rows are in the backing store; only user-a's should reach the queue.
        result = await _call_review_queue([tx_a, tx_b], user_id="user-a")
        ids = {item["transaction_id"] for item in result["items"]}
        self.assertIn("adv-iso-a", ids, "User-a's unresolved row must appear")
        self.assertNotIn("adv-iso-b", ids, "User-b's row must be excluded by scope filter")

    async def test_scope_isolation_cross_scope_decision_does_not_affect_other_queue(self):
        """A resolved decision in user-b's scope must not remove user-a's row."""
        # user-a has an unresolved legacy row (no overrides)
        tx_a = _legacy_tx("cross-scope-a", 150.0, user_id="user-a")
        # user-b has a resolved row (user-b's personal scope override applied)
        tx_b = _legacy_tx(
            "cross-scope-b", 150.0,
            user_id="user-b",
            classification_scope_overrides={
                "user:user-b": {
                    "internal_transfer": False,
                    "internal_transfer_source": "user",
                }
            },
        )

        result = await _call_review_queue([tx_a, tx_b], user_id="user-a")
        ids = {item["transaction_id"] for item in result["items"]}
        # user-b's row is filtered by the scope; user-a's row must still appear
        self.assertIn("cross-scope-a", ids)
        self.assertNotIn("cross-scope-b", ids)

    async def test_scope_isolation_user_b_decision_does_not_affect_user_a_ambiguous(self):
        """User-b's External decision must not remove user-a's ambiguous rows."""
        # user-a's ambiguous outflow (no scope override)
        out_a = _tx("iso-amb-out-a", 300.0, user_id="user-a", plaid_account_id="acct-a")
        in_a1 = _tx("iso-amb-in-a1", -300.0, user_id="user-a", plaid_account_id="acct-b")
        in_a2 = _tx("iso-amb-in-a2", -300.0, user_id="user-a", plaid_account_id="acct-c")
        # user-b's outflow with an External override (different user, different scope)
        out_b = _tx(
            "iso-amb-out-b", 300.0, user_id="user-b", plaid_account_id="acct-d",
            classification_scope_overrides={
                "user:user-b": {
                    "internal_transfer": False,
                    "internal_transfer_source": "user",
                }
            },
        )

        result = await _call_review_queue([out_a, in_a1, in_a2, out_b], user_id="user-a")
        ids = {item["transaction_id"] for item in result["items"]}
        # user-a's ambiguous rows must remain in queue
        self.assertIn("iso-amb-out-a", ids)
        # user-b's row must not appear
        self.assertNotIn("iso-amb-out-b", ids)

    # --- Finding 4: real PUT update tests ---

    async def test_update_automatic_choice_resolves_legacy_and_leaves_queue(self):
        """PUT internal_transfer_override='auto' removes the legacy row from the queue."""
        scope_id = "user:user-a"
        current_user = {"id": "user-a", "email": "user-a@test.invalid", "household_id": None}

        legacy_tx = _legacy_tx("put-auto-tx", 100.0, user_id="user-a")
        post_update_tx = {
            **legacy_tx,
            "classification_scope_overrides": {
                scope_id: {
                    "internal_transfer_mode": "auto",
                    "analytics_class_mode": "auto",
                    "updated_by_user_id": "user-a",
                }
            },
        }

        # Exercise the actual PUT contract.
        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(side_effect=[legacy_tx, post_update_tx])
        mock_col.update_one = AsyncMock(return_value=MagicMock(matched_count=1))

        with patch.object(server, "db", SimpleNamespace(transactions=mock_col)):
            updated = await server.update_transaction(
                transaction_id="put-auto-tx",
                transaction_update=server.TransactionUpdate(
                    internal_transfer_override="auto",
                    analytics_class_override="auto",
                ),
                current_user=current_user,
                view_user_id="user-a",
            )

        self.assertIsNotNone(updated)
        # Confirm update_one was called (i.e. the endpoint reached the DB write)
        mock_col.update_one.assert_awaited_once()

        # Verify the post-update transaction no longer appears in the review queue.
        result = await _call_review_queue([post_update_tx], user_id="user-a")
        self.assertEqual(result["total"], 0,
            "Row with explicit Automatic decision must leave the review queue")
        self.assertEqual(result["unresolved_legacy_count"], 0)

    async def test_update_internal_plus_class_conflict_raises_400(self):
        """PUT with Internal override AND a financial class simultaneously must be rejected."""
        current_user = {"id": "user-a", "email": "user-a@test.invalid", "household_id": None}
        legacy_tx = _legacy_tx("conflict-class-tx", 100.0, user_id="user-a")

        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(return_value=legacy_tx)

        from fastapi import HTTPException
        with patch.object(server, "db", SimpleNamespace(transactions=mock_col)):
            with self.assertRaises(HTTPException) as ctx:
                await server.update_transaction(
                    transaction_id="conflict-class-tx",
                    transaction_update=server.TransactionUpdate(
                        internal_transfer_override="internal",
                        analytics_class_override="expense",  # conflicting choice
                    ),
                    current_user=current_user,
                    view_user_id="user-a",
                )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_update_scope_ownership_enforced_404(self):
        """PUT to another user's transaction must return 404 (scope ownership)."""
        current_user = {"id": "user-a", "email": "user-a@test.invalid", "household_id": None}

        # DB returns None because user_id does not match the transaction owner
        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(return_value=None)

        from fastapi import HTTPException
        with patch.object(server, "db", SimpleNamespace(transactions=mock_col)):
            with self.assertRaises(HTTPException) as ctx:
                await server.update_transaction(
                    transaction_id="other-user-tx",
                    transaction_update=server.TransactionUpdate(
                        internal_transfer_override="external",
                    ),
                    current_user=current_user,
                    view_user_id="user-a",
                )
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_update_external_override_resolves_legacy_review_count(self):
        """PUT internal_transfer_override='external' updates both queue and counts."""
        scope_id = "user:user-a"
        current_user = {"id": "user-a", "email": "user-a@test.invalid", "household_id": None}

        # Two legacy rows: one will be resolved via PUT, one stays unresolved.
        unresolved_tx = _legacy_tx("put-unresl", 50.0, user_id="user-a")
        before_put_tx = _legacy_tx("put-ext-tx", 75.0, user_id="user-a")
        post_update_tx = {
            **before_put_tx,
            "classification_scope_overrides": {
                scope_id: {
                    "internal_transfer": False,
                    "internal_transfer_source": "user",
                    "updated_by_user_id": "user-a",
                }
            },
        }

        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(side_effect=[before_put_tx, post_update_tx])
        mock_col.update_one = AsyncMock(return_value=MagicMock(matched_count=1))

        with patch.object(server, "db", SimpleNamespace(transactions=mock_col)):
            await server.update_transaction(
                transaction_id="put-ext-tx",
                transaction_update=server.TransactionUpdate(
                    internal_transfer_override="external",
                ),
                current_user=current_user,
                view_user_id="user-a",
            )

        mock_col.update_one.assert_awaited_once()

        # Post-update queue: only the unresolved row remains.
        result = await _call_review_queue([unresolved_tx, post_update_tx], user_id="user-a")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["unresolved_legacy_count"], 1)
        ids = {item["transaction_id"] for item in result["items"]}
        self.assertIn("put-unresl", ids)
        self.assertNotIn("put-ext-tx", ids)

    async def test_empty_scope_returns_empty_queue(self):
        result = await _call_review_queue([])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["items"], [])
        self.assertEqual(result["unresolved_legacy_count"], 0)
        self.assertEqual(result["ambiguous_transfer_count"], 0)

    async def test_non_review_transactions_not_included(self):
        """Ordinary expense transactions must not appear in the review queue."""
        ordinary = _tx("ordinary-purchase", 45.0, category="Restaurants", description="Coffee")
        result = await _call_review_queue([ordinary])
        self.assertEqual(result["total"], 0)

    # --- Regression: matched legacy rows must not appear in the queue ---

    async def test_matched_legacy_pair_not_in_queue(self):
        """Legacy-unverified rows that form a canonical verified pair are resolved."""
        tx_out = _legacy_tx("mleg-out", 250.0, plaid_account_id="acct-mleg-x")
        tx_in = _legacy_tx("mleg-in", -250.0, plaid_account_id="acct-mleg-y")
        result = await _call_review_queue([tx_out, tx_in])
        ids = {item["transaction_id"] for item in result["items"]}
        self.assertNotIn("mleg-out", ids, "Matched legacy outflow must not appear in queue")
        self.assertNotIn("mleg-in", ids, "Matched legacy inflow must not appear in queue")
        self.assertEqual(result["unresolved_legacy_count"], 0)
        self.assertEqual(result["total"], 0)

    async def test_unmatched_legacy_still_in_queue(self):
        """A legacy-unverified row with no counterpart must still appear in the queue."""
        tx_out = _legacy_tx("uleg-solo", 250.0, plaid_account_id="acct-uleg-only")
        result = await _call_review_queue([tx_out])
        ids = {item["transaction_id"] for item in result["items"]}
        self.assertIn("uleg-solo", ids)
        self.assertEqual(result["unresolved_legacy_count"], 1)

    async def test_matched_legacy_count_reconciles_with_summary(self):
        """classification_review_count in summary must be 0 for fully-matched legacy rows."""
        tx_out = _legacy_tx("rcleg-out", 200.0, plaid_account_id="acct-rcleg-x")
        tx_in = _legacy_tx("rcleg-in", -200.0, plaid_account_id="acct-rcleg-y")
        scoped = [
            {**tx_out, "_classification_scope_id": "user:user-a"},
            {**tx_in, "_classification_scope_id": "user:user-a"},
        ]
        analysis = server.detect_internal_transfer_analysis(scoped)
        # The pair must be matched
        self.assertIn("rcleg-out", analysis["matched_ids"])
        self.assertIn("rcleg-in", analysis["matched_ids"])
        summary = server.summarize_analytics_transactions(
            scoped, internal_transfer_analysis=analysis
        )
        self.assertEqual(
            summary["classification_review_count"], 0,
            "Matched legacy pair must not increment classification_review_count",
        )
        # Queue must also be empty
        queue = await _call_review_queue([tx_out, tx_in])
        self.assertEqual(queue["unresolved_legacy_count"], 0)

    async def test_mixed_matched_and_unmatched_legacy(self):
        """Only unmatched legacy rows count; matched pair contributes 0."""
        matched_out = _legacy_tx("mix-mleg-out", 100.0, plaid_account_id="acct-mix-a")
        matched_in = _legacy_tx("mix-mleg-in", -100.0, plaid_account_id="acct-mix-b")
        unmatched = _legacy_tx("mix-uleg-solo", 75.0)  # no plaid_account_id → no match
        result = await _call_review_queue([matched_out, matched_in, unmatched])
        self.assertEqual(result["unresolved_legacy_count"], 1)
        ids = {item["transaction_id"] for item in result["items"]}
        self.assertIn("mix-uleg-solo", ids)
        self.assertNotIn("mix-mleg-out", ids)
        self.assertNotIn("mix-mleg-in", ids)

    # --- Regression: pending exclusion in classification_review_count ---

    async def test_pending_legacy_not_counted_in_summary_by_default(self):
        """Pending legacy rows must be excluded from classification_review_count unless include_pending=True."""
        pending_legacy = _legacy_tx("pend-sum-leg", 100.0, plaid_pending=True)
        scoped = [{**pending_legacy, "_classification_scope_id": "user:user-a"}]
        analysis = server.detect_internal_transfer_analysis(scoped, include_pending=False)
        summary = server.summarize_analytics_transactions(
            scoped, internal_transfer_analysis=analysis, include_pending=False
        )
        self.assertEqual(
            summary["classification_review_count"], 0,
            "Pending legacy row must not count in classification_review_count when include_pending=False",
        )

    async def test_pending_legacy_counted_in_summary_when_requested(self):
        """Pending legacy rows are included in classification_review_count when include_pending=True."""
        pending_legacy = _legacy_tx("pend-inc-sum-leg", 100.0, plaid_pending=True)
        scoped = [{**pending_legacy, "_classification_scope_id": "user:user-a"}]
        analysis = server.detect_internal_transfer_analysis(scoped, include_pending=True)
        summary = server.summarize_analytics_transactions(
            scoped, internal_transfer_analysis=analysis, include_pending=True
        )
        self.assertEqual(
            summary["classification_review_count"], 1,
            "Pending legacy row must count in classification_review_count when include_pending=True",
        )

    async def test_pending_ambiguous_not_counted_in_summary_by_default(self):
        """Pending ambiguous rows are excluded from ambiguous_transfer_review_count by default."""
        pending_out = _tx("pend-amb-out", 200.0, plaid_account_id="pao", plaid_pending=True)
        pending_in1 = _tx("pend-amb-in1", -200.0, plaid_account_id="pai1", plaid_pending=True)
        pending_in2 = _tx("pend-amb-in2", -200.0, plaid_account_id="pai2", plaid_pending=True)
        scoped = [
            {**t, "_classification_scope_id": "user:user-a"}
            for t in [pending_out, pending_in1, pending_in2]
        ]
        analysis = server.detect_internal_transfer_analysis(scoped, include_pending=False)
        summary = server.summarize_analytics_transactions(
            scoped, internal_transfer_analysis=analysis, include_pending=False
        )
        self.assertEqual(summary["ambiguous_transfer_review_count"], 0)

    def test_pending_ambiguous_excluded_by_summarizer_even_with_inclusive_analysis(self):
        """summarize_analytics_transactions must not count pending ambiguous rows when
        include_pending=False, even when the caller supplies an analysis that was produced
        with include_pending=True and therefore has pending IDs in ambiguous_ids.

        Regression for: _count_unresolved_ambiguous not independently enforcing the
        include_pending=False contract when given a caller-supplied analysis.
        """
        # Three pending transfer-like rows on distinct synthetic account IDs.
        pending_out = _tx("reg-pend-out", 100.0, plaid_account_id="rpao", plaid_pending=True)
        pending_in1 = _tx("reg-pend-in1", -100.0, plaid_account_id="rpai1", plaid_pending=True)
        pending_in2 = _tx("reg-pend-in2", -100.0, plaid_account_id="rpai2", plaid_pending=True)
        scoped = [
            {**t, "_classification_scope_id": "user:user-a"}
            for t in [pending_out, pending_in1, pending_in2]
        ]
        # Produce an inclusive analysis: pending rows ARE in ambiguous_ids.
        inclusive_analysis = server.detect_internal_transfer_analysis(scoped, include_pending=True)
        self.assertGreater(
            len(inclusive_analysis["ambiguous_ids"]), 0,
            "Inclusive analysis must capture pending ambiguous IDs for this regression to be valid",
        )
        # Now call the summarizer with include_pending=False but supply the inclusive analysis.
        # The summarizer must still exclude the pending rows — not trust the caller-supplied ids.
        summary_exclude = server.summarize_analytics_transactions(
            scoped,
            internal_transfer_analysis=inclusive_analysis,
            include_pending=False,
        )
        self.assertEqual(
            summary_exclude["ambiguous_transfer_review_count"],
            0,
            "summarizer with include_pending=False must return 0 even when analysis was produced "
            "with include_pending=True and carries pending ambiguous IDs",
        )
        # Conversely, include_pending=True must count those same rows.
        summary_include = server.summarize_analytics_transactions(
            scoped,
            internal_transfer_analysis=inclusive_analysis,
            include_pending=True,
        )
        self.assertGreater(
            summary_include["ambiguous_transfer_review_count"],
            0,
            "summarizer with include_pending=True must count pending ambiguous rows",
        )


# ---------------------------------------------------------------------------
# Integration tests: dashboard/monthly counts reconcile with queue counts
# ---------------------------------------------------------------------------


class SummarizeAmbiguousCountReconciliationTests(unittest.IsolatedAsyncioTestCase):
    """After a user decision, summarize_analytics_transactions ambiguous count must
    match the review queue ambiguous count so the dashboard notice stays coherent."""

    def _scope_txs(self, transactions, scope_id="user:user-a"):
        """Attach _classification_scope_id to all transactions (mimics load_analytics_transactions)."""
        return [{**tx, "_classification_scope_id": scope_id} for tx in transactions]

    def test_unresolved_ambiguous_counted_before_decision(self):
        """Ambiguous rows with no decision appear in both queue and summary counts."""
        outflow = _tx("rc-out", 300.0, plaid_account_id="acct-ch")
        inflow_a = _tx("rc-in-a", -300.0, plaid_account_id="acct-sv")
        inflow_b = _tx("rc-in-b", -300.0, plaid_account_id="acct-jo")
        scoped = self._scope_txs([outflow, inflow_a, inflow_b])
        analysis = server.detect_internal_transfer_analysis(scoped)
        summary = server.summarize_analytics_transactions(scoped, internal_transfer_analysis=analysis)
        # All three rows are ambiguous; none are resolved
        self.assertEqual(summary["ambiguous_transfer_review_count"], 3)

    def test_automatic_decision_removes_from_summary_count(self):
        """After an Automatic decision the summary count drops to match the queue count."""
        outflow = _tx(
            "rc-auto-out", 400.0,
            plaid_account_id="acct-ch",
            classification_scope_overrides={
                "user:user-a": {"internal_transfer_mode": "auto"}
            },
        )
        inflow_a = _tx("rc-auto-in-a", -400.0, plaid_account_id="acct-sv")
        inflow_b = _tx("rc-auto-in-b", -400.0, plaid_account_id="acct-jo")
        scoped = self._scope_txs([outflow, inflow_a, inflow_b])
        analysis = server.detect_internal_transfer_analysis(scoped)
        summary = server.summarize_analytics_transactions(scoped, internal_transfer_analysis=analysis)
        # The row with an Automatic decision is resolved; the two inflows have no decision
        self.assertEqual(summary["ambiguous_transfer_review_count"], 2)

    def test_internal_override_removes_from_summary_count(self):
        """After an Internal override the summary count drops to match the queue count."""
        outflow = _tx(
            "rc-int-out", 500.0,
            plaid_account_id="acct-ch",
            classification_scope_overrides={
                "user:user-a": {
                    "internal_transfer": True,
                    "internal_transfer_source": "user",
                }
            },
        )
        inflow_a = _tx("rc-int-in-a", -500.0, plaid_account_id="acct-sv")
        inflow_b = _tx("rc-int-in-b", -500.0, plaid_account_id="acct-jo")
        scoped = self._scope_txs([outflow, inflow_a, inflow_b])
        analysis = server.detect_internal_transfer_analysis(scoped)
        summary = server.summarize_analytics_transactions(scoped, internal_transfer_analysis=analysis)
        # outflow has Internal override → resolved; two inflows remain
        self.assertEqual(summary["ambiguous_transfer_review_count"], 2)

    def test_external_override_removes_from_summary_count(self):
        """After an External override the row exits transfer analysis; summary count drops to 0."""
        # An External override (internal_transfer: False) causes is_transfer_like_transaction
        # to return False, removing the outflow from the transfer analysis entirely.
        # Without the outflow, neither inflow forms any edges, so ambiguous_ids is empty.
        outflow = _tx(
            "rc-ext-out", 600.0,
            plaid_account_id="acct-ch",
            classification_scope_overrides={
                "user:user-a": {
                    "internal_transfer": False,
                    "internal_transfer_source": "user",
                }
            },
        )
        inflow = _tx("rc-ext-in", -600.0, plaid_account_id="acct-sv")
        inflow_b = _tx("rc-ext-in-b", -600.0, plaid_account_id="acct-jo")
        scoped = self._scope_txs([outflow, inflow, inflow_b])
        analysis = server.detect_internal_transfer_analysis(scoped)
        summary = server.summarize_analytics_transactions(scoped, internal_transfer_analysis=analysis)
        # outflow exited transfer analysis → no edges → no ambiguous rows
        self.assertEqual(summary["ambiguous_transfer_review_count"], 0)

    async def test_summary_and_queue_agree_after_automatic_decision(self):
        """summary ambiguous_transfer_review_count equals queue ambiguous_transfer_count."""
        outflow = _tx(
            "agree-auto-out", 350.0,
            plaid_account_id="ag-ch",
            classification_scope_overrides={
                "user:user-a": {"internal_transfer_mode": "auto"}
            },
        )
        inflow_a = _tx("agree-auto-in-a", -350.0, plaid_account_id="ag-sv")
        inflow_b = _tx("agree-auto-in-b", -350.0, plaid_account_id="ag-jo")
        scoped = self._scope_txs([outflow, inflow_a, inflow_b])

        analysis = server.detect_internal_transfer_analysis(scoped)
        summary = server.summarize_analytics_transactions(scoped, internal_transfer_analysis=analysis)

        queue = await _call_review_queue([outflow, inflow_a, inflow_b])

        self.assertEqual(
            summary["ambiguous_transfer_review_count"],
            queue["ambiguous_transfer_count"],
            "Dashboard/monthly ambiguous count must equal queue count after Automatic decision",
        )

    async def test_summary_and_queue_agree_after_internal_decision(self):
        """summary ambiguous_transfer_review_count equals queue ambiguous_transfer_count."""
        outflow = _tx(
            "agree-int-out", 450.0,
            plaid_account_id="ai-ch",
            classification_scope_overrides={
                "user:user-a": {
                    "internal_transfer": True,
                    "internal_transfer_source": "user",
                }
            },
        )
        inflow_a = _tx("agree-int-in-a", -450.0, plaid_account_id="ai-sv")
        inflow_b = _tx("agree-int-in-b", -450.0, plaid_account_id="ai-jo")
        scoped = self._scope_txs([outflow, inflow_a, inflow_b])

        analysis = server.detect_internal_transfer_analysis(scoped)
        summary = server.summarize_analytics_transactions(scoped, internal_transfer_analysis=analysis)

        queue = await _call_review_queue([outflow, inflow_a, inflow_b])

        self.assertEqual(
            summary["ambiguous_transfer_review_count"],
            queue["ambiguous_transfer_count"],
            "Dashboard/monthly ambiguous count must equal queue count after Internal decision",
        )

    def test_no_ambiguous_ids_returns_zero(self):
        """summarize returns zero when transfer analysis found no ambiguous rows."""
        ordinary = _tx("no-amb-exp", 45.0, category="Restaurants")
        scoped = self._scope_txs([ordinary])
        analysis = server.detect_internal_transfer_analysis(scoped)
        summary = server.summarize_analytics_transactions(scoped, internal_transfer_analysis=analysis)
        self.assertEqual(summary["ambiguous_transfer_review_count"], 0)

    async def test_matched_legacy_summary_and_queue_reconcile(self):
        """classification_review_count and queue unresolved_legacy_count both = 0 for matched pairs."""
        tx_out = _legacy_tx("qsync-out", 180.0, plaid_account_id="qs-acct-x")
        tx_in = _legacy_tx("qsync-in", -180.0, plaid_account_id="qs-acct-y")
        scoped = self._scope_txs([tx_out, tx_in])
        analysis = server.detect_internal_transfer_analysis(scoped)
        summary = server.summarize_analytics_transactions(scoped, internal_transfer_analysis=analysis)
        queue = await _call_review_queue([tx_out, tx_in])
        self.assertEqual(
            summary["classification_review_count"],
            queue["unresolved_legacy_count"],
            "classification_review_count and queue unresolved_legacy_count must agree for matched pair",
        )
        self.assertEqual(summary["classification_review_count"], 0)

    async def test_pending_legacy_excluded_from_summary_and_queue(self):
        """Pending legacy rows excluded from both summary count and queue by default."""
        pending = _legacy_tx("pend-sync-leg", 90.0, plaid_pending=True)
        scoped = self._scope_txs([pending])
        analysis = server.detect_internal_transfer_analysis(scoped, include_pending=False)
        summary = server.summarize_analytics_transactions(
            scoped, internal_transfer_analysis=analysis, include_pending=False
        )
        queue = await _call_review_queue([pending], include_pending=False)
        self.assertEqual(summary["classification_review_count"], 0)
        self.assertEqual(queue["unresolved_legacy_count"], 0)

    async def test_pending_legacy_included_in_both_when_requested(self):
        """Pending legacy rows counted in both summary and queue when include_pending=True."""
        pending = _legacy_tx("pend-inc-sync-leg", 90.0, plaid_pending=True)
        scoped = self._scope_txs([pending])
        analysis = server.detect_internal_transfer_analysis(scoped, include_pending=True)
        summary = server.summarize_analytics_transactions(
            scoped, internal_transfer_analysis=analysis, include_pending=True
        )
        queue = await _call_review_queue([pending], include_pending=True)
        self.assertEqual(
            summary["classification_review_count"],
            queue["unresolved_legacy_count"],
            "Pending legacy row: summary and queue must agree when include_pending=True",
        )
        self.assertEqual(summary["classification_review_count"], 1)

    def test_overlap_row_summary_counts_independently(self):
        """An unmatched legacy+ambiguous row increments both review counts independently."""
        # Legacy-flagged outflow with no unique counterpart (two candidates → ambiguous)
        overlap_out = _tx(
            "ov-sum-out", 400.0,
            plaid_transaction_id="plaid-ov-sum-out",
            plaid_personal_finance_detailed="TRANSFER_OUT_ACCOUNT_TRANSFER",
            is_internal_transfer=True,
            plaid_account_id="ov-acct-out",
        )
        cand1 = _tx("ov-sum-in-1", -400.0, plaid_account_id="ov-acct-in-a")
        cand2 = _tx("ov-sum-in-2", -400.0, plaid_account_id="ov-acct-in-b")
        scoped = self._scope_txs([overlap_out, cand1, cand2])
        analysis = server.detect_internal_transfer_analysis(scoped)
        # overlap_out is ambiguous (two candidates), not matched
        self.assertIn("ov-sum-out", analysis["ambiguous_ids"])
        self.assertNotIn("ov-sum-out", analysis["matched_ids"])
        summary = server.summarize_analytics_transactions(scoped, internal_transfer_analysis=analysis)
        # unresolved legacy count must be 1 (the unmatched legacy-flagged row)
        self.assertEqual(summary["classification_review_count"], 1)
        # ambiguous count must include all 3 ambiguous rows
        self.assertEqual(summary["ambiguous_transfer_review_count"], 3)


if __name__ == "__main__":
    unittest.main()
