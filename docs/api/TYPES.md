# API: Types (`pqr_management.api.types`)

Endpoints para **consultar el catálogo** de `PQR Type`. Archivos:

- `pqr_management/api/types/endpoints.py`
- `pqr_management/api/types/__init__.py`

Ambos endpoints son `allow_guest=True` porque el ciudadano puede llegar al portal sin sesión (debe poder ver los tipos antes de elegir si enviar como anónimo o iniciar sesión).

| Endpoint | Método | Rate limit | Token requerido |
|---|---|---|---|
| `pqr_management.api.types.get_tool_types` | GET | 60/60s | no |
| `pqr_management.api.types.get_all_types` | GET | 60/60s | no |

---

## `get_tool_types`

```python
@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_tool_types(tool_name: str) -> Dict[str, Any]:
```

(`endpoints.py:14-74`)

Devuelve los `PQR Type`s habilitados en un `Service Portal Tool` específico, junto con el flag de anonimato (`pqr_allow_anonymous`).

### Argumentos

| Arg | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `tool_name` | str | **sí** | El `name` del `Service Portal Tool` (la fila child dentro del `Service Portal`, su `name` aleatorio). Sanitizado a 140 chars. |

### Lógica interna

1. `check_rate_limit("pqr_get_tool_types", limit=60, seconds=60)`.
2. `sanitize_string(tool_name, 140)`.
3. Si `tool_name` está vacío → `ValidationError`.
4. `frappe.db.get_value("Service Portal Tool", tool_name, ["tool_type", "pqr_allow_anonymous"], as_dict=True)`.
5. Si no existe → `DoesNotExistError` "Service Portal Tool not found".
6. Si `tool.tool_type != "pqr"` → `ValidationError` "This tool is not a PQR tool".
7. Lee filas de `PQR Tool Type` con `parent=tool_name, is_enabled=1`.
8. Si no hay filas → devuelve `{"allow_anonymous": ..., "types": []}`.
9. Resuelve los datos completos de cada `PQR Type` filtrando además por `is_active=1`.
10. Ordena por `display_order ASC`.

### Respuesta

```json
{
  "message": {
    "allow_anonymous": true,
    "types": [
      {
        "name": "peticion",
        "type_code": "peticion",
        "label": "Petición",
        "description": "Solicita información, gestión o acción de la entidad sobre un tema de tu interés.",
        "icon": "MessageSquare",
        "color": "#2563eb",
        "display_order": 10
      },
      {
        "name": "queja",
        "type_code": "queja",
        "label": "Queja",
        "description": "Manifiesta tu inconformidad por la atención recibida o un servicio mal prestado.",
        "icon": "AlertCircle",
        "color": "#dc2626",
        "display_order": 20
      }
    ]
  }
}
```

### Ejemplo curl

```bash
curl -X GET 'https://tu-sitio.com/api/method/pqr_management.api.types.get_tool_types?tool_name=abc123xyz' \
  -H 'Accept: application/json'
```

> El `tool_name` se obtiene normalmente del frontend, que recibe los `tools` del portal en la respuesta de `common_configurations.api.portals.get_portal`. El componente Angular `PqrToolComponent.ngOnInit()` lee `(tool as any).name` y lo pasa aquí (`pqr-tool.component.ts:104-116`).

### Errores

| Caso | Exception | Mensaje |
|---|---|---|
| `tool_name` vacío | `ValidationError` | "Tool name is required" |
| Tool no existe | `DoesNotExistError` | "Service Portal Tool not found" |
| Tool no es PQR | `ValidationError` | "This tool is not a PQR tool" |
| Rate limit excedido | — | depende de `common_configurations` |

---

## `get_all_types`

```python
@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_all_types() -> List[Dict[str, Any]]:
```

(`endpoints.py:77-87`)

Devuelve **todos** los `PQR Type` activos. Usado por selectors internos o vistas administrativas.

### Argumentos

Sin argumentos.

### Lógica interna

1. `check_rate_limit("pqr_get_all_types", limit=60, seconds=60)`.
2. `frappe.get_all("PQR Type", filters={"is_active": 1}, fields=[...], order_by="display_order asc")`.

### Respuesta

```json
{
  "message": [
    {
      "name": "peticion",
      "type_code": "peticion",
      "label": "Petición",
      "description": "Solicita información...",
      "icon": "MessageSquare",
      "color": "#2563eb",
      "display_order": 10
    },
    // ... resto de tipos activos
  ]
}
```

### Ejemplo curl

```bash
curl -X GET 'https://tu-sitio.com/api/method/pqr_management.api.types.get_all_types' \
  -H 'Accept: application/json'
```

### Errores

| Caso | Exception | Mensaje |
|---|---|---|
| Rate limit excedido | — | depende de `common_configurations` |

---

## Diferencia entre los dos endpoints

| Aspecto | `get_tool_types(tool_name)` | `get_all_types()` |
|---|---|---|
| Filtra por configuración del portal | sí (lee child table `pqr_allowed_types`) | no |
| Devuelve flag `allow_anonymous` | sí | no |
| Devuelve solo tipos activos | sí | sí |
| Necesita un `tool_name` | sí | no |
| Pensado para | Frontend del portal (Angular) | Vistas internas / selectors |

El frontend del portal **siempre** usa `get_tool_types`, nunca `get_all_types`.
