"""Opt-in end-to-end signed Plaid webhook contract test.

Requires a temporary public HTTPS URL that routes to the local backend's
``/api/plaid/webhook`` endpoint. The script creates only Sandbox data, reports
counts/booleans, and removes the remote Item and exact local test records.
"""

import asyncio
import os
import uuid
from datetime import datetime

from backend import server
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.products import Products
from plaid.model.sandbox_item_fire_webhook_request import SandboxItemFireWebhookRequest
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.sandbox_public_token_create_request_options import SandboxPublicTokenCreateRequestOptions
from plaid.model.transactions_refresh_request import TransactionsRefreshRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest


async def run_signed_webhook_contract() -> dict:
    if server.PLAID_ENV != "sandbox" or not server.plaid_enabled():
        raise RuntimeError("Refusing to run: Plaid Sandbox is not safely configured.")
    webhook_url = os.environ.get("PLAID_SANDBOX_WEBHOOK_URL", "")
    if not webhook_url.startswith("https://") or not webhook_url.endswith("/api/plaid/webhook"):
        raise RuntimeError("PLAID_SANDBOX_WEBHOOK_URL must be the temporary HTTPS webhook endpoint.")

    user_id = "contract-user-" + uuid.uuid4().hex
    connection_id = "contract-connection-" + uuid.uuid4().hex
    access_token = None
    item_id = None
    try:
        created = await asyncio.to_thread(
            server.plaid_client.sandbox_public_token_create,
            SandboxPublicTokenCreateRequest(
                institution_id="ins_109508",
                initial_products=[Products("transactions")],
                options=SandboxPublicTokenCreateRequestOptions(
                    webhook=webhook_url,
                    override_username="user_transactions_dynamic",
                    override_password="pass_good",
                ),
            ),
        )
        exchanged = await asyncio.to_thread(
            server.plaid_client.item_public_token_exchange,
            ItemPublicTokenExchangeRequest(public_token=created.public_token),
        )
        access_token = exchanged.access_token
        item_id = exchanged.item_id
        initial_sync = await asyncio.to_thread(
            server.plaid_client.transactions_sync,
            TransactionsSyncRequest(access_token=access_token, count=500),
        )

        await server.db.users.insert_one(
            {
                "id": user_id,
                "email": f"{user_id}@example.invalid",
                "full_name": "Plaid Contract Test",
                "created_at": datetime.utcnow(),
            }
        )
        await server.db.plaid_items.insert_one(
            {
                "id": connection_id,
                "user_id": user_id,
                "item_id": item_id,
                "access_token_ciphertext": server.encrypt_plaid_access_token(access_token),
                "token_encrypted_at": datetime.utcnow(),
                "cursor": getattr(initial_sync, "next_cursor", None),
                "status": "active",
                "accounts": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )

        try:
            await asyncio.to_thread(
                server.plaid_client.transactions_refresh,
                TransactionsRefreshRequest(access_token=access_token),
            )
        except Exception:
            pass
        await asyncio.sleep(4)

        event = None
        connection = None
        transaction_count = 0
        for _ in range(3):
            await asyncio.to_thread(
                server.plaid_client.sandbox_item_fire_webhook,
                SandboxItemFireWebhookRequest(
                    access_token=access_token,
                    webhook_code="SYNC_UPDATES_AVAILABLE",
                ),
            )
            for _ in range(8):
                event = await server.db.plaid_webhook_events.find_one(
                    {"item_id": item_id, "webhook_code": "SYNC_UPDATES_AVAILABLE"},
                    sort=[("received_at", -1)],
                )
                transaction_count = await server.db.transactions.count_documents({"user_id": user_id})
                connection = await server.db.plaid_items.find_one(
                    {"id": connection_id, "user_id": user_id}
                )
                if (
                    event
                    and event.get("status") == "processed"
                    and transaction_count > 0
                    and connection
                    and connection.get("last_successful_sync")
                ):
                    break
                await asyncio.sleep(2)
            if transaction_count > 0 and event and event.get("status") == "processed":
                break

        if not event or event.get("status") != "processed":
            raise AssertionError("A real signed Plaid webhook was not processed.")
        if transaction_count <= 0 or not connection or not connection.get("last_successful_sync"):
            raise AssertionError("The signed webhook did not drive transaction synchronization.")

        return {
            "real_signed_webhook_processed": True,
            "webhook_status": event.get("status"),
            "transactions_synced": transaction_count,
            "cursor_persisted": bool(connection.get("cursor")),
            "accounts_persisted": len(connection.get("accounts") or []),
            "encrypted_token_stored": bool(connection.get("access_token_ciphertext")),
            "plaintext_token_absent": "access_token" not in connection,
        }
    finally:
        if access_token:
            try:
                await asyncio.to_thread(
                    server.plaid_client.item_remove,
                    ItemRemoveRequest(access_token=access_token),
                )
            except Exception:
                pass
        await server.db.transactions.delete_many({"user_id": user_id})
        if item_id:
            await server.db.plaid_webhook_events.delete_many({"item_id": item_id})
        await server.db.plaid_items.delete_many({"id": connection_id, "user_id": user_id})
        await server.db.users.delete_many({"id": user_id})
        server.client.close()


if __name__ == "__main__":
    print(asyncio.run(run_signed_webhook_contract()))
