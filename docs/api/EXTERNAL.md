# API: External (`pqr_management.api.external`)

Endpoint HTTP para **integraciones externas** (chatbots, apps móviles, sistemas terceros) autenticadas con **API Key** vía `X-API-Key`. La autenticación y la habilitación granular del endpoint se manejan a través del DocType `API Service` (definido en `common_configurations`) extendido con custom fields propios de `pqr_management`.

Archivos:

- `pqr_management/api/external/__init__.py`
- `pqr_management/api/external/endpoints.py`

| Endpoint | Método | Autenticación | Decorador |
|---|---|---|---|
| `pqr_management.api.external.create_pqr` | POST | `X-API-Key` | `@require_api_key("enable_create_pqr")` |

---

## Configuración del `API Service`

`pqr_management` añade dos custom fields al DocType `API Service` (definidos en `pqr_management/fixtures/custom_field.json:31-54` y filtrados como fixture en `hooks.py:25-32`):

| Fieldname | Tipo | Notas |
|---|---|---|
| `section_pqr` | Section Break | label `PQR Configuration`, `insert_after: enable_register_contact`. |
| `enable_create_pqr` | Check | default `0`. Habilita el endpoint `create_pqr` para esta `API Service`. |

> El decorador `@require_api_key("enable_create_pqr")` (de `common_configurations.api.shared`) valida que la `API Service` exista, esté activa, tenga la API Key correcta en `X-API-Key`, y tenga `enable_create_pqr=1`. En caso afirmativo, expone el doc en `frappe.local.api_service`.

Ejemplo de configuración (Desk → `API Service`):

```
- service_name: ChatbotMunicipalidad
- service_title: Chatbot Municipalidad
- api_key_hash: (generado al guardar)
- is_active: 1
- enable_register_contact: 0
- ── PQR Configuration ──
- enable_create_pqr: 1
```

---

## `create_pqr`

```python
@frappe.whitelist(allow_guest=True, methods=["POST"])
@require_api_key("enable_create_pqr")
def create_pqr(
    pqr_type: str,
    subject: str,
    description: str,
    user_contact: Optional[str] = None,
    is_anonymous: int = 0,
    submitter_name: Optional[str] = None,
    submitter_email: Optional[str] = None,
    submitter_phone: Optional[str] = None,
) -> Dict[str, Any]:
```

(`endpoints.py:23-92`)

Crea una `PQR Entry` desde un sistema externo.

### Argumentos

| Arg | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `pqr_type` | str | **sí** | `name` del `PQR Type` (ej. `queja`). Debe existir y estar `is_active=1`. |
| `subject` | str | **sí** | Asunto. Max 200 chars. |
| `description` | str | **sí** | Cuerpo. Max 10 000 chars. |
| `user_contact` | str | no | `name` de un `User contact` existente para asociar la PQR. Solo se usa si `is_anonymous=0`. Sanitizado a 140 chars. Validado con `frappe.db.exists`. |
| `is_anonymous` | int | no | `0` (default) o `1`. Si `1`, la PQR es anónima y se ignora `user_contact`. |
| `submitter_name` | str | no | Nombre del remitente. Solo si `is_anonymous=0`. Max 140 chars. |
| `submitter_email` | str | no | Email. Solo si `is_anonymous=0`. Max 140 chars. |
| `submitter_phone` | str | no | Teléfono. Solo si `is_anonymous=0`. Max 30 chars. |

> A diferencia del endpoint del portal, **no hay `honeypot`** (es un API Server-to-Server con clave) y la autenticación se basa exclusivamente en `X-API-Key`.

### Lógica interna

1. `@require_api_key("enable_create_pqr")` valida:
   - Header `X-API-Key` presente y correcto.
   - `API Service` existe y `is_active=1`.
   - `enable_create_pqr=1` en ese `API Service`.
   - Si pasa, popula `frappe.local.api_service`.
2. `is_anonymous_bool = bool(int(is_anonymous))`.
3. `_validate_pqr_inputs(pqr_type, subject, description)` (reutilizado de `entries.endpoints`):
   - Lanza `ValidationError` si vacíos.
   - Lanza `DoesNotExistError` si `pqr_type` no existe.
   - Lanza `ValidationError` si `is_active=0`.
4. Si `user_contact` y no anónimo:
   - `sanitize_string(user_contact, 140)`.
   - `frappe.db.exists("User contact", user_contact)` → `DoesNotExistError` si no existe.
