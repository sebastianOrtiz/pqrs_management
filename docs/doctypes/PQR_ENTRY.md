# DocType: PQR Entry

Entrada principal de la app. Representa **una PQR enviada por un ciudadano** (peticion/queja/reclamo/sugerencia/felicitacion/denuncia u otro tipo configurado).

- Archivo JSON: `pqr_management/pqr_management/doctype/pqr_entry/pqr_entry.json`
- Controlador Python: `pqr_management/pqr_management/doctype/pqr_entry/pqr_entry.py`
- **Naming**: `format:PQR-{YYYY}-{#####}` (autoname por expresión). Ejemplo: `PQR-2026-00001`.
- **Title field**: `subject`.
- **Search fields**: `subject,pqr_type,status,user_contact`.
- **Allow rename**: `0`.
- **Sort field**: `received_at DESC`.
- **Track changes**: sí.
- **Módulo**: Pqr Management.

---

## Propósito y casos de uso

- Una PQR enviada por un ciudadano que la entidad debe procesar.
- Puede crearse:
  - **Desde el Service Portal** (tool `pqr`) via `pqr_management.api.entries.create_entry_from_portal` — con o sin sesión, anónima o asociada.
  - **Desde el Desk** manualmente por agentes con permiso.
  - **Vía API externa** (`X-API-Key`) via `pqr_management.api.external.create_pqr` — para chatbots/apps móviles.
- Permite asignar responsable (`assigned_to`), trazar estado (`status`), y consignar la respuesta (`resolution`).
- El campo `is_anonymous` controla si se guarda información del remitente (ver [features/ANONYMOUS_PQR.md](../features/ANONYMOUS_PQR.md)).

---

## Estructura de la vista (orden de campos)

```
Section: General
  pqr_type (Link → PQR Type)    [reqd]   |  status (Select)        [reqd, default 'New']
  subject (Data)                 [reqd]   |  received_at (Datetime) [reqd, default 'Now']
                                          |  source (Select, default 'portal')

Section: Submitter [collapsible]
  user_contact (Link → User contact)      |  submitter_name (Data)   [depends_on !is_anonymous]
  is_anonymous (Check, default 0)         |  submitter_email (Data)  [depends_on !is_anonymous]
                                          |  submitter_phone (Data)  [depends_on !is_anonymous]

Section: Content
  description (Long Text) [reqd]

Section: Internal Management [collapsible]
  assigned_to (Link → User)               |  resolved_at (Datetime) [depends_on status in Resolved/Closed]

Section: Resolution [collapsible, depends_on status in Resolved/Closed/Rejected]
  resolution (Text Editor)
```

---

## Campos uno por uno

### Sección General

| Campo | Tipo | Obligatorio | Default | Opciones | Notas |
|---|---|---|---|---|---|
| `section_general` | Section Break | — | — | label `General` | — |
| `pqr_type` | Link | **Sí** | — | options `PQR Type` | Tipo de PQR. `in_list_view=1`, `in_standard_filter=1`. Description: "Type of PQR (Petición, Queja, Reclamo, etc.)". Validado en API (`_validate_pqr_inputs`): debe existir y ser `is_active=1`. |
| `subject` | Data | **Sí** | — | — | Asunto corto. `in_list_view=1`. Es el `title_field`. Description: "Short subject for this PQR". Sanitizado en API a 200 chars (`MAX_SUBJECT_LEN`). |
| `column_break_general` | Column Break | — | — | — | — |
| `status` | Select | **Sí** | `New` | `New`, `In Review`, `In Process`, `Resolved`, `Closed`, `Rejected` | Estado de progreso. `in_list_view=1`, `in_standard_filter=1`. |
| `received_at` | Datetime | **Sí** | `Now` | — | Fecha/hora de recepción. `in_list_view=1`. La API setea explícitamente `now_datetime()` al crear (`entries/endpoints.py:80`). |
| `source` | Select | No | `portal` | `portal`, `api`, `internal`, `email`, `phone`, `other` | Origen de la PQR. `in_standard_filter=1`. La API del portal setea `portal`, la externa setea `api` (`external/endpoints.py:75`). Description: "Where this PQR came from". |

