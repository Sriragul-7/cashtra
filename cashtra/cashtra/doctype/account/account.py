# Copyright (c) 2026, Sriragul and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class Account(Document):
    def validate(self):
        self.validate_account_name_uniqueness()
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

    def set_current_balance_default(self):
        """For new documents, default current_balance to opening_balance.

        TODO: Once the Transaction DocType is implemented, replace this with
        the full balance recalculation logic:
            current_balance = opening_balance
              + SUM(amount) WHERE type='Income'   AND account=self AND is_deleted=0
              - SUM(amount) WHERE type='Expense'  AND account=self AND is_deleted=0
              - SUM(amount) WHERE type='Transfer' AND account=self AND is_deleted=0
              + SUM(amount) WHERE type='Transfer' AND transfer_to_account=self AND is_deleted=0
        """
        if self.is_new():
            self.current_balance = self.opening_balance or 0
