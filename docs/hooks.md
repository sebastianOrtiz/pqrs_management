# `hooks.py` — Configuración completa de la app

Archivo: `pqr_management/hooks.py`. A continuación se documentan **todas** las claves significativas en uso. Los bloques comentados al final del archivo (`scheduler_events`, `auth_hooks`, `doc_events`, etc.) no se utilizan y se omiten aquí.

---

## Metadatos

```python
app_name = "pqr_management"
app_title = "PQRs Management"
app_publisher = "Nexora Online SAS"
app_description = "Aplicación enfocada en recepción y gestión de PQRs (Peticiones, Quejas, Reclamos)"
app_email = "sebastianortiz989@gmail.com"
app_license = "mit"
```

> Nota: `app_title` usa "PQRs" (plural) — el label visible del módulo y workspace es **PQRs**, mientras que cada entrada se llama **PQR**.

---

## `required_apps`

```python
required_apps = ["common_configurations"]
```

`common_configurations` aporta:

- DocTypes: `User contact`, `Service Portal`, `Service Portal Tool`, `Tool Type`, `API Service`.
- Autenticación: `X-User-Contact-Token` (token de portal), `X-API-Key` (integraciones).
- Utilidades en `common_configurations.api.shared`:
  - `check_rate_limit(name, limit, seconds)`
  - `check_honeypot(value)`
  - `get_current_user_contact()`
  - `sanitize_string(text, max_length)`
  - `require_api_key(flag_name)` (decorador)

Ver `common_configurations/CLAUDE.md` para el detalle.

---

## `fixtures`

```python
fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", ["PQR Manager", "PQR Agent"]]],
    },
    {
        "dt": "Tool Type",
        "filters": [["app_name", "=", "pqr_management"]],
    },
    {
        "dt": "Custom Field",
        "filters": [["name", "in", [
            "Service Portal Tool-pqr_allowed_types",
            "Service Portal Tool-pqr_allow_anonymous",
            "API Service-section_pqr",
            "API Service-enable_create_pqr",
        ]]],
    },
    {
        "dt": "PQR Type",
        "filters": [["name", "in", [
            "peticion", "queja", "reclamo",
            "sugerencia", "felicitacion", "denuncia",
        ]]],
    },
]
```

### Roles (`fixtures/role.json`)

| `name` / `role_name` | `desk_access` |
|---|---|
| `PQR Manager` | 1 |
| `PQR Agent` | 1 |

### Tool Types (`fixtures/tool_type.json`)

| `name` / `tool_name` | `tool_label` | `icon` | `description` | `app_name` |
|---|---|---|---|---|
| `pqr` | PQRs | `MessageSquare` | "Permite a los ciudadanos enviar Peticiones, Quejas, Reclamos y otras retroalimentaciones" | `pqr_management` |
| `my_pqr` | Mis PQRs | `Inbox` | "Permite a los ciudadanos ver el estado de las PQR que han enviado" | `pqr_management` |

> El filtro `["app_name", "=", "pqr_management"]` selecciona automáticamente todos los Tool Types declarados por esta app, sin enumerarlos.

### Custom Fields (`fixtures/custom_field.json`)

| `name` | DocType extendido | Tipo | `insert_after` | Reglas |
|---|---|---|---|---|
| `Service Portal Tool-pqr_allowed_types` | Service Portal Tool | Table → `PQR Tool Type` | `is_enabled` | `depends_on / mandatory_depends_on = eval:doc.tool_type=='pqr'` |
| `Service Portal Tool-pqr_allow_anonymous` | Service Portal Tool | Check (default `1`) | `pqr_allowed_types` | `depends_on = eval:doc.tool_type=='pqr'` |
| `API Service-section_pqr` | API Service | Section Break (label `PQR Configuration`) | `enable_register_contact` | — |
| `API Service-enable_create_pqr` | API Service | Check (default `0`) | `section_pqr` | — |

Todos están en `module: "Pqr Management"` y se crean también de forma idempotente desde `install.py`.

