import frappe

def execute():
    frappe.set_user("Administrator")

    frappe.db.sql("DELETE FROM `tabTransactionTag`")
    frappe.db.sql("DELETE FROM `tabTransaction`")
    frappe.db.sql("DELETE FROM `tabAccount`")
    frappe.db.sql("DELETE FROM `tabCategory`")
    frappe.db.sql("DELETE FROM `tabTag`")
    frappe.db.commit()

    acc = frappe.get_doc({
        "doctype": "Account",
        "account_name": "TestAcc",
        "account_type": "Cash",
        "currency": "INR",
        "opening_balance": 1000,
    })
    acc.insert(ignore_permissions=True)
    frappe.db.commit()

    print("Doc name:", acc.name)
    print("Doc current_balance:", acc.current_balance)

    row = frappe.db.get_value("Account", "TestAcc", ["current_balance", "opening_balance", "name"], as_dict=True)
    print("DB row for TestAcc:", row)

    all_accs = frappe.db.get_all("Account", fields=["name", "account_name", "current_balance", "opening_balance"])
    print("All accounts:", all_accs)
