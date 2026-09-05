# Copyright (c) 2026, Sriragul and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class Tag(Document):
    def validate(self):
        self.validate_name_uniqueness()

    def validate_name_uniqueness(self):
        """Tag name must be unique per owner."""
        existing = frappe.db.exists(
            "Tag",
            {
                "tag_name": self.tag_name,
                "owner": self.owner,
                "name": ["!=", self.name],
            },
        )
        if existing:
            frappe.throw(
                _('Tag "{0}" already exists for this user.').format(self.tag_name),
                frappe.ValidationError,
            )
