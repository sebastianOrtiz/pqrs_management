"""
PqrProvider — the config provider for pqr_management.

Owns manifest key "pqr_management", covering: pqr_types, pqr_type_sets.

Naming keys (verified against each doctype's `autoname` before designing this
provider): PQR Type autonames `field:type_code` and PQR Type Set autonames
`field:title` — neither is a counter, so `name` IS the natural key the
manifest already uses (type_code / title). No `import_key` field is needed
on either — upsert matches directly on that natural field.

PQR Entry (transactional data) is intentionally NOT covered by this
provider — only catalog/config doctypes (PQR Type, PQR Type Set) are
managed through declarative import/export.

Ref namespace published
------------------------
`common_configurations`'s "pqr" tool type has a custom field
`pqr_type_set` on `Service Portal Tool` (Link -> PQR Type Set). Since a
portal's manifest is owned by `CommonConfigProvider` and must not hardcode
this app's doctypes, it references our PQR Type Sets indirectly via:

    {"$ref": {"namespace": "pqr_management.pqr_type_set", "key": "<title>"}}

which this provider resolves by publishing, for every PQR Type Set it
upserts, `ctx.set_ref("pqr_management.pqr_type_set", title, doc.name)`.
`CommonConfigProvider.depends_on` already includes "pqr_management" so this
provider always runs first when both are registered.
"""

from __future__ import annotations

from typing import Any

import frappe

from common_configurations.api.config import ConfigProvider, upsert_doc

# ---------------------------------------------------------------------
# Doctype <-> manifest section wiring
# ---------------------------------------------------------------------

PQR_TYPE_DOCTYPE = "PQR Type"
PQR_TYPE_SET_DOCTYPE = "PQR Type Set"

# Ref namespace this provider publishes (documented for other providers).
REF_NS_PQR_TYPE_SET = "pqr_management.pqr_type_set"

# Fieldtypes never surfaced through import/export (structural or secret).
_SKIP_FIELDTYPES = {
    "Section Break",
    "Column Break",
    "Tab Break",
    "HTML",
    "Button",
    "Fold",
    "Table",
    "Table MultiSelect",
    "Password",  # never import/export secrets, ever.
}


def _exportable_fields(doctype: str, exclude: tuple[str, ...] = ()) -> list[str]:
    """Flat (non-table, non-structural, non-secret) fieldnames for a doctype,
    reflected from its meta so custom fields added later are picked up
    automatically without this provider needing to know about them."""
    meta = frappe.get_meta(doctype)
    return [
        df.fieldname
        for df in meta.fields
        if df.fieldtype not in _SKIP_FIELDTYPES and df.fieldname not in exclude
    ]


