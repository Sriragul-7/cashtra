import frappe

def execute():
    frappe.set_user("Administrator")
    meta = frappe.get_meta("Account")
    print("naming_rule:", meta.naming_rule)
    print("autoname:", getattr(meta, "autoname", "NOT SET"))
