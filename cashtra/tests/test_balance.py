import frappe

def execute():
    frappe.set_user("Administrator")

    frappe.db.sql("DELETE FROM `tabTransactionTag`")
    frappe.db.sql("DELETE FROM `tabTransaction`")
    frappe.db.sql("DELETE FROM `tabAccount`")
    frappe.db.sql("DELETE FROM `tabCategory`")
    frappe.db.sql("DELETE FROM `tabTag`")
    frappe.db.commit()
    print("=== Clean slate ===")

    def show_bal(label, account_name):
        bal = frappe.db.get_value("Account", account_name, "current_balance")
        print(f"  {label}: {account_name} -> {bal}")
        return bal

    # Step 1: Account with opening_balance
    print("\n--- Step 1: Account opening_balance=1000 ---")
    acc = frappe.get_doc({
        "doctype": "Account",
        "account_name": "Main Checking",
        "account_type": "Cash",
        "currency": "INR",
        "opening_balance": 1000,
    })
    acc.insert(ignore_permissions=True)
    frappe.db.commit()
    val = show_bal("S1", "Main Checking")
    assert val == 1000, f"FAIL S1: expected 1000 got {val}"
    print("  PASS")

    # Step 2: Category
    print("\n--- Step 2: Income category ---")
    cat_in = frappe.get_doc({
        "doctype": "Category",
        "category_name": "Salary",
        "category_type": "Income",
        "parent_category": "",
        "category_icon": "",
        "category_emoji": "",
        "category_color": "#000",
        "sort_order": 0,
    })
    cat_in.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"  PASS: {cat_in.name}")

    cat_ex = frappe.get_doc({
        "doctype": "Category",
        "category_name": "Food",
        "category_type": "Expense",
        "parent_category": "",
        "category_icon": "",
        "category_emoji": "",
        "category_color": "#000",
        "sort_order": 0,
    })
    cat_ex.insert(ignore_permissions=True)
    frappe.db.commit()
    print(f"  PASS: {cat_ex.name}")

    # Step 3: Income +500
    print("\n--- Step 3: Income +500 ---")
    t1 = frappe.get_doc({
        "doctype": "Transaction",
        "transaction_type": "Income",
        "account": "Main Checking",
        "category": cat_in.name,
        "amount": 500,
        "date": "2026-09-05",
        "note": "Salary",
    })
    t1.insert(ignore_permissions=True)
    frappe.db.commit()
    val = show_bal("S3", "Main Checking")
    assert val == 1500, f"FAIL S3: expected 1500 got {val}"
    print("  PASS")

    # Step 4: Expense -200
    print("\n--- Step 4: Expense -200 ---")
    t2 = frappe.get_doc({
        "doctype": "Transaction",
        "transaction_type": "Expense",
        "account": "Main Checking",
        "category": cat_ex.name,
        "amount": 200,
        "date": "2026-09-05",
        "note": "Lunch",
    })
    t2.insert(ignore_permissions=True)
    frappe.db.commit()
    val = show_bal("S4", "Main Checking")
    assert val == 1300, f"FAIL S4: expected 1300 got {val}"
    print("  PASS")

    # Step 5: Savings + Transfer
    print("\n--- Step 5: Transfer 300 Checking->Savings ---")
    acc2 = frappe.get_doc({
        "doctype": "Account",
        "account_name": "Savings",
        "account_type": "Bank",
        "currency": "INR",
        "opening_balance": 0,
    })
    acc2.insert(ignore_permissions=True)
    frappe.db.commit()

    t3 = frappe.get_doc({
        "doctype": "Transaction",
        "transaction_type": "Transfer",
        "account": "Main Checking",
        "transfer_to_account": "Savings",
        "amount": 300,
        "date": "2026-09-05",
        "note": "Transfer",
    })
    t3.insert(ignore_permissions=True)
    frappe.db.commit()
    val_c = show_bal("S5 Checking", "Main Checking")
    val_s = show_bal("S5 Savings", "Savings")
    assert val_c == 1000, f"FAIL S5 Checking: expected 1000 got {val_c}"
    assert val_s == 300, f"FAIL S5 Savings: expected 300 got {val_s}"
    print("  PASS")

    # Step 6: Edit income 500 -> 700
    print("\n--- Step 6: Edit income 500 -> 700 ---")
    doc = frappe.get_doc("Transaction", t1.name)
    doc.amount = 700
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    val = show_bal("S6", "Main Checking")
    assert val == 1200, f"FAIL S6: expected 1200 got {val}"
    print("  PASS")

    # Step 7: Soft-delete expense
    print("\n--- Step 7: Soft-delete expense ---")
    doc2 = frappe.get_doc("Transaction", t2.name)
    doc2.is_deleted = 1
    doc2.save(ignore_permissions=True)
    frappe.db.commit()
    val = show_bal("S7", "Main Checking")
    assert val == 1400, f"FAIL S7: expected 1400 got {val}"
    print("  PASS")

    # Step 8: Restore expense
    print("\n--- Step 8: Restore expense ---")
    doc2 = frappe.get_doc("Transaction", t2.name)
    doc2.is_deleted = 0
    doc2.save(ignore_permissions=True)
    frappe.db.commit()
    val = show_bal("S8", "Main Checking")
    assert val == 1200, f"FAIL S8: expected 1200 got {val}"
    print("  PASS")

    # Step 9: Reverse transfer
    print("\n--- Step 9: Reverse transfer Savings->Checking ---")
    doc3 = frappe.get_doc("Transaction", t3.name)
    doc3.account = "Savings"
    doc3.transfer_to_account = "Main Checking"
    doc3.save(ignore_permissions=True)
    frappe.db.commit()
    val_c = show_bal("S9 Checking", "Main Checking")
    val_s = show_bal("S9 Savings", "Savings")
    assert val_c == 1800, f"FAIL S9 Checking: expected 1800 got {val_c}"
    assert val_s == -300, f"FAIL S9 Savings: expected -300 got {val_s}"
    print("  PASS")

    print("\n" + "=" * 50)
    print("ALL 9 STEPS PASSED")
    print("=" * 50)
