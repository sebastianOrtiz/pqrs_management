# Copyright (c) 2026, Nexora Online SAS and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class PQREntry(Document):
	def validate(self):
		self._validate_anonymous_consistency()
		self._fill_submitter_from_user_contact()
		self._auto_resolve_timestamp()

	def _validate_anonymous_consistency(self):
		"""
		If marked as anonymous, clear submitter fields and unlink user_contact.
		Submitter fields are only meaningful for non-anonymous PQRs.
		"""
		if self.is_anonymous:
			self.user_contact = None
			self.submitter_name = None
			self.submitter_email = None
			self.submitter_phone = None

	def _fill_submitter_from_user_contact(self):
		"""
		If a user_contact is linked and submitter_* fields are empty,
		auto-populate them from the User Contact document.
		"""
		if self.is_anonymous or not self.user_contact:
			return

		contact = frappe.db.get_value(
			"User contact",
			self.user_contact,
			["full_name", "email", "phone_number"],
			as_dict=True,
		)
		if not contact:
			return

		if not self.submitter_name:
			self.submitter_name = contact.full_name
		if not self.submitter_email:
			self.submitter_email = contact.email
		if not self.submitter_phone:
			self.submitter_phone = contact.phone_number

	def _auto_resolve_timestamp(self):
		"""Set resolved_at when status moves to Resolved/Closed and it's empty."""
		if self.status in ("Resolved", "Closed") and not self.resolved_at:
			self.resolved_at = now_datetime()


def get_permission_query_conditions(user):
	"""
	Limit visibility of PQR Entry:
	- System Manager / PQR Manager: see all
	- PQR Agent: see only entries assigned to them
	- Other users: no access
	"""
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)

	if "System Manager" in roles or "PQR Manager" in roles:
		return ""

	if "PQR Agent" in roles:
		return f"`tabPQR Entry`.assigned_to = {frappe.db.escape(user)}"

	return "1=0"


def has_permission(doc, ptype, user):
	if not user:
		user = frappe.session.user

	roles = frappe.get_roles(user)

	if "System Manager" in roles or "PQR Manager" in roles:
		return True

	if "PQR Agent" in roles:
		return doc.assigned_to == user

	return False
