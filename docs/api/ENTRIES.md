# API: Entries (`pqr_management.api.entries`)

Endpoints HTTP whitelisted del módulo `entries`, expuestos para el **Service Portal** (Angular SPA). Todos viven en `pqr_management/api/entries/endpoints.py` y se re-exportan en `pqr_management/api/entries/__init__.py`.

- Acceso: `allow_guest=True` en los 3 endpoints (el portal puede consumirlos sin sesión Frappe).
- Autenticación: header `X-User-Contact-Token` con un token válido emitido a un `User contact` (gestionado por `common_configurations.api.shared.get_current_user_contact`).
- Rate limit por IP (ver tabla).
- Protección anti-bot: campo `honeypot` (debe ir vacío) en los `POST`.
- Sanitización: `sanitize_string(text, max_length)` de `common_configurations.api.shared` se aplica a todos los inputs antes de persistir.

| Endpoint | Método | Rate limit | Token requerido | Honeypot |
|---|---|---|---|---|
| `pqr_management.api.entries.create_entry_from_portal` | POST | 5/60s | opcional (define anonimato) | sí |
| `pqr_management.api.entries.get_my_pqr` | GET | 30/60s | **obligatorio** | — |
| `pqr_management.api.entries.get_pqr_detail` | GET | 30/60s | **obligatorio** | — |

Utilidades importadas (`endpoints.py:17-22`):

- `check_rate_limit(name, limit, seconds)` — bloquea si la IP excedió el rate.
- `check_honeypot(value)` — bloquea si `value` no está vacío.
- `get_current_user_contact()` — devuelve el `User contact` autenticado por `X-User-Contact-Token`, o `None` si no hay token válido.
- `sanitize_string(text, max_length)` — recorta/normaliza inputs.

---

## Autenticación

Las llamadas de **lectura** (`get_my_pqr`, `get_pqr_detail`) requieren:

```
X-User-Contact-Token: <token-emitido-al-user-contact>
```

Si falta o es inválido:

```json
{"exc_type": "AuthenticationError", "message": "Authentication required"}
```

La llamada de **creación** (`create_entry_from_portal`) puede ir con o sin token:

- **Con token y `is_anonymous=0`** → se asocia `user_contact`.
- **Con token y `is_anonymous=1`** → se ignora el token, se guarda anónima (los campos del submitter se limpian en `validate()`).
- **Sin token** → el endpoint fuerza `is_anonymous=True` aunque no se haya enviado el flag (`endpoints.py:144-145`).

Ver [features/ANONYMOUS_PQR.md](../features/ANONYMOUS_PQR.md) para el detalle.

---

## Constantes de validación

`endpoints.py:29-32`

| Constante | Valor | Aplica a |
|---|---|---|
| `MAX_SUBJECT_LEN` | 200 | `subject` |
| `MAX_DESCRIPTION_LEN` | 10 000 | `description` |
| `MAX_NAME_LEN` | 140 | `submitter_name`, `submitter_email`, `pqr_name` |
| `MAX_PHONE_LEN` | 30 | `submitter_phone` |

---

## `create_entry_from_portal`

```python
@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_entry_from_portal(
    pqr_type: str,
    subject: str,
    description: str,
    is_anonymous: int = 0,
    submitter_name: Optional[str] = None,
    submitter_email: Optional[str] = None,
    submitter_phone: Optional[str] = None,
    honeypot: Optional[str] = None,
) -> Dict[str, Any]:
```

(`endpoints.py:109-163`)

Crea una `PQR Entry` desde el Service Portal.

### Argumentos

| Arg | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `pqr_type` | str | **sí** | `name` del `PQR Type` (ej. `peticion`, `queja`). Debe existir y estar `is_active=1`. |
| `subject` | str | **sí** | Asunto. Max 200 chars (recortado). |
| `description` | str | **sí** | Cuerpo. Max 10 000 chars. |
| `is_anonymous` | int | no | `0` (default) o `1`. Convertido a bool con `bool(int(is_anonymous))`. |
| `submitter_name` | str | no | Nombre del remitente. Solo si `is_anonymous=0`. Max 140 chars. |
| `submitter_email` | str | no | Email. Solo si `is_anonymous=0`. Max 140 chars (el código usa `MAX_NAME_LEN`). |
| `submitter_phone` | str | no | Teléfono. Solo si `is_anonymous=0`. Max 30 chars. |
| `honeypot` | str | no | Debe ir **vacío**. Si llega con contenido, bloquea la request. |

### Lógica interna

