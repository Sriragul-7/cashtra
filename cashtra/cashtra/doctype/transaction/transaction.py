# Copyright (c) 2026, Sriragul and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class Transaction(Document):
    def validate(self):
        self.validate_amount_positive()
        self.validate_transfer_rules()
        self.validate_income_expense_rules()

    def validate_amount_positive(self):
        """Amount must be positive. Reject negative or zero values."""
        if self.amount is not None and self.amount <= 0:
            frappe.throw(
                _("Amount must be a positive number. Got {0}.").format(self.amount),
                frappe.ValidationError,
            )

    def validate_transfer_rules(self):
        """Transfer: transfer_to_account required, must differ from account, category must be empty."""
        if self.transaction_type != "Transfer":
            return

        if not self.transfer_to_account:
            frappe.throw(
                _("Transfer requires a 'Transfer To Account'."),
                frappe.ValidationError,
            )

        if self.transfer_to_account == self.account:
            frappe.throw(
                _("Transfer To Account must differ from the source Account."),
                frappe.ValidationError,
            )

        if self.category:
            frappe.throw(
                _("Category must be empty for Transfer transactions."),
                frappe.ValidationError,
            )

    def validate_income_expense_rules(self):
        """Income/Expense: category required, transfer_to_account must be empty."""
        if self.transaction_type not in ("Income", "Expense"):
            return

        if not self.category:
            frappe.throw(
                _("Category is required for {0} transactions.").format(self.transaction_type),
                frappe.ValidationError,
            )

        if self.transfer_to_account:
            frappe.throw(
                _("Transfer To Account must be empty for {0} transactions.").format(
                    self.transaction_type
                ),
                frappe.ValidationError,
            )
