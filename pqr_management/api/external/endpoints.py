"""
PQR External API (API Key authenticated).

For external integrations (chatbots, mobile apps, etc.) to register PQRs
on behalf of citizens.
"""

import frappe
from frappe import _
from typing import Dict, Any, Optional

from common_configurations.api.shared import (
	require_api_key,
	sanitize_string,
)

from pqr_management.api.entries.endpoints import (
	_validate_pqr_inputs,
	_build_pqr_entry,
)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@require_api_key("enable_create_pqr")
def create_pqr(
	pqr_type: str,
	subject: str,
	description: str,
	user_contact: Optional[str] = None,
	is_anonymous: int = 0,
	submitter_name: Optional[str] = None,
	submitter_email: Optional[str] = None,
	submitter_phone: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Create a PQR from an external integration.

	Headers:
		X-API-Key: <api_key>

	Args:
		pqr_type: name of the PQR Type (e.g. "peticion", "queja")
		subject: short subject
		description: detailed text
		user_contact: optional User Contact name to associate
		is_anonymous: 1 to mark anonymous (overrides user_contact)
		submitter_name/email/phone: optional contact info (ignored if anonymous)

	Returns:
		Created PQR summary
	"""
	is_anonymous_bool = bool(int(is_anonymous)) if is_anonymous else False

	_validate_pqr_inputs(pqr_type, subject, description)

	if user_contact and not is_anonymous_bool:
		user_contact = sanitize_string(user_contact, 140)
		if not frappe.db.exists("User contact", user_contact):
			frappe.throw(_("User contact not found"), frappe.DoesNotExistError)
	else:
		user_contact = None

	service_info = frappe.local.api_service

	try:
		result = _build_pqr_entry(
			pqr_type=pqr_type,
			subject=subject,
			description=description,
			user_contact=user_contact,
			is_anonymous=is_anonymous_bool,
			submitter_name=submitter_name,
			submitter_email=submitter_email,
			submitter_phone=submitter_phone,
			source="api",
		)

		frappe.logger().info(
			f"PQR {result['name']} created via API "
			f"(service: {service_info['service_title']}, type: {pqr_type})"
		)

		return result

	except frappe.ValidationError:
		raise
	except Exception as e:
		frappe.log_error(
			title=_("Error creating PQR via API"),
			message=f"Service: {service_info.get('service_title')}, Error: {str(e)}",
		)
		frappe.throw(_("Error creating PQR"), frappe.ValidationError)