def _pick(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Only the keys of `data` that are in `fields` — so imports only ever
    touch fields the manifest explicitly mentions (no accidental clobbering
    of fields the manifest is silent about)."""
    return {f: data[f] for f in fields if f in data}


class PqrProvider(ConfigProvider):
    key = "pqr_management"

    # No cross-provider refs are consumed on import — this provider only
    # publishes one (REF_NS_PQR_TYPE_SET), it does not resolve refs
    # published by others.
    depends_on: list[str] = []

    # ------------------------------------------------------------------
    # import_section
    # ------------------------------------------------------------------

    def import_section(self, data: dict[str, Any], ctx, dry_run: bool) -> None:
        data = data or {}
        self._import_pqr_types(data.get("pqr_types") or [], ctx)
        self._import_pqr_type_sets(data.get("pqr_type_sets") or [], ctx)

    def _import_pqr_types(self, entries: list[dict], ctx) -> None:
        fields = _exportable_fields(PQR_TYPE_DOCTYPE)
        for entry in entries:
            type_code = entry.get("type_code")
            if not type_code:
                ctx.warn("pqr_types: entry missing 'type_code', skipped")
                continue
            upsert_doc(
                PQR_TYPE_DOCTYPE,
                match={"type_code": type_code},
                values=_pick(entry, fields),
                ctx=ctx,
                key=type_code,
            )

    def _import_pqr_type_sets(self, entries: list[dict], ctx) -> None:
        fields = _exportable_fields(PQR_TYPE_SET_DOCTYPE, exclude=("types",))
        for entry in entries:
            title = entry.get("title")
            if not title:
                ctx.warn("pqr_type_sets: entry missing 'title', skipped")
                continue

            item_rows = []
            for idx, item in enumerate(entry.get("types") or []):
                type_code = item.get("type_code")
                if not type_code:
                    ctx.warn(
                        f"pqr_type_sets.{title}.types[{idx}]: item missing "
                        f"'type_code', skipped"
                    )
                    continue
                if not frappe.db.exists(PQR_TYPE_DOCTYPE, type_code):
                    ctx.warn(
                        f"pqr_type_sets.{title}.types[{idx}]: PQR Type "
                        f"'{type_code}' does not exist, skipped"
                    )
                    continue
                item_rows.append(
                    {
                        "pqr_type": type_code,
                        "is_enabled": item.get("is_enabled", 1),
                    }
                )

            doc, _action = upsert_doc(
                PQR_TYPE_SET_DOCTYPE,
                match={"title": title},
                values=_pick(entry, fields),
                child_tables={"types": item_rows},
                ctx=ctx,
                key=title,
            )
            ctx.set_ref(REF_NS_PQR_TYPE_SET, title, doc.name)

    # ------------------------------------------------------------------
    # export_section
    # ------------------------------------------------------------------

    def export_section(self, ctx) -> dict[str, Any]:
        return {
            "pqr_types": self._export_pqr_types(),
            "pqr_type_sets": self._export_pqr_type_sets(),
        }

    def _export_pqr_types(self) -> list[dict]:
        fields = _exportable_fields(PQR_TYPE_DOCTYPE)
        names = frappe.get_all(PQR_TYPE_DOCTYPE, pluck="name", order_by="name asc")
        return [self._doc_as_dict(PQR_TYPE_DOCTYPE, n, fields) for n in names]

    def _export_pqr_type_sets(self) -> list[dict]:
        fields = _exportable_fields(PQR_TYPE_SET_DOCTYPE, exclude=("types",))
        names = frappe.get_all(PQR_TYPE_SET_DOCTYPE, pluck="name", order_by="name asc")
        result = []
        for n in names:
            doc = frappe.get_doc(PQR_TYPE_SET_DOCTYPE, n)
            entry = self._doc_as_dict(PQR_TYPE_SET_DOCTYPE, n, fields, doc=doc)
            entry["types"] = [
                {"type_code": row.pqr_type, "is_enabled": row.is_enabled}
                for row in doc.types
            ]
            result.append(entry)
        return result

    @staticmethod
    def _doc_as_dict(doctype: str, name: str, fields: list[str], doc=None) -> dict:
        doc = doc or frappe.get_doc(doctype, name)
        return {f: doc.get(f) for f in fields}

    # ------------------------------------------------------------------
    # describe_schema
    # ------------------------------------------------------------------

    def describe_schema(self) -> dict[str, Any]:
        return {
            "pqr_types": {
                "type": "list",
                "doctype": PQR_TYPE_DOCTYPE,
                "match_on": ["type_code"],
                "description": "Catalog of PQR types (Petición, Queja, "
                "Reclamo, ...) selectable in PQR Type Sets.",
                "fields": {
                    "type_code": "Data, required, unique — natural docname, "
                    "snake_case (e.g. peticion, queja, reclamo).",
                    "label": "Data, required — display name shown to citizens.",
                    "is_active": "Check.",
                    "icon": "Data — lucide icon name.",
                    "color": "Color.",
                    "display_order": "Int.",
                    "description": "Small Text.",
                },
            },
            "pqr_type_sets": {
                "type": "list",
                "doctype": PQR_TYPE_SET_DOCTYPE,
                "match_on": ["title"],
                "description": "Named, ordered collection of PQR types "
                "assignable to a portal's 'pqr' tool via the "
                "'pqr_type_set' custom field on Service Portal Tool.",
                "fields": {
                    "title": "Data, required, unique — natural docname.",
                    "is_active": "Check.",
                    "description": "Small Text.",
                    "types": "list[{type_code: <PQR Type type_code>, "
                    "is_enabled: 0|1}] — each type_code must already exist "
                    "as a PQR Type (e.g. imported via 'pqr_types' above, or "
                    "seeded by this app's fixtures); unresolved rows are "
                    "skipped with a warning, not a hard failure.",
                },
                "publishes_ref": {
                    "namespace": REF_NS_PQR_TYPE_SET,
                    "key": "title",
                    "description": "Resolved via "
                    '`{"$ref": {"namespace": "pqr_management.pqr_type_set", '
                    '"key": "<title>"}}` by common_configurations\' portals '
                    "section, for a Service Portal Tool row's 'pqr_type_set' "
                    "field (tool_type='pqr').",
                },
            },
        }
