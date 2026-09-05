# Copyright (c) 2026, Sriragul and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.utils import now, get_datetime_str


# Fields to sync per DocType (excludes Section/Column Breaks, computed fields,
# and fields managed by the server like `name`, `owner`, `modified_by`).
# `modified` and `client_id` are always included implicitly.

ACCOUNT_FIELDS = [
    "account_name", "account_type", "currency", "icon", "color",
    "opening_balance", "current_balance", "is_archived", "client_id",
]

CATEGORY_FIELDS = [
    "category_name", "category_type", "parent_category", "icon", "color",
    "is_archived", "sort_order", "client_id",
]

TAG_FIELDS = [
    "tag_name", "emoji", "color", "is_archived", "sort_order", "client_id",
]

TRANSACTION_FIELDS = [
    "date", "transaction_type", "account", "transfer_to_account",
    "amount", "category", "note", "receipt", "is_archived", "is_deleted",
    "client_id",
]


def _get_owner():
    """Return the current user's name for owner-scoped queries."""
    return frappe.session.user


def _parse_since(since):
    """Normalize the `since` parameter. Returns None for full sync."""
    if not since:
        return None
    return str(since)


def _resolve_ref(value, ref_map, owner):
    """Resolve a field value that may be a same-batch client_id reference.

    If `value` is a dict with a "client_id" key, look it up in ref_map
    (populated from already-processed records in this batch) or in the
    database. If `value` is a plain string, return it as-is (already a
    server name).

    Returns (resolved_name, error_string_or_None).
    """
    if not value:
        return value, None

    if isinstance(value, dict) and "client_id" in value:
        cid = value["client_id"]
        # Check the in-batch resolution map first
        if cid in ref_map:
            return ref_map[cid], None
        # Check the database (existing record with this client_id)
        for dt in ["Account", "Category", "Tag"]:
            existing = frappe.db.get_value(dt, {"client_id": cid, "owner": owner}, "name")
            if existing:
                return existing, None
        return None, f"client_id '{cid}' not found in batch or database"

    # Plain string — already a server name
    return str(value), None


def _push_doctype(doctype, records, field_list, owner, ref_map,
                  reference_fields=None):
    """Process a batch of records for a single DocType.

    `ref_map`: dict mapping client_id -> server_name, updated as records
               are created/updated.
    `reference_fields`: list of field names whose values may be same-batch
                        client_id references (dicts) that need resolution.

    Returns (accepted, rejected) lists.
    """
    accepted = []
    rejected = []
    reference_fields = reference_fields or []

    for rec in (records or []):
        client_id = rec.get("client_id")
        incoming_modified = rec.get("modified")

        # Idempotency check: if client_id exists, compare modified timestamps
        if client_id:
            existing_name = frappe.db.get_value(
                doctype, {"client_id": client_id, "owner": owner}, "name"
            )
            if existing_name:
                server_modified = get_datetime_str(
                    frappe.db.get_value(doctype, existing_name, "modified")
                )
                # If incoming is not newer, reject as stale
                if not incoming_modified or incoming_modified <= server_modified:
                    rejected.append({
                        "client_id": client_id,
                        "reason": "stale",
                        "server_modified": server_modified,
                    })
                    continue

                # Update existing record — resolve references first
                doc = frappe.get_doc(doctype, existing_name)
                for field in field_list:
                    if field in rec and field != "client_id":
                        val = rec[field]
                        if field in reference_fields:
                            val, err = _resolve_ref(val, ref_map, owner)
                            if err:
                                rejected.append({
                                    "client_id": client_id,
                                    "reason": "unresolved reference",
                                    "detail": err,
                                })
                                break
                        doc.set(field, val)
                else:
                    # No break — all references resolved
                    doc.save(ignore_permissions=True)
                    accepted.append({
                        "client_id": client_id,
                        "name": doc.name,
                    })
                    ref_map[client_id] = doc.name
                continue

            # Create new record — resolve references first
            doc = frappe.get_doc({"doctype": doctype})
            for field in field_list:
                if field in rec and field != "client_id":
                    val = rec[field]
                    if field in reference_fields:
                        val, err = _resolve_ref(val, ref_map, owner)
                        if err:
                            rejected.append({
                                "client_id": client_id,
                                "reason": "unresolved reference",
                                "detail": err,
                            })
                            break
                    doc.set(field, val)
            else:
                if client_id:
                    doc.set("client_id", client_id)
                doc.insert(ignore_permissions=True)
                accepted.append({
                    "client_id": client_id,
                    "name": doc.name,
                })
                ref_map[client_id] = doc.name
        else:
            # No client_id — just create (still resolve references)
            doc = frappe.get_doc({"doctype": doctype})
            for field in field_list:
                if field in rec:
                    val = rec[field]
                    if field in reference_fields:
                        val, err = _resolve_ref(val, ref_map, owner)
                        if err:
                            rejected.append({
                                "client_id": None,
                                "reason": "unresolved reference",
                                "detail": err,
                            })
                            break
                    doc.set(field, val)
            else:
                doc.insert(ignore_permissions=True)
                accepted.append({
                    "client_id": None,
                    "name": doc.name,
                })

    return accepted, rejected