### Sección Submitter (collapsible)

| Campo | Tipo | Obligatorio | Default | Opciones | Notas |
|---|---|---|---|---|---|
| `section_submitter` | Section Break | — | — | label `Submitter`, `collapsible=1` | Sección plegable. |
| `user_contact` | Link | No | — | options `User contact` | Contacto del ciudadano asociado. `in_standard_filter=1`. Description: "Associated user contact (optional - leave empty for anonymous)". Se **limpia automáticamente** en `validate()` si `is_anonymous=1`. |
| `is_anonymous` | Check | No | `0` | — | Marca la PQR como anónima. `in_list_view=1`. Description: "Mark as anonymous - submitter info will not be stored". Si está activo, el controlador limpia `user_contact`, `submitter_name`, `submitter_email`, `submitter_phone`. |
| `column_break_submitter` | Column Break | — | — | — | — |
| `submitter_name` | Data | No | — | — | Nombre completo del remitente. `depends_on: eval:!doc.is_anonymous`. Description: "Submitter full name (only if not anonymous)". Sanitizado a 140 chars (`MAX_NAME_LEN`). |
| `submitter_email` | Data | No | — | `options: Email` | Email del remitente. `depends_on: eval:!doc.is_anonymous`. Description: "Submitter email for contact (optional, only if not anonymous)". Sanitizado a 140 chars. |
| `submitter_phone` | Data | No | — | — | Teléfono. `depends_on: eval:!doc.is_anonymous`. Description: "Submitter phone (optional)". Sanitizado a 30 chars (`MAX_PHONE_LEN`). |

> Bug menor: el `MAX_NAME_LEN` (140) se aplica también al `submitter_email` (`entries/endpoints.py:87-88`); no es un bug funcional pero el truncamiento por longitud usa el mismo límite que el nombre. Convencionalmente bastaría con dejar la validación de formato `Email` que Frappe aplica al guardar.

### Sección Content

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `section_content` | Section Break | — | label `Content`. |
| `description` | Long Text | **Sí** | Texto detallado de la PQR. Description: "Detailed description of the PQR submitted by the citizen". Sanitizado a 10 000 chars (`MAX_DESCRIPTION_LEN`). |

### Sección Internal Management (collapsible)

| Campo | Tipo | Obligatorio | Opciones | Notas |
|---|---|---|---|---|
| `section_management` | Section Break | — | label `Internal Management`, `collapsible=1` | — |
| `assigned_to` | Link | No | options `User` | Usuario responsable. `in_standard_filter=1`. Description: "User responsible for handling this PQR". El `PQR Agent` solo puede ver/editar PQRs donde `assigned_to == frappe.session.user` (ver `pqr_entry.py:32-65`). |
| `column_break_management` | Column Break | — | — | — |
| `resolved_at` | Datetime | No | — | Marca temporal de resolución. `depends_on: eval:doc.status === 'Resolved' || doc.status === 'Closed'`. **Auto-set** por el controlador (`_auto_resolve_timestamp`) cuando `status in ('Resolved','Closed')` y está vacío. |

### Sección Resolution (collapsible)

| Campo | Tipo | Notas |
|---|---|---|
| `section_resolution` | Section Break | label `Resolution`, `collapsible=1`, `depends_on: eval:doc.status === 'Resolved' || doc.status === 'Closed' || doc.status === 'Rejected'`. |
| `resolution` | Text Editor | Respuesta al ciudadano. Description: "Response to the citizen". Se devuelve en `get_pqr_detail` solo si la PQR pertenece al `user_contact` autenticado y no es anónima. |

---

## Controlador Python (`pqr_entry.py`)

```python
class PQREntry(Document):
    def validate(self):
        self._validate_anonymous_consistency()
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

    def _auto_resolve_timestamp(self):
        """Set resolved_at when status moves to Resolved/Closed and it's empty."""
        if self.status in ("Resolved", "Closed") and not self.resolved_at:
            self.resolved_at = now_datetime()
```

Archivo: `pqr_management/pqr_management/doctype/pqr_entry/pqr_entry.py:10-29`.

### Hooks de evento

