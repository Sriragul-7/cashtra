# Copyright (c) 2026, Sriragul and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class Account(Document):
    def validate(self):
        self.validate_account_name_uniqueness()
        self.validate_client_id_unique()
        self.set_current_balance_default()

    def validate_account_name_uniqueness(self):
        """Account name must be unique per owner."""
        existing = frappe.db.exists(
            "Account",
            {
                "account_name": self.account_name,
                "owner": self.owner,
                "name": ["!=", self.name],
            },
        )
        if existing:
            frappe.throw(
                _('Account "{0}" already exists for this user.').format(
                    self.account_name
                ),
                frappe.ValidationError,
            )

    def validate_client_id_unique(self):
        """If client_id is set, it must be unique per owner."""
        if not self.client_id:
            return
        existing = frappe.db.exists(
            "Account",
            {
                "client_id": self.client_id,
                "owner": self.owner,
                "name": ["!=", self.name],
            },
        )
        if existing:
            frappe.throw(
                _('Client ID "{0}" already exists for this user.').format(
                    self.client_id
                ),
                frappe.ValidationError,
            )

    def after_insert(self):
        recalculate_account_balance(self.name)

    def on_update(self):
        if not self.is_new():
            recalculate_account_balance(self.name)

    def set_current_balance_default(self):
        """For new documents, default current_balance to opening_balance."""
        if self.is_new():
            self.current_balance = self.opening_balance or 0

def recalculate_account_balance(account_name):
    """Recalculate current_balance for a given Account name."""
    account = frappe.get_doc("Account", account_name)

    income = frappe.db.get_value(
        "Transaction",
        {"account": account_name, "transaction_type": "Income", "is_deleted": 0},
        "sum(amount)",
    ) or 0

    expense = frappe.db.get_value(
        "Transaction",
        {"account": account_name, "transaction_type": "Expense", "is_deleted": 0},
        "sum(amount)",
    ) or 0

    transfer_out = frappe.db.get_value(
        "Transaction",
        {"account": account_name, "transaction_type": "Transfer", "is_deleted": 0},
        "sum(amount)",
    ) or 0

    transfer_in = frappe.db.get_value(
        "Transaction",
        {"transfer_to_account": account_name, "transaction_type": "Transfer", "is_deleted": 0},
        "sum(amount)",
    ) or 0

    balance = (account.opening_balance or 0) + income - expense - transfer_out + transfer_in
    frappe.db.set_value("Account", account_name, "current_balance", balance)