### PQR Types (`fixtures/pqr_type.json`)

6 tipos pre-cargados con `is_active=1`:

| `name` | `label` | `icon` | `color` | `display_order` |
|---|---|---|---|---|
| `peticion` | Petición | `MessageSquare` | `#2563eb` | 10 |
| `queja` | Queja | `AlertCircle` | `#dc2626` | 20 |
| `reclamo` | Reclamo | `AlertTriangle` | `#ea580c` | 30 |
| `sugerencia` | Sugerencia | `Lightbulb` | `#ca8a04` | 40 |
| `felicitacion` | Felicitación | `Heart` | `#16a34a` | 50 |
| `denuncia` | Denuncia | `ShieldAlert` | `#7c3aed` | 60 |

Las descripciones se mantienen en español y son `translatable=1`.

---

## `after_install`

```python
after_install = "pqr_management.install.after_install"
```

Llama a `pqr_management/install.py:after_install()` que:

1. **Valida dependencias**: aborta si `common_configurations` no está instalado.
2. **Crea custom fields idempotentemente**: los 4 custom fields se crean en este punto si no existen (sin esperar al primer `bench migrate`).

Detalle completo en [`INSTALL.md`](INSTALL.md).

---

## Permisos custom

```python
permission_query_conditions = {
    "PQR Entry": "pqr_management.pqr_management.doctype.pqr_entry.pqr_entry.get_permission_query_conditions",
}

has_permission = {
    "PQR Entry": "pqr_management.pqr_management.doctype.pqr_entry.pqr_entry.has_permission",
}
```

Ambas funciones están en `pqr_management/pqr_management/doctype/pqr_entry/pqr_entry.py:32-65`. Comportamiento:

| Rol | `get_permission_query_conditions` | `has_permission` |
|---|---|---|
| `System Manager` o `PQR Manager` | `""` (sin filtro → ve todas) | `True` |
| `PQR Agent` | ``f"`tabPQR Entry`.assigned_to = '{user}'"`` | `doc.assigned_to == user` |
| Cualquier otro | `"1=0"` (sin acceso) | `False` |

Detalles en [`features/PERMISSIONS.md`](features/PERMISSIONS.md) y [`doctypes/PQR_ENTRY.md`](doctypes/PQR_ENTRY.md).

---

## `add_to_apps_screen`

Está **comentado** en el archivo (`pqr_management/hooks.py:57-65`). Si se quisiera mostrar la app en la pantalla de Apps del Desk:

```python
add_to_apps_screen = [
    {
        "name": "pqr_management",
        "logo": "/assets/pqr_management/logo.png",
        "title": "Pqr Management",
        "route": "/pqr_management",
        "has_permission": "pqr_management.api.permission.has_app_permission"
    }
]
```

Actualmente desactivado.

---

## Bloques no usados

Los siguientes hooks **no están en uso** (comentados o ausentes) en `pqr_management/hooks.py`:

- `app_include_css`, `app_include_js`, `web_include_css`, `web_include_js`.
- `website_theme_scss`, `webform_include_js/css`, `page_js`, `doctype_js`, `doctype_list_js`, etc.
- `app_include_icons`.
- `home_page`, `role_home_page`, `website_generators`.
- `jinja` (sin custom methods/filters).
- `before_install`, `before_uninstall`, `after_uninstall`.
- `before_app_install`, `after_app_install`, `before_app_uninstall`, `after_app_uninstall`.
- `notification_config`.
- `doc_events` (sin overrides — la lógica vive en el controlador `pqr_entry.py`).
- `override_doctype_class`, `override_doctype_dashboards`.
- `scheduler_events` (sin jobs programados).
- `auto_cancel_exempted_doctypes`, `ignore_links_on_delete`.
- `before_request`, `after_request`, `before_job`, `after_job`.
- `user_data_fields`, `auth_hooks`, `default_log_clearing_doctypes`.
- `before_tests`, `export_python_type_annotations`.
- `override_whitelisted_methods`.