1. `check_rate_limit("pqr_create_entry", limit=5, seconds=60)` (`endpoints.py:130`).
2. `check_honeypot(honeypot)` (`endpoints.py:131`).
3. `_validate_pqr_inputs(pqr_type, subject, description)` (`endpoints.py:135`):
   - Lanza `ValidationError` si vacíos.
   - Lanza `DoesNotExistError` si `pqr_type` no existe.
   - Lanza `ValidationError` si `is_active=0`.
4. Si `is_anonymous=0`:
   - Llama `get_current_user_contact()`.
   - Si hay contact → `user_contact = authenticated_contact`.
   - **Si no hay contact** → **fuerza** `is_anonymous=True` (clave del sistema).
5. `_build_pqr_entry(...)` (`endpoints.py:58-102`):
   - Crea el doc, sanitiza strings, setea `source="portal"`, `status="New"`, `received_at=now_datetime()`.
   - Si no es anónima, asocia `user_contact` y campos del submitter.
   - `doc.insert(ignore_permissions=True)` + `frappe.db.commit()`.

### Respuesta

```json
{
  "message": {
    "name": "PQR-2026-00001",
    "pqr_type": "queja",
    "subject": "Mal servicio en taquilla 3",
    "status": "New",
    "received_at": "2026-05-18 14:32:11",
    "is_anonymous": false
  }
}
```

### Errores

| Caso | Exception | Mensaje |
|---|---|---|
| `pqr_type` vacío | `ValidationError` | "PQR type is required" |
| `subject` vacío | `ValidationError` | "Subject is required" |
| `description` vacía | `ValidationError` | "Description is required" |
| `pqr_type` no existe | `DoesNotExistError` | "PQR type '<x>' not found" |
| `pqr_type` inactivo | `ValidationError` | "PQR type '<x>' is not active" |
| Rate limit excedido | (manejado por `check_rate_limit`) | depende de `common_configurations` |
| Honeypot lleno | (manejado por `check_honeypot`) | depende de `common_configurations` |
| Error inesperado al insertar | `ValidationError` | "Error creating PQR" (loggeado en `Error Log` con título `PQR Portal Create`) |

### Ejemplo curl: **autenticado** (PQR asociada)

```bash
curl -X POST 'https://tu-sitio.com/api/method/pqr_management.api.entries.create_entry_from_portal' \
  -H 'X-User-Contact-Token: TU-TOKEN' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'pqr_type=queja' \
  --data-urlencode 'subject=Mal servicio en taquilla 3' \
  --data-urlencode 'description=El cajero fue grosero y no atendió mi consulta sobre el certificado.' \
  --data-urlencode 'is_anonymous=0' \
  --data-urlencode 'honeypot='
```

### Ejemplo curl: **anónimo explícito** (logueado pero opta por anónimo)

```bash
curl -X POST 'https://tu-sitio.com/api/method/pqr_management.api.entries.create_entry_from_portal' \
  -H 'X-User-Contact-Token: TU-TOKEN' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'pqr_type=denuncia' \
  --data-urlencode 'subject=Presunto soborno en la oficina X' \
  --data-urlencode 'description=Vi al funcionario Y recibir dinero a cambio de agilizar un trámite.' \
  --data-urlencode 'is_anonymous=1' \
  --data-urlencode 'honeypot='
```

> Aunque vaya el token, al ir `is_anonymous=1` el endpoint **no** asocia `user_contact`. El doc se guarda con `is_anonymous=1`, sin nombre, email, ni teléfono.

### Ejemplo curl: **sin sesión** (anónimo automático)

```bash
curl -X POST 'https://tu-sitio.com/api/method/pqr_management.api.entries.create_entry_from_portal' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'pqr_type=sugerencia' \
  --data-urlencode 'subject=Agregar más cajeros en horas pico' \
  --data-urlencode 'description=Recomiendo abrir más ventanillas entre 10am y 2pm.' \
  --data-urlencode 'is_anonymous=0' \
  --data-urlencode 'honeypot='
```

> Aunque `is_anonymous=0`, al no haber token, el endpoint **fuerza** `is_anonymous=True` (`endpoints.py:144-145`). Es seguro: nunca se intenta asociar a un `user_contact` inexistente.

---

## `get_my_pqr`

```python
@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_my_pqr(status: Optional[str] = None) -> List[Dict[str, Any]]:
```

(`endpoints.py:166-220`)

Lista las PQRs del `user_contact` autenticado. **Anónimas nunca se devuelven**.

### Argumentos

| Arg | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `status` | str | no | Filtra por estado (`New`, `In Review`, `In Process`, `Resolved`, `Closed`, `Rejected`). Se sanitiza a 50 chars. |

### Lógica interna

