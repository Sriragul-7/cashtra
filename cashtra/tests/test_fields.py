import frappe

def execute():
    for dt in ['Account', 'Category', 'Tag', 'Transaction']:
        meta = frappe.get_meta(dt)
        fields = [f.fieldname for f in meta.fields if f.fieldtype not in ('Section Break', 'Column Break', 'Tab Break')]
        print(f'{dt}: {fields}')
