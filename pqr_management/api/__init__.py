"""
PQR Management API

Modular API for PQR (Petitions, Complaints, Claims) management.

Structure:
    api/
    ├── __init__.py
    ├── entries/      # PQR Entry endpoints (portal)
    ├── types/        # PQR Type catalog endpoints (public-ish)
    └── external/     # External API Key endpoints

Usage:
    frappe.call("pqr_management.api.entries.create_entry_from_portal", ...)
    frappe.call("pqr_management.api.types.get_active_types", ...)
    frappe.call("pqr_management.api.external.create_pqr", ...)

All shared utilities (rate limiting, security, validation) are imported
from common_configurations.api.shared to avoid code duplication.
"""

from . import entries
from . import types
from . import external

__all__ = ["entries", "types", "external"]