5. Si `is_anonymous=1` o no llegó `user_contact` → `user_contact = None`.
6. `_build_pqr_entry(..., source="api")` crea el doc (`endpoints.py:65-76`).
7. Logger info: `f"PQR {result['name']} created via API (service: {service_title}, type: {pqr_type})"`.
8. En caso de excepción → loggea en `Error Log` con título `"Error creating PQR via API"` y lanza `ValidationError("Error creating PQR")`.

### Respuesta

```json
{
  "message": {
    "name": "PQR-2026-00045",
    "pqr_type": "queja",
    "subject": "Reporte vía chatbot",
    "status": "New",
    "received_at": "2026-05-18 16:02:33",
    "is_anonymous": false
  }
}
```

### Ejemplo curl: integración con `user_contact` existente

```bash
curl -X POST 'https://tu-sitio.com/api/method/pqr_management.api.external.create_pqr' \
  -H 'X-API-Key: TU-API-KEY' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'pqr_type=queja' \
  --data-urlencode 'subject=Reporte chatbot - falla servicio' \
  --data-urlencode 'description=El ciudadano reportó por WhatsApp que el servicio de aguas en la calle 23 está suspendido desde hace 3 días.' \
  --data-urlencode 'user_contact=UC-00042' \
  --data-urlencode 'is_anonymous=0'
```

### Ejemplo curl: integración anónima (sin asociar contacto)

```bash
curl -X POST 'https://tu-sitio.com/api/method/pqr_management.api.external.create_pqr' \
  -H 'X-API-Key: TU-API-KEY' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'pqr_type=denuncia' \
  --data-urlencode 'subject=Denuncia anónima recibida en buzón web' \
  --data-urlencode 'description=Texto reportado de forma anónima a través del formulario público.' \
  --data-urlencode 'is_anonymous=1'
```

### Ejemplo curl: registro con datos de submitter pero sin `user_contact`

```bash
curl -X POST 'https://tu-sitio.com/api/method/pqr_management.api.external.create_pqr' \
  -H 'X-API-Key: TU-API-KEY' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'pqr_type=peticion' \
  --data-urlencode 'subject=Solicitud de certificado' \
  --data-urlencode 'description=Necesito un certificado de residencia.' \
  --data-urlencode 'submitter_name=Juan Pérez' \
  --data-urlencode 'submitter_email=juan.perez@example.com' \
  --data-urlencode 'submitter_phone=+57 300 1234567' \
  --data-urlencode 'is_anonymous=0'
```

> En este caso no se asocia `user_contact` (porque no se envió) pero se guardan los datos del remitente directamente en `PQR Entry`.

---

## Errores

| Caso | Exception | Mensaje |
|---|---|---|
| Sin `X-API-Key` o inválida | (devuelto por `@require_api_key`) | depende de `common_configurations` |
| `API Service` desactivada | (devuelto por `@require_api_key`) | depende de `common_configurations` |
| `enable_create_pqr=0` | (devuelto por `@require_api_key`) | "This service does not allow create_pqr" (formato típico de `require_api_key`) |
| `pqr_type` vacío | `ValidationError` | "PQR type is required" |
| `subject` vacío | `ValidationError` | "Subject is required" |
| `description` vacía | `ValidationError` | "Description is required" |
| `pqr_type` no existe | `DoesNotExistError` | "PQR type '<x>' not found" |
| `pqr_type` inactivo | `ValidationError` | "PQR type '<x>' is not active" |
| `user_contact` no existe | `DoesNotExistError` | "User contact not found" |
| Error inesperado al insertar | `ValidationError` | "Error creating PQR" (con log en `Error Log`) |

---

## Notas y consideraciones

- No hay rate limit a nivel de endpoint (a diferencia del portal). La gestión queda delegada a `common_configurations` y/o capa de proxy. El control natural es la API Key + el flag `enable_create_pqr`.
- El endpoint reutiliza `_validate_pqr_inputs` y `_build_pqr_entry` de `entries.endpoints` (`endpoints.py:17-20`). Esto garantiza paridad de comportamiento entre portal y API externa (mismas sanitizaciones, mismos límites, mismo flujo).
- El `source` se setea a `"api"` (no a `"portal"`), lo que permite distinguir en reportes el origen.
- El logger registra el `service_title` (ej. "Chatbot Municipalidad"), útil para auditar qué integración creó cada PQR.
- La PQR creada vía API es **invisible** para `get_my_pqr` salvo que `user_contact` se asocie explícitamente y la PQR no sea anónima. Es decir, una integración puede crear PQRs vinculadas al `User contact` del ciudadano y este las verá luego en su portal.
