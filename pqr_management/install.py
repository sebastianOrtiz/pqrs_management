# Copyright (c) 2026, Nexora Online SAS and contributors
# For license information, please see license.txt

"""
Install hook for pqr_management.

Creates custom fields defensively (in case fixtures don't apply on
first install) and validates that common_configurations is available.
"""

import frappe


def after_install():
	_validate_dependencies()
	_install_custom_fields()


def _validate_dependencies():
	"""Ensure common_configurations is installed."""
	installed = frappe.get_installed_apps()
	if "common_configurations" not in installed:
		frappe.throw(
			"pqr_management requires common_configurations. "
			"Please install it first: bench install-app common_configurations"
		)


def _install_custom_fields():
	"""Create custom fields on Service Portal Tool and API Service if missing."""
	fields = [
		{
			"dt": "Service Portal Tool",
			"fieldname": "pqr_type_set",
			"fieldtype": "Link",
			"options": "PQR Type Set",
			"label": "PQR Type Set",
			"description": "Set of PQR types shown in this tool",
			"insert_after": "is_enabled",
			"depends_on": "eval:doc.tool_type=='pqr'",
			"mandatory_depends_on": "eval:doc.tool_type=='pqr'",
		},
		{
			"dt": "Service Portal Tool",
			"fieldname": "pqr_allow_anonymous",
			"fieldtype": "Check",
			"label": "Allow Anonymous PQR",
			"description": "Allow citizens to submit PQR anonymously",
			"default": "1",
			"insert_after": "pqr_type_set",
			"depends_on": "eval:doc.tool_type=='pqr'",
		},
		{
			"dt": "API Service",
			"fieldname": "section_pqr",
			"fieldtype": "Section Break",
			"label": "PQR Configuration",
			"insert_after": "enable_register_contact",
		},
		{
			"dt": "API Service",
			"fieldname": "enable_create_pqr",
			"fieldtype": "Check",
			"label": "Enable Create PQR",
			"description": "Allow creating PQR entries via this API service",
			"default": "0",
			"insert_after": "section_pqr",
		},
	]

	for field in fields:
		name = f"{field['dt']}-{field['fieldname']}"
		if frappe.db.exists("Custom Field", name):
			continue

		doc = frappe.get_doc({
			"doctype": "Custom Field",
			"module": "Pqr Management",
			**field,
		})
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
