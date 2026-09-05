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

    # Create an EXISTING category (already synced, has a real server name)
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
    print(f"Pre-existing category: {cat_exp.name}")

    # ── Re-run tests a–e to confirm nothing broke ──
    print("\n" + "=" * 60)
    print("TEST a: Full pull (since=None)")
    print("=" * 60)
    result_a = pull(since=None)
    assert len(result_a['accounts']) == 0, f"FAIL a: expected 0 accounts, got {len(result_a['accounts'])}"
    assert len(result_a['categories']) >= 1, f"FAIL a: expected >=1 categories, got {len(result_a['categories'])}"
    assert len(result_a['tags']) == 0, f"FAIL a: expected 0 tags, got {len(result_a['tags'])}"
    assert len(result_a['transactions']) == 0, f"FAIL a: expected 0 transactions, got {len(result_a['transactions'])}"
    server_time_a = result_a['server_time']
    print(f"  accounts={len(result_a['accounts'])} categories={len(result_a['categories'])} tags={len(result_a['tags'])} transactions={len(result_a['transactions'])}")
    print("  PASS\n")

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
    assert len(result_b['accepted']['accounts']) == 1, "FAIL b"
    print(f"  accepted: {result_b['accepted']['accounts']}")
    print("  PASS\n")

    print("=" * 60)
    print("TEST c: Push same client_id, older modified → stale")
    print("=" * 60)
    result_c = push(accounts=[{
        "account_name": "CHANGED",
        "account_type": "Wallet",
        "currency": "INR",
        "opening_balance": 999,
        "client_id": "test-uuid-001",
        "modified": "2026-09-05 10:00:00",
    }])
    assert len(result_c['rejected']['accounts']) == 1, "FAIL c"
    assert result_c['rejected']['accounts'][0]['reason'] == "stale", "FAIL c reason"
    original = frappe.db.get_value("Account", {"client_id": "test-uuid-001"}, "account_name")
    assert original == "Offline Wallet", f"FAIL c: record overwritten, got {original}"
    print(f"  rejected: {result_c['rejected']['accounts']}")
    print("  PASS\n")

    print("=" * 60)
    print("TEST d: Incremental pull")
    print("=" * 60)
    result_d = pull(since=server_time_a)
    assert len(result_d['accounts']) == 1, f"FAIL d: expected 1 account, got {len(result_d['accounts'])}"
    assert len(result_d['categories']) == 0, f"FAIL d: expected 0 categories, got {len(result_d['categories'])}"
    assert len(result_d['tags']) == 0, f"FAIL d: expected 0 tags, got {len(result_d['tags'])}"
    assert len(result_d['transactions']) == 0, f"FAIL d: expected 0 transactions, got {len(result_d['transactions'])}"
    print(f"  accounts={len(result_d['accounts'])} categories={len(result_d['categories'])} tags={len(result_d['tags'])} transactions={len(result_d['transactions'])}")
    print("  PASS\n")

    print("=" * 60)
    print("TEST e: Push Transaction with is_deleted=1, pull includes it")
    print("=" * 60)
    result_e_push = push(transactions=[{
        "transaction_type": "Expense",
        "account": "Offline Wallet",
        "category": cat_exp.name,
        "amount": 99,
        "date": "2026-09-05",
        "note": "deleted item",
        "is_deleted": 1,
        "client_id": "test-uuid-txn-001",
        "modified": "2026-09-05 13:00:00",
    }])
    assert len(result_e_push['accepted']['transactions']) == 1, "FAIL e push"
    result_e_pull = pull(since=server_time_a)
    deleted_txns = [t for t in result_e_pull['transactions'] if t.get('is_deleted') == 1]
    assert len(deleted_txns) >= 1, "FAIL e: soft-deleted txn missing from pull"
    print(f"  push accepted: {result_e_push['accepted']['transactions']}")
    print(f"  pull soft-deleted txns: {len(deleted_txns)}")
    print("  PASS\n")

    # ── Test f: Single push with Account + Transaction referencing same-batch Account ──
    print("=" * 60)
    print("TEST f: Single push — new Account + Transaction referencing it via client_id")
    print("=" * 60)
    result_f = push(
        accounts=[{
            "account_name": "New Savings",
            "account_type": "Bank",
            "currency": "INR",
            "opening_balance": 1000,
            "client_id": "acc-1",
            "modified": "2026-09-05 14:00:00",
        }],
        transactions=[{
            "transaction_type": "Expense",
            "account": {"client_id": "acc-1"},  # same-batch reference
            "category": cat_exp.name,           # already-synced reference
            "amount": 150,
            "date": "2026-09-05",
            "note": "groceries",
            "client_id": "txn-1",
            "modified": "2026-09-05 14:01:00",
        }],
    )

    print(f"  accepted accounts: {result_f['accepted']['accounts']}")
    print(f"  accepted transactions: {result_f['accepted']['transactions']}")
    print(f"  rejected: {result_f['rejected']}")

    # Both should be accepted
    assert len(result_f['accepted']['accounts']) == 1, f"FAIL f: account not accepted"
    assert len(result_f['accepted']['transactions']) == 1, f"FAIL f: transaction not accepted"
    assert result_f['rejected']['accounts'] == [], f"FAIL f: unexpected account rejection"
    assert result_f['rejected']['transactions'] == [], f"FAIL f: unexpected transaction rejection"

    # Get the server-assigned names
    acc_server_name = result_f['accepted']['accounts'][0]['name']
    txn_server_name = result_f['accepted']['transactions'][0]['name']
    print(f"  Account server name: {acc_server_name}")
    print(f"  Transaction server name: {txn_server_name}")

    # Verify the Transaction's account field points to the real server name
    txn_account = frappe.db.get_value("Transaction", txn_server_name, "account")
    print(f"  Transaction.account = {txn_account}")
    assert txn_account == acc_server_name, f"FAIL f: Transaction.account is '{txn_account}', expected '{acc_server_name}'"

    # Verify current_balance recalculation: opening_balance=1000 - expense=150 = 850
    balance = frappe.db.get_value("Account", acc_server_name, "current_balance")
    print(f"  Account.current_balance = {balance}")
    assert balance == 850, f"FAIL f: expected balance 850, got {balance}"

    print("  PASS\n")

    print("=" * 60)
    print("ALL 6 TESTS PASSED")
    print("=" * 60)
