# Feature: Permisos por rol

`pqr_management` define **2 roles propios** y aplica un sistema de **permisos custom** sobre `PQR Entry` que combina los permisos declarativos del DocType con dos hooks de Frappe:

- `permission_query_conditions["PQR Entry"]` — filtra listados/reportes.
- `has_permission["PQR Entry"]` — autoriza acceso a documentos individuales.

Ambos hooks se declaran en `pqr_management/hooks.py:48-54` y se implementan en `pqr_management/pqr_management/doctype/pqr_entry/pqr_entry.py:32-65`.

---

## Roles propios

Definidos en `pqr_management/fixtures/role.json`:

| Rol | `desk_access` | Pensado para |
|---|---|---|
| `PQR Manager` | 1 | Administradores/líderes del área PQR. Ven y editan todo. |
| `PQR Agent` | 1 | Agentes/funcionarios que trabajan las PQRs asignadas a ellos. Solo ven lo suyo. |

Adicionalmente, **`System Manager`** (rol estándar de Frappe) tiene siempre acceso total.

---

## Permisos declarativos (JSON del DocType)

### PQR Entry (`pqr_entry.json:193-228`)

| Rol | read | write | create | delete | email | export | print | report | share |
|---|---|---|---|---|---|---|---|---|---|
| System Manager | sí | sí | sí | sí | sí | sí | sí | sí | sí |
| PQR Manager | sí | sí | sí | sí | sí | sí | sí | sí | sí |
| PQR Agent | sí | sí | **NO** | — | sí | sí | sí | sí | sí |

> `PQR Agent` puede leer y editar pero **no crear desde el Desk**. Esto es deliberado: los agentes solo trabajan PQRs que llegan por el portal o por el API externo.

### PQR Type (`pqr_type.json:96-125`)

| Rol | read | write | create | delete |
|---|---|---|---|---|
| System Manager | sí | sí | sí | sí |
| PQR Manager | sí | sí | sí | sí |
| PQR Agent | sí | — | — | — |

> Agente solo puede leer el catálogo (para que se le rendericen filtros y referencias).

### PQR Tool Type

No tiene permisos directos (`"permissions": []`). Al ser child table, hereda del padre (`Service Portal Tool`, gestionado por `common_configurations`).

---

## Hooks de permiso (`pqr_entry.py`)

### `get_permission_query_conditions(user)` — filtra listados

`pqr_entry.py:32-50`

```python
def get_permission_query_conditions(user):
    """
    Limit visibility of PQR Entry:
    - System Manager / PQR Manager: see all
    - PQR Agent: see only entries assigned to them
    - Other users: no access
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    if "System Manager" in roles or "PQR Manager" in roles:
        return ""

    if "PQR Agent" in roles:
        return f"`tabPQR Entry`.assigned_to = {frappe.db.escape(user)}"

    return "1=0"
```

Comportamiento:

| Rol del usuario | Retorno | Efecto |
|---|---|---|
| `System Manager` o `PQR Manager` | `""` | Sin filtro: ve todos los registros. |
| `PQR Agent` | ``f"`tabPQR Entry`.assigned_to = '{user}'"`` | Solo ve los asignados a él. |
| Cualquier otro | `"1=0"` | Cláusula imposible → no ve nada. |

Aplica en list views, reportes y queries que respeten permisos.

### `has_permission(doc, ptype, user)` — autoriza por documento

`pqr_entry.py:53-65`

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

Comportamiento:

| Rol del usuario | Retorno |
|---|---|
| `System Manager` o `PQR Manager` | `True` (acceso total) |
| `PQR Agent` | `True` si `doc.assigned_to == user`, `False` en caso contrario |
| Otro | `False` |

---

## Matriz combinada

| Acción | System Manager | PQR Manager | PQR Agent (asignado) | PQR Agent (no asignado) | Otro usuario |
|---|---|---|---|---|---|
| Ver lista de PQRs en el Desk | Todas | Todas | Solo las asignadas | (no ve) | (no ve) |
| Abrir una PQR específica | sí | sí | sí (si `assigned_to=él`) | NO (`PermissionError`) | NO |
| Editar PQR | sí | sí | sí (si asignado) | NO | NO |
| Crear PQR desde el Desk | sí | sí | **NO** (JSON `create=0`) | NO | NO |
| Borrar PQR | sí | sí | NO | NO | NO |
| Crear PQR desde portal (cualquiera) | sí | sí | sí | sí | sí (anónima si no autenticado) |
| Ver `PQR Type` (catálogo) | sí | sí | sí | sí | NO |
| Editar `PQR Type` | sí | sí | NO | NO | NO |

---

## Excepción: creación desde portal y API externa

Los endpoints públicos del portal (`create_entry_from_portal`) y de la API externa (`create_pqr`) crean el `PQR Entry` con `doc.insert(ignore_permissions=True)` (`entries/endpoints.py:92`). Por tanto:

- El **rol del usuario que llama no importa** — la creación queda mediada por el token (`X-User-Contact-Token`) o la API Key (`X-API-Key`), no por rol.
- Esto permite que **ciudadanos sin rol** (`User contact` no tiene rol Frappe) creen PQRs sin que `has_permission` los bloquee.

Lo que sí aplica al crear:

- Rate limit por IP (`check_rate_limit`).
- Honeypot (`check_honeypot`).
- Validación de tipo (`_validate_pqr_inputs`).
- Sanitización (`sanitize_string`).
- Decorador `@require_api_key("enable_create_pqr")` en el endpoint externo.

---

## Sugerencias operativas

1. **Asignar rol `PQR Manager`** al líder del área. Verán todo y podrán mover estados.
2. **Asignar rol `PQR Agent`** a cada funcionario que tramite PQRs. Su lista solo mostrará lo que tienen asignado.
3. Establecer en cada PQR un `assigned_to` para que llegue al agente correcto. Sin `assigned_to`, ningún `PQR Agent` la verá.
4. Los reportes filtran automáticamente por `get_permission_query_conditions`. Si un Manager arma un reporte, lo verán todos; si un Agent lo ejecuta, solo verá los suyos.

---

## Auditoría

`PQR Entry` tiene `track_changes=1` (`pqr_entry.json:236`). Cualquier cambio queda registrado en la timeline del doc y en `tabVersion`. Esto permite auditar:

- Cambios de `status`.
- Cambios de `assigned_to`.
- Edición de `resolution`.
- Edición de cualquier campo.

Las creaciones vía API externa quedan adicionalmente en `frappe.logger().info()` (`external/endpoints.py:78-81`):

```python
frappe.logger().info(
    f"PQR {result['name']} created via API "
    f"(service: {service_info['service_title']}, type: {pqr_type})"
)
```
