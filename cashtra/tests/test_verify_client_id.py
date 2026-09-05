import frappe

def execute():
    for dt in ["Account", "Category", "Tag", "Transaction"]:
        meta = frappe.get_meta(dt)
        fields = [f.fieldname for f in meta.fields]
        has_client_id = "client_id" in fields
        print(f"{dt}: client_id present = {has_client_id}")
        if not has_client_id:
            frappe.throw(f"MISSING client_id on {dt}")
    print("All four DocTypes verified.")
