# Copyright (c) 2026, Sriragul and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class Category(Document):
    def validate(self):
        self.validate_name_uniqueness()
        self.validate_client_id_unique()
        self.validate_parent_type_match()
        self.validate_no_self_reference()
        self.validate_no_cycle()

    def validate_name_uniqueness(self):
        """Category name must be unique per category_type per parent_category per owner.

        Handles null parent_category correctly: two top-level categories with
        the same name collide; a top-level and a subcategory with the same
        name do not (because parent_category differs).
        """
        filters = {
            "category_name": self.category_name,
            "category_type": self.category_type,
            "owner": self.owner,
            "name": ["!=", self.name],
        }

        if self.parent_category:
            filters["parent_category"] = self.parent_category
        else:
            filters["parent_category"] = ("is", "not set")

        existing = frappe.db.exists("Category", filters)
        if existing:
            frappe.throw(
                _('Category "{0}" already exists under this parent for this type.').format(
                    self.category_name
                ),
                frappe.ValidationError,
            )

    def validate_client_id_unique(self):
        """If client_id is set, it must be unique per owner."""
        if not self.client_id:
            return
        existing = frappe.db.exists(
            "Category",
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

    def validate_parent_type_match(self):
        """If parent_category is set, its category_type must match this record's type."""
        if not self.parent_category:
            return

        parent_type = frappe.db.get_value("Category", self.parent_category, "category_type")
        if parent_type and parent_type != self.category_type:
            frappe.throw(
                _('Parent category must be of the same type. Got "{0}" but this category is "{1}".').format(
                    parent_type, self.category_type
                ),
                frappe.ValidationError,
            )

    def validate_no_self_reference(self):
        """parent_category must not equal this record's own name."""
        if self.parent_category and self.parent_category == self.name:
            frappe.throw(
                _("A category cannot be its own parent."),
                frappe.ValidationError,
            )

    def validate_no_cycle(self):
        """Walking up the parent_category chain must not eventually reach this record."""
        if not self.parent_category:
            return

        visited = set()
        current = self.parent_category
        while current:
            if current == self.name:
                frappe.throw(
                    _("Cycle detected: this category appears in the parent chain of the proposed parent."),
                    frappe.ValidationError,
                )
            if current in visited:
                break
            visited.add(current)
            current = frappe.db.get_value("Category", current, "parent_category")
