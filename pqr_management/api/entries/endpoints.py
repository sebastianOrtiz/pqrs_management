"""
PQR Entry endpoints (Service Portal).

- create_entry_from_portal: creates a PQR from the portal. Can be:
  - Authenticated (token) → associated to the user_contact
  - Authenticated but marked anonymous → not associated
  - Guest (no token) → anonymous by default
- get_my_pqr: lists PQRs of the authenticated user contact
- get_pqr_detail: detail of one PQR (ownership-checked)
"""

import frappe
from frappe import _
from frappe.utils import now_datetime
from typing import Dict, List, Any, Optional

from common_configurations.api.shared import (
	check_rate_limit,
	check_honeypot,
	get_current_user_contact,
	sanitize_string,
)


# ===================
# Validation helpers
# ===================

MAX_SUBJECT_LEN = 200
MAX_DESCRIPTION_LEN = 10000
MAX_NAME_LEN = 140
MAX_PHONE_LEN = 30


def _validate_pqr_inputs(
	pqr_type: str,
	subject: str,
	description: str,
) -> None:
	"""Common input sanitization/validation for PQR creation."""
	if not pqr_type:
		frappe.throw(_("PQR type is required"), frappe.ValidationError)

	if not subject or not subject.strip():
		frappe.throw(_("Subject is required"), frappe.ValidationError)

	if not description or not description.strip():
		frappe.throw(_("Description is required"), frappe.ValidationError)

	if not frappe.db.exists("PQR Type", pqr_type):
		frappe.throw(_("PQR type '{0}' not found").format(pqr_type), frappe.DoesNotExistError)

	is_active = frappe.db.get_value("PQR Type", pqr_type, "is_active")
	if not is_active:
		frappe.throw(_("PQR type '{0}' is not active").format(pqr_type), frappe.ValidationError)


def _build_pqr_entry(
	pqr_type: str,
	subject: str,
	description: str,
	user_contact: Optional[str],
	is_anonymous: bool,
	submitter_name: Optional[str] = None,
	submitter_email: Optional[str] = None,
	submitter_phone: Optional[str] = None,
	source: str = "portal",
) -> Dict[str, Any]:
	"""
	Pure builder for a PQR Entry document. Does not insert.
	Returns the inserted doc as dict.
	"""
	doc = frappe.new_doc("PQR Entry")
	doc.pqr_type = pqr_type
	doc.subject = sanitize_string(subject, MAX_SUBJECT_LEN)
	doc.description = sanitize_string(description, MAX_DESCRIPTION_LEN)
	doc.is_anonymous = 1 if is_anonymous else 0
	doc.source = source
	doc.status = "New"
	doc.received_at = now_datetime()

	if not is_anonymous:
		if user_contact:
			doc.user_contact = user_contact
		if submitter_name:
			doc.submitter_name = sanitize_string(submitter_name, MAX_NAME_LEN)
		if submitter_email:
			doc.submitter_email = sanitize_string(submitter_email, MAX_NAME_LEN)
		if submitter_phone:
			doc.submitter_phone = sanitize_string(submitter_phone, MAX_PHONE_LEN)

	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	return {
		"name": doc.name,
		"pqr_type": doc.pqr_type,
		"subject": doc.subject,
		"status": doc.status,
		"received_at": str(doc.received_at),
		"is_anonymous": bool(doc.is_anonymous),
	}


# ===================
# Portal endpoints
# ===================