def _push_transactions(records, owner, ref_map):
    """Process Transaction records, including child table (tags).

    `ref_map`: dict mapping client_id -> server_name for same-batch resolution.

    Returns (accepted, rejected) lists.
    """
    accepted = []
    rejected = []

    for rec in (records or []):
        client_id = rec.get("client_id")
        incoming_modified = rec.get("modified")

        # Resolve references for account, category, transfer_to_account
        resolved = {}
        ref_fields = {"account", "category", "transfer_to_account"}
        ref_error = False
        for field in ref_fields:
            if field in rec:
                val, err = _resolve_ref(rec[field], ref_map, owner)
                if err:
                    rejected.append({
                        "client_id": client_id,
                        "reason": "unresolved reference",
                        "detail": err,
                    })
                    ref_error = True
                    break
                resolved[field] = val
        if ref_error:
            continue

        # Resolve tags child table references
        resolved_tags = []
        if "tags" in rec:
            for tag_ref in rec["tags"]:
                if isinstance(tag_ref, dict) and "client_id" in tag_ref:
                    val, err = _resolve_ref(tag_ref, ref_map, owner)
                    if err:
                        rejected.append({
                            "client_id": client_id,
                            "reason": "unresolved reference",
                            "detail": err,
                        })
                        ref_error = True
                        break
                    resolved_tags.append(val)
                else:
                    resolved_tags.append(tag_ref)
        if ref_error:
            continue

        # Idempotency check
        if client_id:
            existing_name = frappe.db.get_value(
                "Transaction", {"client_id": client_id, "owner": owner}, "name"
            )
            if existing_name:
                server_modified = get_datetime_str(
                    frappe.db.get_value("Transaction", existing_name, "modified")
                )
                if not incoming_modified or incoming_modified <= server_modified:
                    rejected.append({
                        "client_id": client_id,
                        "reason": "stale",
                        "server_modified": server_modified,
                    })
                    continue

                # Update existing transaction
                doc = frappe.get_doc("Transaction", existing_name)
                for field in TRANSACTION_FIELDS:
                    if field in rec and field != "client_id" and field != "tags":
                        doc.set(field, resolved.get(field, rec[field]))
                _sync_transaction_tags(doc, resolved_tags)
                doc.save(ignore_permissions=True)
                accepted.append({
                    "client_id": client_id,
                    "name": doc.name,
                })
                ref_map[client_id] = doc.name
            else:
                # Create new transaction
                doc = frappe.get_doc({"doctype": "Transaction"})
                for field in TRANSACTION_FIELDS:
                    if field in rec and field != "tags":
                        doc.set(field, resolved.get(field, rec[field]))
                if client_id:
                    doc.set("client_id", client_id)
                _sync_transaction_tags(doc, resolved_tags)
                doc.insert(ignore_permissions=True)
                accepted.append({
                    "client_id": client_id,
                    "name": doc.name,
                })
                ref_map[client_id] = doc.name
        else:
            # No client_id — just create
            doc = frappe.get_doc({"doctype": "Transaction"})
            for field in TRANSACTION_FIELDS:
                if field in rec and field != "tags":
                    doc.set(field, resolved.get(field, rec[field]))
            _sync_transaction_tags(doc, resolved_tags)
            doc.insert(ignore_permissions=True)
            accepted.append({
                "client_id": None,
                "name": doc.name,
            })

    return accepted, rejected


def _sync_transaction_tags(doc, tag_names):
    """Replace the transaction's tags with the given list of tag names."""
    doc.set("tags", [])
    for tag_name in tag_names:
        if tag_name:
            doc.append("tags", {"tag": tag_name})


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------

