"""
PQR Type catalog endpoints.

Returns the list of active PQR Types configured for a given Service Portal Tool.
The tool references a `PQR Type Set` (regular DocType) which contains the actual
list of types to expose.
"""

import frappe
from frappe import _
from typing import List, Dict, Any

from common_configurations.api.shared import check_rate_limit, sanitize_string
from common_configurations.api.questions import resolve_questions


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_tool_types(tool_name: str) -> Dict[str, Any]:
	"""
	Get the PQR Types enabled for a specific Service Portal Tool,
	plus whether anonymous submissions are allowed.

	Public endpoint (allow_guest) — the citizen may not be logged in.

	Args:
		tool_name: name of the Service Portal Tool row

	Returns:
		{
			"allow_anonymous": bool,
			"types": [
				{name, type_code, label, description, icon, color, display_order},
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
		["tool_type", "pqr_type_set", "pqr_allow_anonymous"],
		as_dict=True,
	)
	if not tool:
		frappe.throw(_("Service Portal Tool not found"), frappe.DoesNotExistError)

	if tool.tool_type != "pqr":
		frappe.throw(_("This tool is not a PQR tool"), frappe.ValidationError)

	if not tool.pqr_type_set:
		return {"allow_anonymous": bool(tool.pqr_allow_anonymous), "types": []}

	# Verify the set is active
	set_info = frappe.db.get_value(
		"PQR Type Set",
		tool.pqr_type_set,
		["name", "is_active"],
		as_dict=True,
	)
	if not set_info or not set_info.is_active:
		return {"allow_anonymous": bool(tool.pqr_allow_anonymous), "types": []}

	# Get enabled types from the set
	rows = frappe.get_all(
		"PQR Type Set Item",
		filters={"parent": tool.pqr_type_set, "is_enabled": 1},
		fields=["pqr_type"],
	)
	type_names = [r.pqr_type for r in rows if r.pqr_type]

	if not type_names:
		return {"allow_anonymous": bool(tool.pqr_allow_anonymous), "types": []}

	types_data = frappe.get_all(
		"PQR Type",
		filters={"name": ["in", type_names], "is_active": 1},
		fields=[
			"name",
			"type_code",
			"label",
			"description",
			"icon",
			"color",
			"display_order",
			"question_set",
		],
		order_by="display_order asc",
	)

	# Per-type question override: resolve_questions([]) when the type has no
	# question_set configured, so the front falls back to the tool-level set.
	for type_row in types_data:
		type_row["questions"] = resolve_questions(type_row.pop("question_set", None))

	return {
		"allow_anonymous": bool(tool.pqr_allow_anonymous),
		"types": types_data,
	}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_all_types() -> List[Dict[str, Any]]:
	"""Get all active PQR Types (for internal selectors)."""
	check_rate_limit("pqr_get_all_types", limit=60, seconds=60)

	return frappe.get_all(
		"PQR Type",
		filters={"is_active": 1},
		fields=["name", "type_code", "label", "description", "icon", "color", "display_order"],
		order_by="display_order asc",
	)
