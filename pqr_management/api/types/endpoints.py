"""
PQR Type catalog endpoints.

Returns the list of active PQR Types configured in a given Service Portal Tool.
"""

import frappe
from frappe import _
from typing import List, Dict, Any

from common_configurations.api.shared import check_rate_limit, sanitize_string


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_tool_types(tool_name: str) -> Dict[str, Any]:
	"""
	Get the PQR Types enabled for a specific Service Portal Tool, plus
	whether anonymous submissions are allowed for that tool.

	Public endpoint (allow_guest) because the citizen may not be logged in
	when the portal renders the tool.

	Args:
		tool_name: name of the Service Portal Tool (child row "name")

	Returns:
		{
			"allow_anonymous": bool,
			"types": [
				{name, label, description, icon, color, display_order},
				...
			]
		}
	"""
	check_rate_limit("pqr_get_tool_types", limit=60, seconds=60)

	tool_name = sanitize_string(tool_name, 140)
	if not tool_name:
		frappe.throw(_("Tool name is required"), frappe.ValidationError)

	tool = frappe.db.get_value(
		"Service Portal Tool",
		tool_name,
		["tool_type", "pqr_allow_anonymous"],
		as_dict=True,
	)
	if not tool:
		frappe.throw(_("Service Portal Tool not found"), frappe.DoesNotExistError)

	if tool.tool_type != "pqr":
		frappe.throw(_("This tool is not a PQR tool"), frappe.ValidationError)

	# Get enabled types in this tool's table
	rows = frappe.get_all(
		"PQR Tool Type",
		filters={"parent": tool_name, "is_enabled": 1},
		fields=["pqr_type"],
	)
	type_names = [r.pqr_type for r in rows if r.pqr_type]

	if not type_names:
		return {"allow_anonymous": bool(tool.pqr_allow_anonymous), "types": []}

	types_data = frappe.get_all(
		"PQR Type",
		filters={"name": ["in", type_names], "is_active": 1},
		fields=["name", "type_code", "label", "description", "icon", "color", "display_order"],
		order_by="display_order asc",
	)

	return {
		"allow_anonymous": bool(tool.pqr_allow_anonymous),
		"types": types_data,
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_all_types() -> List[Dict[str, Any]]:
	"""Get all active PQR Types (used for internal selectors)."""
	check_rate_limit("pqr_get_all_types", limit=60, seconds=60)

	return frappe.get_all(
		"PQR Type",
		filters={"is_active": 1},
		fields=["name", "type_code", "label", "description", "icon", "color", "display_order"],
		order_by="display_order asc",
	)
