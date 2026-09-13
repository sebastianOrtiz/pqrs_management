import frappe

# Statuses considered "open" (pending work) for the bell counter.
OPEN_STATUSES = ["New", "In Review", "In Process"]


def get_notification_config():
	"""
	Frappe bell/sidebar counter for PQR Entries.

	Shows the number of OPEN entries the current user can see — computed with
	the user's own permissions (`get_permission_query_conditions` on PQR Entry):
	a PQR Agent sees only their assigned cases; Manager / Supervisor see all open.
	"""
	return {
		"for_doctype": {
			"PQR Entry": {"status": ["in", OPEN_STATUSES]},
		}
	}
