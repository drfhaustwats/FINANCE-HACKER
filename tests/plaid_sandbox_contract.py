"""Opt-in Plaid Sandbox contract test.

Creates an ephemeral Sandbox Item, waits for real Transactions payloads, checks
the SDK contract used by LifeTracker, and always removes the Item. It never
prints tokens, identifiers, descriptions, amounts, or account details.

Run from the repository root with the backend environment configured for
Sandbox:

    python tests/plaid_sandbox_contract.py
"""

import time

from bson import BSON
from backend import server
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.products import Products
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.sandbox_public_token_create_request_options import SandboxPublicTokenCreateRequestOptions
from plaid.model.transactions_refresh_request import TransactionsRefreshRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest


def run_contract_test() -> dict:
    if server.PLAID_ENV != "sandbox":
        raise RuntimeError("Refusing to run: PLAID_ENV must be sandbox.")
    if not server.plaid_enabled():
        raise RuntimeError("Plaid Sandbox and token encryption must be configured.")

    access_token = None
    try:
        created = server.plaid_client.sandbox_public_token_create(
            SandboxPublicTokenCreateRequest(
                institution_id="ins_109508",
                initial_products=[Products("transactions")],
                options=SandboxPublicTokenCreateRequestOptions(
                    override_username="user_transactions_dynamic",
                    override_password="pass_good",
                ),
            )
        )
        exchanged = server.plaid_client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=created.public_token)
        )
        access_token = exchanged.access_token

        accounts_response = server.plaid_client.accounts_get(
            server.AccountsGetRequest(access_token=access_token)
        )
        account_snapshots = [
            server.build_account_snapshot(account)
            for account in list(accounts_response.accounts or [])
        ]
        for account_snapshot in account_snapshots:
            BSON.encode(account_snapshot)

        cursor = None
        pages = 0
        added_rows = []
        modified_count = 0
        removed_count = 0
        poll_attempts = 0

        for poll_attempts in range(1, 11):
            while True:
                request_values = {"access_token": access_token, "count": 500}
                if cursor:
                    request_values["cursor"] = cursor
                response = server.plaid_client.transactions_sync(
                    TransactionsSyncRequest(**request_values)
                )
                pages += 1
                added_rows.extend(list(response.added or []))
                modified_count += len(response.modified or [])
                removed_count += len(response.removed or [])
                cursor = response.next_cursor
                if not response.has_more:
                    break

            if added_rows:
                break
            if poll_attempts == 1:
                try:
                    server.plaid_client.transactions_refresh(
                        TransactionsRefreshRequest(access_token=access_token)
                    )
                except Exception:
                    # Refresh is an optional add-on; normal /sync polling remains valid.
                    pass
            time.sleep(3)

        if not added_rows:
            raise AssertionError("Plaid Sandbox did not return a transaction payload in time.")

        sample = added_rows[0]
        contract = {
            "sandbox_payload_received": True,
            "poll_attempts": poll_attempts,
            "pages": pages,
            "account_snapshots_bson_safe": bool(account_snapshots),
            "added_count": len(added_rows),
            "modified_count": modified_count,
            "removed_count": removed_count,
            "transaction_id_present": bool(getattr(sample, "transaction_id", None)),
            "date_present": bool(getattr(sample, "date", None)),
            "amount_is_numeric": isinstance(getattr(sample, "amount", None), (int, float)),
            "personal_finance_category_present": bool(
                getattr(sample, "personal_finance_category", None)
            ),
            "cursor_present": bool(cursor),
        }
        required_checks = (
            "transaction_id_present",
            "date_present",
            "amount_is_numeric",
            "personal_finance_category_present",
            "cursor_present",
            "account_snapshots_bson_safe",
        )
        if not all(contract[field] for field in required_checks):
            raise AssertionError(f"Plaid transaction contract mismatch: {contract}")
        return contract
    finally:
        try:
            if access_token:
                server.plaid_client.item_remove(ItemRemoveRequest(access_token=access_token))
        finally:
            server.client.close()


if __name__ == "__main__":
    print(run_contract_test())
