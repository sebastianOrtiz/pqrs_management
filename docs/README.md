# Documentación de la App PQRs Management

App de Frappe para la **recepción y gestión de PQRs** (Peticiones, Quejas, Reclamos, Sugerencias, Felicitaciones y Denuncias) provenientes de ciudadanía a través de un Service Portal público, integraciones externas autenticadas o registro interno.

- **Publisher**: Nexora Online SAS
- **Apps requeridas**: `common_configurations`
- **Módulo Frappe**: `Pqr Management`
- **Roles propios**: `PQR Manager`, `PQR Agent`
- **Labels visibles**: `PQRs` (módulo/colección) — `PQR` (entrada individual)

---

## Tabla de Contenidos

### Instalación y configuración

- [INSTALL.md](INSTALL.md) — Proceso de instalación (`install.py`, custom fields creados, fixtures, verificación).
- [hooks.md](hooks.md) — Documentación completa de `hooks.py`: `required_apps`, fixtures, `permission_query_conditions`, `has_permission`, `after_install`.

### DocTypes

| DocType | Documento | Propósito |
|---|---|---|
| PQR Type | [doctypes/PQR_TYPE.md](doctypes/PQR_TYPE.md) | Catálogo de tipos (label, icono, color, orden, activo). |
| PQR Entry | [doctypes/PQR_ENTRY.md](doctypes/PQR_ENTRY.md) | DocType principal: una PQR enviada por un ciudadano. |
| PQR Tool Type | [doctypes/PQR_TOOL_TYPE.md](doctypes/PQR_TOOL_TYPE.md) | Child table para enlazar tipos a un `Service Portal Tool`. |

### APIs

| API | Documento | Descripción |
|---|---|---|
| Entries | [api/ENTRIES.md](api/ENTRIES.md) | Endpoints del portal: crear PQR, listar mis PQRs, obtener detalle. Autenticación `X-User-Contact-Token` (opcional para crear, obligatoria para leer). |
| Types | [api/TYPES.md](api/TYPES.md) | Consulta del catálogo: tipos habilitados por tool y todos los tipos activos. |
| External | [api/EXTERNAL.md](api/EXTERNAL.md) | Endpoint con API Key (`X-API-Key`) para integraciones (chatbots, apps móviles). |

### Features

| Feature | Documento |
|---|---|
| Sistema de anonimato (3 casos) | [features/ANONYMOUS_PQR.md](features/ANONYMOUS_PQR.md) |
| Tool del portal `pqr` (envío) | [features/PQR_TOOL.md](features/PQR_TOOL.md) |
| Tool del portal `my_pqr` (historial) | [features/MY_PQR_TOOL.md](features/MY_PQR_TOOL.md) |
| Permisos por rol | [features/PERMISSIONS.md](features/PERMISSIONS.md) |

---

## Tipos de PQR pre-cargados (fixture)

Estos 6 tipos se instalan automáticamente al sincronizar fixtures (ver [`pqr_management/fixtures/pqr_type.json`](../pqr_management/fixtures/pqr_type.json)):

| `name` / `type_code` | `label` | `icon` (Lucide) | `color` | `display_order` |
|---|---|---|---|---|
| `peticion` | Petición | `MessageSquare` | `#2563eb` | 10 |
| `queja` | Queja | `AlertCircle` | `#dc2626` | 20 |
| `reclamo` | Reclamo | `AlertTriangle` | `#ea580c` | 30 |
| `sugerencia` | Sugerencia | `Lightbulb` | `#ca8a04` | 40 |
| `felicitacion` | Felicitación | `Heart` | `#16a34a` | 50 |
| `denuncia` | Denuncia | `ShieldAlert` | `#7c3aed` | 60 |

Todos quedan activos (`is_active = 1`) por defecto y se ordenan por `display_order` ascendente. Pueden desactivarse o complementarse con nuevos tipos sin tocar código (ver [doctypes/PQR_TYPE.md](doctypes/PQR_TYPE.md)).

---

## Tools del Service Portal pre-cargadas

Al sincronizar el fixture `tool_type.json`, se registran dos Tool Types:

| `tool_name` | `tool_label` | `icon` | Propósito | Componente Angular |
|---|---|---|---|---|
| `pqr` | PQRs | `MessageSquare` | Permite enviar una PQR (con o sin autenticación). | `features/tools/pqr/` |
| `my_pqr` | Mis PQRs | `Inbox` | Listado y detalle de las PQRs propias (solo autenticados). | `features/tools/my-pqr/` |

Cada `Service Portal Tool` con `tool_type='pqr'` debe configurar:

- **`pqr_allowed_types`** (child table → `PQR Tool Type`): qué tipos se ofrecen al ciudadano en esa instancia.
- **`pqr_allow_anonymous`** (Check, default `1`): si se permite el envío anónimo explícito para usuarios autenticados.

---

## Resumen de archivos clave

- `pqr_management/hooks.py` — registro de fixtures, hooks de permisos, `after_install`.
- `pqr_management/install.py` — creación defensiva e idempotente de los 4 custom fields.
- `pqr_management/pqr_management/doctype/pqr_entry/pqr_entry.py` — controlador y funciones de permisos (`get_permission_query_conditions`, `has_permission`).
- `pqr_management/pqr_management/doctype/pqr_type/pqr_type.py` — controlador del catálogo (vacío, `pass`).
- `pqr_management/pqr_management/doctype/pqr_tool_type/pqr_tool_type.py` — child table (vacío, `pass`).
- `pqr_management/api/entries/endpoints.py` — endpoints del portal.
- `pqr_management/api/types/endpoints.py` — consulta del catálogo.
- `pqr_management/api/external/endpoints.py` — endpoint externo con API Key.
- `pqr_management/fixtures/role.json`, `tool_type.json`, `pqr_type.json`, `custom_field.json` — datos sincronizados con `bench migrate`.

Y en `common_configurations`:

- `front_apps/service-portal/src/app/features/tools/pqr/` — componente Angular de envío.
- `front_apps/service-portal/src/app/features/tools/my-pqr/` — componente Angular de seguimiento.
