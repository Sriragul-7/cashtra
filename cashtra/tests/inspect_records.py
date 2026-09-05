import frappe

def execute():
    frappe.set_user("Administrator")

    print("=== ALL ACCOUNTS ===")
    for a in frappe.get_all("Account", fields=["name","account_name","account_type","currency","opening_balance","current_balance","client_id","owner","is_archived","modified"], limit_page_length=0):
        print(f"  {a}")

    print("\n=== ALL CATEGORIES ===")
    for c in frappe.get_all("Category", fields=["name","category_name","category_type","parent_category","client_id","owner","is_archived","modified"], limit_page_length=0):
        print(f"  {c}")

    print("\n=== ALL TAGS ===")
    for t in frappe.get_all("Tag", fields=["name","tag_name","emoji","color","client_id","owner","is_archived","modified"], limit_page_length=0):
        print(f"  {t}")

    print("\n=== ALL TRANSACTIONS ===")
    for t in frappe.get_all("Transaction", fields=["name","client_id","transaction_type","account","transfer_to_account","amount","category","date","note","is_deleted","owner","modified"], limit_page_length=0):
        print(f"  {t}")

    print("\n=== TRANSACTION TAGS ===")
    for tt in frappe.get_all("TransactionTag", fields=["name","parent","parenttype","tag"], limit_page_length=0):
        print(f"  {tt}")
