# DocType: PQR Tool Type

Child table que enlaza **un `PQR Type` a una `Service Portal Tool`** con un flag `is_enabled`. Configura qué tipos de PQR se ofrecen al ciudadano en cada instancia del portal.

- Archivo JSON: `pqr_management/pqr_management/doctype/pqr_tool_type/pqr_tool_type.json`
- Controlador Python: `pqr_management/pqr_management/doctype/pqr_tool_type/pqr_tool_type.py` (clase vacía `pass`)
- **istable**: `1` (es child table, no se instancia sola).
- **Naming rule**: `Random` (Frappe genera un nombre aleatorio para cada fila).
- **Módulo**: Pqr Management.
- **Ordenamiento por defecto**: `modified DESC`.

---

## Propósito y casos de uso

Es la child table del custom field `Service Portal Tool-pqr_allowed_types` (`fixtures/custom_field.json:3-16`). Cada `Service Portal Tool` con `tool_type='pqr'`:

- Tiene una colección de filas `PQR Tool Type` en `pqr_allowed_types`.
- Cada fila apunta a un `PQR Type` y dice si está habilitado.
- El endpoint `pqr_management.api.types.get_tool_types` lee esta tabla y devuelve solo las filas con `is_enabled=1`.

Esto permite que diferentes portales (o diferentes "tools" del mismo portal) ofrezcan distintos subconjuntos de tipos al ciudadano. Por ejemplo: un portal interno podría aceptar solo `denuncia`, mientras que el público acepta los 6 tipos.

---

## Estructura de la vista

```
Row:
  pqr_type (Link → PQR Type) [reqd] | is_enabled (Check, default 1)
```

---

## Campos uno por uno

| Campo | Tipo | Obligatorio | Default | Opciones | Notas |
|---|---|---|---|---|---|
| `pqr_type` | Link | **Sí** | — | options `PQR Type` | El tipo de PQR a habilitar en esta tool. `in_list_view=1`. |
| `is_enabled` | Check | No | `1` | — | Habilitar/deshabilitar este tipo sin removerlo de la lista. `in_list_view=1`. Si está en `0`, no se incluye en la respuesta de `get_tool_types`. |

> No hay campos adicionales: no se permite override de `label`, `color`, etc. por tool — esos datos vienen siempre del `PQR Type` enlazado.

---

## Permisos

El JSON declara `"permissions": []` (vacío). Por ser una child table (`istable=1`), Frappe gestiona el acceso a través de la tabla padre (`Service Portal Tool`). No hay permisos directos.

---

## Cómo se usa

Desde el Desk:

1. Abrir `Service Portal > Service Portal Tool` con `tool_type='pqr'`.
2. La sección **PQR Allowed Types** aparece (`depends_on: eval:doc.tool_type=='pqr'`).
3. Añadir filas: cada una con un `pqr_type` y `is_enabled`.

Desde el backend, ejemplo de consulta:

```python
rows = frappe.get_all(
    "PQR Tool Type",
    filters={"parent": tool_name, "is_enabled": 1},
    fields=["pqr_type"],
)
```

(Ver `api/types/endpoints.py:54-58`.)

---

## Controlador Python

`pqr_management/pqr_management/doctype/pqr_tool_type/pqr_tool_type.py:1-9`

```python
from frappe.model.document import Document

class PQRToolType(Document):
    pass
```

Sin lógica custom.

---

## Relación con el custom field

El custom field `Service Portal Tool-pqr_allowed_types` (declarado en `pqr_management/fixtures/custom_field.json:2-16` y en `install.py:32-43`) es:

```json
{
    "dt": "Service Portal Tool",
    "fieldname": "pqr_allowed_types",
    "fieldtype": "Table",
    "options": "PQR Tool Type",
    "label": "PQR Allowed Types",
    "insert_after": "is_enabled",
    "depends_on": "eval:doc.tool_type=='pqr'",
    "mandatory_depends_on": "eval:doc.tool_type=='pqr'"
}
```

Esto significa que:

- El campo solo aparece (`depends_on`) y solo es obligatorio (`mandatory_depends_on`) cuando la tool es de tipo `pqr`.
- Es obligatorio: una tool de tipo `pqr` debe tener al menos una fila configurada para poder guardarse.