1. `check_rate_limit("pqr_get_my", limit=30, seconds=60)`.
2. `get_current_user_contact()` → si no hay, lanza `AuthenticationError` con mensaje "Authentication required".
3. `frappe.get_all("PQR Entry", filters={"user_contact": user_contact, "is_anonymous": 0, [status]}, ...)`.
4. Enriquece cada fila con `pqr_type_label`, `pqr_type_color`, `pqr_type_icon` (consulta separada a `PQR Type`).
5. Convierte `received_at` y `resolved_at` a str.
6. Ordena por `received_at DESC`, `limit=200`.

### Respuesta

```json
{
  "message": [
    {
      "name": "PQR-2026-00012",
      "pqr_type": "queja",
      "pqr_type_label": "Queja",
      "pqr_type_color": "#dc2626",
      "pqr_type_icon": "AlertCircle",
      "subject": "Mal servicio en taquilla 3",
      "status": "In Process",
      "received_at": "2026-05-18 14:32:11",
      "resolved_at": null
    }
  ]
}
```

### Ejemplo curl

```bash
curl -X GET 'https://tu-sitio.com/api/method/pqr_management.api.entries.get_my_pqr' \
  -H 'X-User-Contact-Token: TU-TOKEN'
```

Con filtro de estado:

```bash
curl -X GET 'https://tu-sitio.com/api/method/pqr_management.api.entries.get_my_pqr?status=In%20Process' \
  -H 'X-User-Contact-Token: TU-TOKEN'
```

### Errores

| Caso | Exception | Mensaje |
|---|---|---|
| Sin token o token inválido | `AuthenticationError` | "Authentication required" |
| Rate limit excedido | — | depende de `common_configurations` |

---

## `get_pqr_detail`

```python
@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_pqr_detail(pqr_name: str) -> Dict[str, Any]:
```

(`endpoints.py:223-261`)

Detalle completo de una PQR. **Solo si pertenece** al `user_contact` autenticado y **no es anónima**.

### Argumentos

| Arg | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `pqr_name` | str | **sí** | `name` del `PQR Entry` (ej. `PQR-2026-00012`). Sanitizado a 140 chars. |

### Lógica interna

1. `check_rate_limit("pqr_get_detail", limit=30, seconds=60)`.
2. `get_current_user_contact()` → si no hay, lanza `AuthenticationError`.
3. `sanitize_string(pqr_name, 140)`.
4. `frappe.db.exists("PQR Entry", pqr_name)` → si no existe, lanza `DoesNotExistError`.
5. Carga el doc. Si `is_anonymous=1` **o** `user_contact != authenticated_contact` → `PermissionError` con mensaje "Not authorized to view this PQR".
6. Resuelve datos del `PQR Type` con `frappe.db.get_value`.
7. Devuelve el dict con todos los campos visibles (incluyendo `description` y `resolution`).

### Respuesta

```json
{
  "message": {
    "name": "PQR-2026-00012",
    "pqr_type": "queja",
    "pqr_type_label": "Queja",
    "pqr_type_color": "#dc2626",
    "pqr_type_icon": "AlertCircle",
    "subject": "Mal servicio en taquilla 3",
    "description": "El cajero fue grosero y no atendió mi consulta sobre el certificado.",
    "status": "Resolved",
    "received_at": "2026-05-18 14:32:11",
    "resolved_at": "2026-05-20 09:15:00",
    "resolution": "<p>Hemos abierto un caso disciplinario...</p>",
    "is_anonymous": false
  }
}
```

### Ejemplo curl

```bash
curl -X GET 'https://tu-sitio.com/api/method/pqr_management.api.entries.get_pqr_detail?pqr_name=PQR-2026-00012' \
  -H 'X-User-Contact-Token: TU-TOKEN'
```

### Errores

| Caso | Exception | Mensaje |
|---|---|---|
| Sin token | `AuthenticationError` | "Authentication required" |
| PQR no existe | `DoesNotExistError` | "PQR not found" |
| PQR anónima o de otro contacto | `PermissionError` | "Not authorized to view this PQR" |
| Rate limit excedido | — | depende de `common_configurations` |

---

## Resumen de seguridad

| Riesgo | Mitigación |
|---|---|
| Spam masivo | `check_rate_limit` por IP (5/60s en create, 30/60s en read) |
| Bots automatizados | `check_honeypot` (campo oculto que debe ir vacío) |
| Inputs maliciosos | `sanitize_string` con límites por campo |
| PQR de otro ciudadano | Filtros estrictos por `user_contact` en `get_my_pqr` y check de ownership en `get_pqr_detail` |
| PQR anónimas filtradas a otros | `is_anonymous: 0` en filtros + check explícito en `get_pqr_detail` |
| Creación con tipos inexistentes/inactivos | `_validate_pqr_inputs` valida ambos casos |
