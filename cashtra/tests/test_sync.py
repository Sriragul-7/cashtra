import frappe
from cashtra.api.sync import pull, push

def execute():
    frappe.set_user("Administrator")

    # Clean slate
    frappe.db.sql("DELETE FROM `tabTransactionTag`")
    frappe.db.sql("DELETE FROM `tabTransaction`")
    frappe.db.sql("DELETE FROM `tabAccount`")
    frappe.db.sql("DELETE FROM `tabCategory`")
    frappe.db.sql("DELETE FROM `tabTag`")
    frappe.db.commit()

    # Create prerequisite data
    cat_exp = frappe.get_doc({
        "doctype": "Category",
        "category_name": "Food",
        "category_type": "Expense",
        "parent_category": "",
        "category_icon": "",
        "category_emoji": "",
        "category_color": "#000",
        "sort_order": 0,
    })
    cat_exp.insert(ignore_permissions=True)
    frappe.db.commit()

    tag = frappe.get_doc({
        "doctype": "Tag",
        "tag_name": "groceries",
        "emoji": "",
        "color": "#000",
        "sort_order": 0,
    })
    tag.insert(ignore_permissions=True)
    frappe.db.commit()

    acc = frappe.get_doc({
        "doctype": "Account",
        "account_name": "Test Acc",
        "account_type": "Cash",
        "currency": "INR",
        "opening_balance": 500,
    })
    acc.insert(ignore_permissions=True)
    frappe.db.commit()

    txn = frappe.get_doc({
        "doctype": "Transaction",
        "transaction_type": "Expense",
        "account": "Test Acc",
        "category": cat_exp.name,
        "amount": 50,
        "date": "2026-09-05",
        "note": "milk",
    })
    txn.insert(ignore_permissions=True)
    frappe.db.commit()

    # ── Test a: Full pull with since=None ──
    print("=" * 60)
    print("TEST a: Full pull (since=None)")
    print("=" * 60)
    result_a = pull(since=None)
    print(f"  accounts: {len(result_a['accounts'])} records")
    print(f"  categories: {len(result_a['categories'])} records")
    print(f"  tags: {len(result_a['tags'])} records")
    print(f"  transactions: {len(result_a['transactions'])} records")
    print(f"  server_time: {result_a['server_time']}")
    assert len(result_a['accounts']) >= 1, "FAIL a: no accounts"
    assert len(result_a['categories']) >= 1, "FAIL a: no categories"
    assert len(result_a['tags']) >= 1, "FAIL a: no tags"
    assert len(result_a['transactions']) >= 1, "FAIL a: no transactions"
    server_time_a = result_a['server_time']
    print("  PASS\n")

    # ── Test b: Push new Account with client_id, no name ──
    print("=" * 60)
    print("TEST b: Push new Account with client_id")
    print("=" * 60)
    result_b = push(accounts=[{
        "account_name": "Offline Wallet",
        "account_type": "Wallet",
        "currency": "INR",
        "opening_balance": 200,
        "client_id": "test-uuid-001",
        "modified": "2026-09-05 12:00:00",
    }])
    print(f"  accepted accounts: {result_b['accepted']['accounts']}")
    print(f"  rejected accounts: {result_b['rejected']['accounts']}")
    assert len(result_b['accepted']['accounts']) == 1, "FAIL b: not accepted"
    assert result_b['accepted']['accounts'][0]['client_id'] == "test-uuid-001", "FAIL b: wrong client_id"
    assert result_b['accepted']['accounts'][0]['name'] is not None, "FAIL b: no server name"
    print("  PASS\n")

    # ── Test c: Push SAME client_id with older modified → reject stale ──
    print("=" * 60)
    print("TEST c: Push same client_id, older modified → stale")
    print("=" * 60)
    result_c = push(accounts=[{
        "account_name": "Offline Wallet CHANGED",
        "account_type": "Wallet",
        "currency": "INR",
        "opening_balance": 999,
        "client_id": "test-uuid-001",
        "modified": "2026-09-05 10:00:00",  # older than server's 12:00:00
    }])
    print(f"  accepted accounts: {result_c['accepted']['accounts']}")
    print(f"  rejected accounts: {result_c['rejected']['accounts']}")
    assert len(result_c['rejected']['accounts']) == 1, "FAIL c: not rejected"
    assert result_c['rejected']['accounts'][0]['reason'] == "stale", "FAIL c: wrong reason"
    # Verify original record was NOT overwritten
    original = frappe.db.get_value("Account", {"client_id": "test-uuid-001"}, "account_name")
    assert original == "Offline Wallet", f"FAIL c: record was overwritten, got {original}"
    print("  PASS\n")

    # ── Test d: Incremental pull using server_time_a ──
    print("=" * 60)
    print("TEST d: Incremental pull (since=server_time_a)")
    print("=" * 60)
    result_d = pull(since=server_time_a)
    print(f"  accounts: {len(result_d['accounts'])} records")
    print(f"  categories: {len(result_d['categories'])} records")
    print(f"  tags: {len(result_d['tags'])} records")
    print(f"  transactions: {len(result_d['transactions'])} records")
    # Should only have the 1 account from test b, nothing else
    assert len(result_d['accounts']) == 1, f"FAIL d: expected 1 account, got {len(result_d['accounts'])}"
    assert result_d['accounts'][0]['client_id'] == "test-uuid-001", "FAIL d: wrong account"
    assert len(result_d['categories']) == 0, f"FAIL d: expected 0 categories, got {len(result_d['categories'])}"
    assert len(result_d['tags']) == 0, f"FAIL d: expected 0 tags, got {len(result_d['tags'])}"
    assert len(result_d['transactions']) == 0, f"FAIL d: expected 0 transactions, got {len(result_d['transactions'])}"
    print("  PASS\n")

    # ── Test e: Push Transaction with is_deleted=1, then pull includes it ──
    print("=" * 60)
    print("TEST e: Push Transaction with is_deleted=1, pull includes it")
    print("=" * 60)
    result_e_push = push(transactions=[{
        "transaction_type": "Expense",
        "account": "Test Acc",
        "category": cat_exp.name,
        "amount": 99,
        "date": "2026-09-05",
        "note": "deleted item",
        "is_deleted": 1,
        "client_id": "test-uuid-txn-001",
        "modified": "2026-09-05 13:00:00",
    }])
    print(f"  push accepted: {result_e_push['accepted']['transactions']}")
    assert len(result_e_push['accepted']['transactions']) == 1, "FAIL e: push not accepted"

    # Now pull — the soft-deleted transaction should appear
    result_e_pull = pull(since=server_time_a)
    deleted_txns = [t for t in result_e_pull['transactions'] if t.get('is_deleted') == 1]
    print(f"  pull transactions (since server_time_a): {len(result_e_pull['transactions'])} total")
    print(f"  soft-deleted transactions in pull: {len(deleted_txns)}")
    assert len(deleted_txns) >= 1, "FAIL e: soft-deleted transaction missing from pull"
    print("  PASS\n")

    print("=" * 60)
    print("ALL 5 TESTS PASSED")
    print("=" * 60)
