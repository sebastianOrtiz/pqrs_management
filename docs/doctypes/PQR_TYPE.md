# DocType: PQR Type

Catálogo de **tipos de PQR** disponibles en el sistema. Cada `PQR Entry` enlaza obligatoriamente a un `PQR Type` vía `Link`.

- Archivo JSON: `pqr_management/pqr_management/doctype/pqr_type/pqr_type.json`
- Controlador Python: `pqr_management/pqr_management/doctype/pqr_type/pqr_type.py` (clase vacía `pass`)
- **Naming**: `field:type_code` — el `name` del documento es el valor de `type_code`. Ejemplo: documento con `type_code='peticion'` se llama `peticion`.
- **Title field**: `label`.
- **Allow rename**: `1`.
- **Módulo**: Pqr Management.
- **Ordenamiento por defecto**: `display_order ASC`.
- **Track changes**: sí.
- **Indexable for web search**: `index_web_pages_for_search = 1`.

---

## Propósito y casos de uso

- Define qué clases de PQR existen en el sistema (Petición, Queja, Reclamo, Sugerencia, Felicitación, Denuncia, etc.).
- Cada tipo controla cómo se muestra en el portal: `label`, `icon` (Lucide), `color` y `description`.
- El admin puede crear nuevos tipos sin tocar código.
- Solo los tipos `is_active=1` se ofrecen en las tools del portal (la API valida el flag, `entries/endpoints.py:53-55`).
- Existen 6 tipos pre-cargados como fixture: `peticion`, `queja`, `reclamo`, `sugerencia`, `felicitacion`, `denuncia`.

---

## Estructura de la vista (orden de campos)

```
Section: Basic Information
  type_code (Data)    [reqd, unique]   |  icon (Data)
  label (Data)        [reqd, transl]   |  color (Color)
  is_active (Check)   [default 1]      |  display_order (Int, default 0)

Section: Description
  description (Small Text) [translatable]
```

---

## Campos uno por uno

### Sección Basic Information

| Campo | Tipo | Obligatorio | Default | Opciones | Notas |
|---|---|---|---|---|---|
| `section_basic` | Section Break | — | — | label `Basic Information` | Encabezado. |
| `type_code` | Data | **Sí** | — | unique | Identificador en `snake_case`. Sirve como `name` del doc. `in_list_view=1`. Ejemplos: `peticion`, `queja`, `denuncia`. Description (autodoc): "Unique identifier in snake_case (e.g. peticion, queja, reclamo)". |
| `label` | Data | **Sí** | — | `translatable=1` | Nombre visible mostrado al ciudadano en el portal. `in_list_view=1`. Es el `title_field` del DocType. Description: "Display name shown to citizens (e.g. Petición, Queja)". |
| `is_active` | Check | No | `1` | — | Solo los tipos activos aparecen en las tools del portal. `in_list_view=1`. Description: "Only active types can be shown in tools". La API `get_tool_types`/`get_all_types` filtra por `is_active=1`; `_validate_pqr_inputs` rechaza creaciones contra un tipo inactivo (`entries/endpoints.py:53-55`). |
| `column_break_basic` | Column Break | — | — | — | — |
| `icon` | Data | No | — | — | Nombre de icono Lucide (ej. `MessageSquare`, `AlertCircle`, `Heart`). El frontend Angular usa `<app-icon [name]="type.icon">`. Description: "Lucide icon name (e.g. MessageSquare, AlertCircle)". |
| `color` | Color | No | — | — | Color de acento usado en la tarjeta del portal. Description: "Accent color for the card in the portal". Ejemplos en fixture: `#2563eb` (azul), `#dc2626` (rojo), `#ea580c` (naranja). |
| `display_order` | Int | No | `0` | — | Orden ascendente para mostrar tipos en el portal. Description: "Sort order in the portal (ascending)". El `sort_field` del DocType es `display_order`. La API `get_active_types` ordena por este campo. |

### Sección Description

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| `section_description` | Section Break | — | label `Description`. |
| `description` | Small Text | No | Texto corto mostrado debajo del label en la tarjeta del portal. `translatable=1`. Description: "Short explanation shown below the type name in the portal". |

---

## Permisos

| Rol | Read | Write | Create | Delete | Email | Export | Print | Report | Share |
|---|---|---|---|---|---|---|---|---|---|
| System Manager | sí | sí | sí | sí | sí | sí | sí | sí | sí |
| PQR Manager | sí | sí | sí | sí | sí | sí | sí | sí | sí |
| PQR Agent | sí | — | — | — | — | — | — | — | — |

`PQR Agent` solo puede leer el catálogo (necesario para que se le rendericen tipos en cualquier vista o reporte).

---

## Validaciones

- `type_code` es `unique=1` y `reqd=1` → no se pueden crear dos tipos con el mismo código.
- `label` es `reqd=1`.
- Naming por expresión: el `name` del doc se setea desde `type_code`, por lo que es inmutable a menos que se renombre (`allow_rename=1`).
- `is_active=0` no impide tener el doc, pero lo excluye de las tools del portal (filtrado en API).

---

## Tipos pre-cargados (fixture)

Archivo: `pqr_management/fixtures/pqr_type.json`. Se sincronizan via `bench migrate` (filtro en `hooks.py:34-39`).

| `name` | `label` | `icon` | `color` | `display_order` | `description` |
|---|---|---|---|---|---|
| `peticion` | Petición | `MessageSquare` | `#2563eb` | 10 | "Solicita información, gestión o acción de la entidad sobre un tema de tu interés." |
| `queja` | Queja | `AlertCircle` | `#dc2626` | 20 | "Manifiesta tu inconformidad por la atención recibida o un servicio mal prestado." |
| `reclamo` | Reclamo | `AlertTriangle` | `#ea580c` | 30 | "Reporta una falla específica para que sea corregida o reparada." |
| `sugerencia` | Sugerencia | `Lightbulb` | `#ca8a04` | 40 | "Propone una mejora o idea que ayude a brindar un mejor servicio." |
| `felicitacion` | Felicitación | `Heart` | `#16a34a` | 50 | "Reconoce un buen servicio, atención destacada o experiencia positiva." |
| `denuncia` | Denuncia | `ShieldAlert` | `#7c3aed` | 60 | "Reporta una situación irregular, posible falta ética o presunto acto de corrupción." |

Todos quedan con `is_active=1`.

---

## Cómo crear un nuevo tipo

Desde el Desk: **PQRs > PQR Type > New**.

Mínimo:

- `type_code`: identificador `snake_case` único (ej. `solicitud_acceso_info`).
- `label`: nombre visible (ej. "Solicitud de acceso a la información").

Opcionales:

- `icon`: cualquier nombre Lucide (`FileText`, `Mail`, etc.).
- `color`: hexadecimal.
- `description`: explicación corta.
- `display_order`: para reordenar.

Luego, en la `Service Portal Tool` con `tool_type='pqr'` correspondiente, añadir una fila a `pqr_allowed_types` apuntando al nuevo tipo (`is_enabled=1`).

---

## Controlador Python

`pqr_management/pqr_management/doctype/pqr_type/pqr_type.py:1-9`

```python
from frappe.model.document import Document

class PQRType(Document):
    pass
```

Sin lógica custom: validaciones y naming las gestiona Frappe a partir del JSON.
