import frappe

def execute():
    frappe.set_user("Administrator")

    # Clean slate
    frappe.db.sql("DELETE FROM `tabTransactionTag`")
    frappe.db.sql("DELETE FROM `tabTransaction`")
    frappe.db.sql("DELETE FROM `tabAccount`")
    frappe.db.sql("DELETE FROM `tabCategory`")
    frappe.db.sql("DELETE FROM `tabTag`")
    frappe.db.commit()
    print("=== CLEAN SLATE ===")

    def show_all(label):
        accounts = frappe.db.get_all(
            "Account",
            fields=["name", "account_name", "current_balance", "opening_balance"],
            order_by="account_name asc",
        )
        print(f"\n  [{label}]")
        for a in accounts:
            print(f"    {a.account_name}: current_balance={a.current_balance}")
        return {a.account_name: a.current_balance for a in accounts}

    # Step 1: Create Account "Test Checking", opening_balance=1000
    print("\n--- Step 1: Create Account 'Test Checking', opening_balance=1000 ---")
    acc_checking = frappe.get_doc({
        "doctype": "Account",
        "account_name": "Test Checking",
        "account_type": "Cash",
        "currency": "INR",
        "opening_balance": 1000,
    })
    acc_checking.insert(ignore_permissions=True)
    frappe.db.commit()
    bal = show_all("After Step 1")
    assert bal["Test Checking"] == 1000, f"FAIL Step 1: got {bal['Test Checking']}"

    # Step 2: Create Expense, account=Test Checking, amount=200
    print("\n--- Step 2: Create Expense, amount=200 ---")
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

    t_expense = frappe.get_doc({
        "doctype": "Transaction",
        "transaction_type": "Expense",
        "account": "Test Checking",
        "category": cat_exp.name,
        "amount": 200,
        "date": "2026-09-05",
        "note": "Food",
    })
    t_expense.insert(ignore_permissions=True)
    frappe.db.commit()
    bal = show_all("After Step 2")
    assert bal["Test Checking"] == 800, f"FAIL Step 2: got {bal['Test Checking']}"

    # Step 3: Create Income, account=Test Checking, amount=500
    print("\n--- Step 3: Create Income, amount=500 ---")
    cat_inc = frappe.get_doc({
        "doctype": "Category",
        "category_name": "Salary",
        "category_type": "Income",
        "parent_category": "",
        "category_icon": "",
        "category_emoji": "",
        "category_color": "#000",
        "sort_order": 0,
    })
    cat_inc.insert(ignore_permissions=True)
    frappe.db.commit()

    t_income = frappe.get_doc({
        "doctype": "Transaction",
        "transaction_type": "Income",
        "account": "Test Checking",
        "category": cat_inc.name,
        "amount": 500,
        "date": "2026-09-05",
        "note": "Salary",
    })
    t_income.insert(ignore_permissions=True)
    frappe.db.commit()
    bal = show_all("After Step 3")
    assert bal["Test Checking"] == 1300, f"FAIL Step 3: got {bal['Test Checking']}"

    # Step 4: Create Account "Test Savings", opening_balance=0
    print("\n--- Step 4: Create Account 'Test Savings', opening_balance=0 ---")
    acc_savings = frappe.get_doc({
        "doctype": "Account",
        "account_name": "Test Savings",
        "account_type": "Bank",
        "currency": "INR",
        "opening_balance": 0,
    })
    acc_savings.insert(ignore_permissions=True)
    frappe.db.commit()
    bal = show_all("After Step 4")
    assert bal["Test Savings"] == 0, f"FAIL Step 4: got {bal['Test Savings']}"

    # Step 5: Create Transfer, Test Checking -> Test Savings, amount=300
    print("\n--- Step 5: Create Transfer, Checking->Savings, amount=300 ---")
    t_transfer = frappe.get_doc({
        "doctype": "Transaction",
        "transaction_type": "Transfer",
        "account": "Test Checking",
        "transfer_to_account": "Test Savings",
        "amount": 300,
        "date": "2026-09-05",
        "note": "Transfer to savings",
    })
    t_transfer.insert(ignore_permissions=True)
    frappe.db.commit()
    bal = show_all("After Step 5")
    assert bal["Test Checking"] == 1000, f"FAIL Step 5 Checking: got {bal['Test Checking']}"
    assert bal["Test Savings"] == 300, f"FAIL Step 5 Savings: got {bal['Test Savings']}"

    # Step 6: EDIT Expense from 200 -> 350
    print("\n--- Step 6: EDIT Expense amount 200 -> 350 ---")
    doc_exp = frappe.get_doc("Transaction", t_expense.name)
    doc_exp.amount = 350
    doc_exp.save(ignore_permissions=True)
    frappe.db.commit()
    bal = show_all("After Step 6")
    assert bal["Test Checking"] == 850, f"FAIL Step 6 Checking: got {bal['Test Checking']}"

    # Step 7: Soft-delete Income (is_deleted=1)
    print("\n--- Step 7: Soft-delete Income (is_deleted=1) ---")
    doc_inc = frappe.get_doc("Transaction", t_income.name)
    doc_inc.is_deleted = 1
    doc_inc.save(ignore_permissions=True)
    frappe.db.commit()
    bal = show_all("After Step 7")
    assert bal["Test Checking"] == 350, f"FAIL Step 7 Checking: got {bal['Test Checking']}"

    # Step 8: Restore Income (is_deleted=0)
    print("\n--- Step 8: Restore Income (is_deleted=0) ---")
    doc_inc2 = frappe.get_doc("Transaction", t_income.name)
    doc_inc2.is_deleted = 0
    doc_inc2.save(ignore_permissions=True)
    frappe.db.commit()
    bal = show_all("After Step 8")
    assert bal["Test Checking"] == 850, f"FAIL Step 8 Checking: got {bal['Test Checking']}"

    # Step 9: EDIT Transfer — change transfer_to_account from "Test Savings" to NEW "Test Cash"
    print("\n--- Step 9: Create 'Test Cash' account, then EDIT Transfer transfer_to_account -> Test Cash ---")
    acc_cash = frappe.get_doc({
        "doctype": "Account",
        "account_name": "Test Cash",
        "account_type": "Cash",
        "currency": "INR",
        "opening_balance": 0,
    })
    acc_cash.insert(ignore_permissions=True)
    frappe.db.commit()

    doc_tr = frappe.get_doc("Transaction", t_transfer.name)
    doc_tr.transfer_to_account = "Test Cash"
    doc_tr.save(ignore_permissions=True)
    frappe.db.commit()
    bal = show_all("After Step 9")

    print("\n--- FINAL ASSERTIONS ---")
    print(f"  Test Checking:  {bal['Test Checking']}  (expected 850)")
    print(f"  Test Savings:   {bal['Test Savings']}  (expected 0)")
    print(f"  Test Cash:      {bal['Test Cash']}  (expected 300)")
    assert bal["Test Checking"] == 850, f"FAIL Step 9 Checking: got {bal['Test Checking']}"
    assert bal["Test Savings"] == 0, f"FAIL Step 9 Savings: got {bal['Test Savings']}"
    assert bal["Test Cash"] == 300, f"FAIL Step 9 Cash: got {bal['Test Cash']}"

    print("\n" + "=" * 50)
    print("ALL 9 STEPS PASSED")
    print("=" * 50)