@frappe.whitelist()
def pull(since=None):
    """Return all records modified after `since` for the four core DocTypes.

    If `since` is omitted or null, returns every record (full initial sync).

    Transaction records with is_deleted=1 ARE included -- the client needs them
    to know a record was deleted locally.

    `server_time` is captured BEFORE any queries run to avoid a race condition
    where a record modified during the pull window gets missed on the next
    incremental sync.
    """
    since = _parse_since(since)
    owner = _get_owner()
    server_time = get_datetime_str(now())

    # -- Accounts --
    filters = {"owner": owner}
    if since:
        filters["modified"] = (">", since)
    accounts = frappe.get_list(
        "Account", filters=filters, fields=ACCOUNT_FIELDS + ["modified"],
        limit_page_length=0, ignore_permissions=True,
    )

    # -- Categories --
    filters = {"owner": owner}
    if since:
        filters["modified"] = (">", since)
    categories = frappe.get_list(
        "Category", filters=filters, fields=CATEGORY_FIELDS + ["modified"],
        limit_page_length=0, ignore_permissions=True,
    )

    # -- Tags --
    filters = {"owner": owner}
    if since:
        filters["modified"] = (">", since)
    tags = frappe.get_list(
        "Tag", filters=filters, fields=TAG_FIELDS + ["modified"],
        limit_page_length=0, ignore_permissions=True,
    )

    # -- Transactions (INCLUDES is_deleted=1) --
    filters = {"owner": owner}
    if since:
        filters["modified"] = (">", since)
    transactions_raw = frappe.get_list(
        "Transaction", filters=filters,
        fields=TRANSACTION_FIELDS + ["name", "modified"],
        limit_page_length=0, ignore_permissions=True,
    )

    # Attach tags child table rows to each transaction
    transactions = []
    for t in transactions_raw:
        tag_rows = frappe.get_list(
            "TransactionTag",
            filters={"parent": t["name"], "parenttype": "Transaction"},
            fields=["tag"],
            limit_page_length=0,
            ignore_permissions=True,
        )
        t["tags"] = [r["tag"] for r in tag_rows]
        t["modified"] = get_datetime_str(t["modified"])
        transactions.append(t)

    # Format modified for other DocTypes
    for rec in accounts + categories + tags:
        rec["modified"] = get_datetime_str(rec["modified"])

    return {
        "server_time": server_time,
        "accounts": accounts,
        "categories": categories,
        "tags": tags,
        "transactions": transactions,
    }


@frappe.whitelist()
def push(accounts=None, categories=None, tags=None, transactions=None):
    """Batch create/update records across all four DocTypes.

    Processes records in dependency order:
    1. Accounts and Tags (no inter-dependencies)
    2. Categories (may reference parent_category)
    3. Transactions (may reference account, category, transfer_to_account, tags)

    A resolution map (client_id -> server_name) is built progressively as
    each record is created, so same-batch cross-references are resolved
    correctly.

    Each record should include `client_id` (required for offline-created
    records) and all field values. The server runs the normal DocType
    controller validate() on every record — business rules are enforced.

    Cross-record references use this format:
    - Already-synced record: plain string (the server name)
    - Same-batch record: {"client_id": "<client_id>"}

    Conflict resolution: last-write-wins, determined by `modified` timestamps.
    """
    owner = _get_owner()

    # Resolution map: client_id -> server_name, populated progressively
    ref_map = {}

    # Step 1: Accounts and Tags (no dependencies on each other)
    accepted_accounts, rejected_accounts = _push_doctype(
        "Account", accounts, ACCOUNT_FIELDS, owner, ref_map,
    )
    accepted_tags, rejected_tags = _push_doctype(
        "Tag", tags, TAG_FIELDS, owner, ref_map,
    )

    # Step 2: Categories (may reference parent_category — another Category)
    accepted_categories, rejected_categories = _push_doctype(
        "Category", categories, CATEGORY_FIELDS, owner, ref_map,
        reference_fields=["parent_category"],
    )

    # Step 3: Transactions (may reference account, category, transfer_to_account, tags)
    accepted_transactions, rejected_transactions = _push_transactions(
        transactions, owner, ref_map,
    )

    return {
        "accepted": {
            "accounts": accepted_accounts,
            "categories": accepted_categories,
            "tags": accepted_tags,
            "transactions": accepted_transactions,
        },
        "rejected": {
            "accounts": rejected_accounts,
            "categories": rejected_categories,
            "tags": rejected_tags,
            "transactions": rejected_transactions,
        },
    }
