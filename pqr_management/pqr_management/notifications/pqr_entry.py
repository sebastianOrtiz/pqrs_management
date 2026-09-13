# Copyright (c) 2026, Nexora Online SAS and contributors
# For license information, please see license.txt

"""
PQR Entry Notification Service

In-app (bell) notifications for the staff member a PQR case is assigned or
reassigned to. Mirrors the pattern used by the `logbook` app
(logbook.logbook.notifications.logbook_entry.notify_staff_of_assignment),
adapted to how PQR Management assigns cases: by user only (`assigned_to`),
with no area concept.

NOTE: pqr_management has no Settings doctype yet, so there is no
"notify_assignee_on_assignment" toggle to gate this on/off — the
notification is unconditionally enabled. If a PQR Settings doctype is
introduced later, add a Check field (default 1) and gate `notify_assignee`
on it the same way `logbook.notify_staff_of_assignment` is gated by
`Logbook Settings.notify_staff_on_assignment`.
"""

import frappe
from frappe import _


def _create_notification_log(user: str, entry, subject: str, actor: str = None) -> None:
	"""Insert a Notification Log (the bell) for `user` and push the realtime event."""
	frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": user,
			"from_user": actor if actor and actor != "Guest" else None,
			"type": "Alert",
			"document_type": "PQR Entry",
			"document_name": entry.name,
			"subject": subject,
		}
	).insert(ignore_permissions=True)
	# Nudge the recipient's bell so the unread count updates without a refresh.
	frappe.publish_realtime("notification", {"type": "Alert"}, user=user, after_commit=True)


def notify_assignee(entry_name: str, actor: str = None) -> None:
	"""
	Create an in-app Notification Log for the user a PQR Entry is (re)assigned
	to (`assigned_to`), when the case is created already assigned or its
	assignment changes.

	Never notifies the actor who triggered it, Guest, Administrator (a system
	account, consistent with the other apps), or a disabled user. Best-effort:
	never raises to the caller/queue. Intended to run in a background job
	(see PQREntry.after_insert / on_update).

	Args:
		entry_name: Name of the PQR Entry document.
		actor: User who triggered the (re)assignment, if any.
	"""
	try:
		entry = frappe.get_doc("PQR Entry", entry_name)

		user = entry.assigned_to
		if not user:
			return

		if user in ("Guest", "Administrator") or (actor and user == actor):
			return

		if not frappe.db.get_value("User", user, "enabled"):
			return

		subject = _("Nuevo caso PQR asignado: {0}").format(entry.get("subject") or entry.name)

		_create_notification_log(user, entry, subject, actor)

	except Exception:
		frappe.log_error(
			title="PQR Entry assignment notification failed",
			message=frappe.get_traceback(),
		)