| Hook Frappe | Acción |
|---|---|
| `validate` | Ejecuta `_validate_anonymous_consistency` + `_auto_resolve_timestamp`. |

No hay `before_save`, `after_insert`, `on_submit`, etc. La app no emite notificaciones automáticas: ni email, ni websocket, ni desk alert.

---

## Permisos

| Rol | Read | Write | Create | Delete | Email | Export | Print | Report | Share |
|---|---|---|---|---|---|---|---|---|---|
| System Manager | sí | sí | sí | sí | sí | sí | sí | sí | sí |
| PQR Manager | sí | sí | sí | sí | sí | sí | sí | sí | sí |
| PQR Agent | sí | sí | **NO** | — | sí | sí | sí | sí | sí |

> `PQR Agent` tiene `"create": 0` en `pqr_entry.json:219` (no puede crear desde el Desk; solo trabajar lo que se le asigne).

Adicionalmente, los hooks declarados en `hooks.py:48-54`:

```python
permission_query_conditions = {
    "PQR Entry": "pqr_management.pqr_management.doctype.pqr_entry.pqr_entry.get_permission_query_conditions",
}

has_permission = {
    "PQR Entry": "pqr_management.pqr_management.doctype.pqr_entry.pqr_entry.has_permission",
}
```

### `get_permission_query_conditions(user)` (`pqr_entry.py:32-50`)

```python
def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user
    roles = frappe.get_roles(user)
    if "System Manager" in roles or "PQR Manager" in roles:
        return ""
    if "PQR Agent" in roles:
        return f"`tabPQR Entry`.assigned_to = {frappe.db.escape(user)}"
    return "1=0"
```

Filtra los resultados en list views y reportes. `1=0` significa "ningún resultado".

### `has_permission(doc, ptype, user)` (`pqr_entry.py:53-65`)

```python
def has_permission(doc, ptype, user):
    if not user:
        user = frappe.session.user
    roles = frappe.get_roles(user)
    if "System Manager" in roles or "PQR Manager" in roles:
        return True
    if "PQR Agent" in roles:
        return doc.assigned_to == user
    return False
```

Comprueba acceso a un documento individual. Más detalle en [`features/PERMISSIONS.md`](../features/PERMISSIONS.md).

> Nota: el endpoint del portal `create_entry_from_portal` usa `doc.insert(ignore_permissions=True)` (`entries/endpoints.py:92`), por lo que estas restricciones **no** impiden que ciudadanos sin rol creen PQRs. La validación a nivel de portal se basa en token + rate limit + honeypot.

---

## Validaciones de la API al crear

Al crear via API (portal o externa), `_validate_pqr_inputs` (`entries/endpoints.py:35-55`) aplica:

- `pqr_type` no vacío.
- `subject` no vacío y `.strip()`.
- `description` no vacía y `.strip()`.
- `frappe.db.exists("PQR Type", pqr_type)` → `DoesNotExistError` si no existe.
- `PQR Type.is_active == 1` → `ValidationError` si está inactivo.

Y `_build_pqr_entry` sanitiza/trunca con `sanitize_string`:

| Campo | Límite |
|---|---|
| `subject` | 200 chars |
| `description` | 10 000 chars |
| `submitter_name` | 140 chars |
| `submitter_email` | 140 chars |
| `submitter_phone` | 30 chars |

---

## Flujo de estados

```
New ──▶ In Review ──▶ In Process ──▶ Resolved ──▶ Closed
   │           │              │           │
   └───────────┴──────────────┴─────────▶ Rejected
```

- Al pasar a `Resolved` o `Closed`, el controlador setea `resolved_at` automáticamente si está vacío.
- La sección **Resolution** se vuelve visible (`depends_on`) cuando `status` está en `Resolved`, `Closed` o `Rejected`.
- El estado se devuelve textual en las APIs del portal; el frontend Angular lo traduce con `translateStatus()` (mapeo `My PQR Tool Component`):
  - `New` → "Nueva"
  - `In Review` → "En revisión"
  - `In Process` → "En proceso"
  - `Resolved` → "Resuelta"
  - `Closed` → "Cerrada"
  - `Rejected` → "Rechazada"