@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_entry_from_portal(
	pqr_type: str,
	subject: str,
	description: str,
	is_anonymous: int = 0,
	submitter_name: Optional[str] = None,
	submitter_email: Optional[str] = None,
	submitter_phone: Optional[str] = None,
	honeypot: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Create a PQR Entry from the Service Portal.

	Auth rules:
	- If X-User-Contact-Token is sent AND is_anonymous=0 → associate user_contact
	- If is_anonymous=1 → do NOT associate user_contact (even if token present)
	- If no token → treated as anonymous

	Rate limit: 5 per minute per IP. Honeypot protected.
	"""
	check_rate_limit("pqr_create_entry", limit=5, seconds=60)
	check_honeypot(honeypot)

	is_anonymous_bool = bool(int(is_anonymous)) if is_anonymous else False

	_validate_pqr_inputs(pqr_type, subject, description)

	# Determine user_contact
	user_contact = None
	if not is_anonymous_bool:
		authenticated_contact = get_current_user_contact()
		if authenticated_contact:
			user_contact = authenticated_contact
		# If no auth token and not flagged anonymous, treat as anonymous anyway
		else:
			is_anonymous_bool = True

	try:
		return _build_pqr_entry(
			pqr_type=pqr_type,
			subject=subject,
			description=description,
			user_contact=user_contact,
			is_anonymous=is_anonymous_bool,
			submitter_name=submitter_name,
			submitter_email=submitter_email,
			submitter_phone=submitter_phone,
			source="portal",
		)
	except frappe.ValidationError:
		raise
	except Exception as e:
		frappe.log_error(f"Error creating PQR Entry from portal: {str(e)}", "PQR Portal Create")
		frappe.throw(_("Error creating PQR"), frappe.ValidationError)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_my_pqr(status: Optional[str] = None) -> List[Dict[str, Any]]:
	"""
	List PQRs created by the authenticated user contact.
	Requires X-User-Contact-Token. Anonymous PQRs are NEVER returned.
	"""
	check_rate_limit("pqr_get_my", limit=30, seconds=60)

	user_contact = get_current_user_contact()
	if not user_contact:
		frappe.throw(_("Authentication required"), frappe.AuthenticationError)

	filters = {"user_contact": user_contact, "is_anonymous": 0}
	if status:
		filters["status"] = sanitize_string(status, 50)

	entries = frappe.get_all(
		"PQR Entry",
		filters=filters,
		fields=[
			"name",
			"pqr_type",
			"subject",
			"status",
			"received_at",
			"resolved_at",
		],
		order_by="received_at desc",
		limit=200,
	)

	# Enrich with type label
	type_names = list({e.pqr_type for e in entries if e.pqr_type})
	type_labels = {}
	if type_names:
		for row in frappe.get_all(
			"PQR Type",
			filters={"name": ["in", type_names]},
			fields=["name", "label", "color", "icon"],
		):
			type_labels[row.name] = {
				"label": row.label,
				"color": row.color,
				"icon": row.icon,
			}

	for e in entries:
		info = type_labels.get(e.pqr_type, {})
		e["pqr_type_label"] = info.get("label", e.pqr_type)
		e["pqr_type_color"] = info.get("color")
		e["pqr_type_icon"] = info.get("icon")
		e["received_at"] = str(e.received_at) if e.received_at else None
		e["resolved_at"] = str(e.resolved_at) if e.resolved_at else None

	return entries


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_pqr_detail(pqr_name: str) -> Dict[str, Any]:
	"""
	Get full detail of a PQR. Requires authentication and ownership.
	Anonymous PQRs cannot be retrieved through this endpoint.
	"""
	check_rate_limit("pqr_get_detail", limit=30, seconds=60)

	user_contact = get_current_user_contact()
	if not user_contact:
		frappe.throw(_("Authentication required"), frappe.AuthenticationError)

	pqr_name = sanitize_string(pqr_name, MAX_NAME_LEN)
	if not frappe.db.exists("PQR Entry", pqr_name):
		frappe.throw(_("PQR not found"), frappe.DoesNotExistError)

	pqr = frappe.get_doc("PQR Entry", pqr_name)

	if pqr.is_anonymous or pqr.user_contact != user_contact:
		frappe.throw(_("Not authorized to view this PQR"), frappe.PermissionError)

	type_info = frappe.db.get_value(
		"PQR Type", pqr.pqr_type, ["label", "color", "icon"], as_dict=True
	) or {}

	return {
		"name": pqr.name,
		"pqr_type": pqr.pqr_type,
		"pqr_type_label": type_info.get("label", pqr.pqr_type),
		"pqr_type_color": type_info.get("color"),
		"pqr_type_icon": type_info.get("icon"),
		"subject": pqr.subject,
		"description": pqr.description,
		"status": pqr.status,
		"received_at": str(pqr.received_at) if pqr.received_at else None,
		"resolved_at": str(pqr.resolved_at) if pqr.resolved_at else None,
		"resolution": pqr.resolution,
		"is_anonymous": bool(pqr.is_anonymous),
	}
