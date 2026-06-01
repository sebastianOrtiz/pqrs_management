# Feature: Sistema de PQR Anónimas

`pqr_management` soporta envío anónimo de PQRs de forma nativa. Existen **tres casos** distintos a manejar, todos resueltos por el endpoint del portal y reforzados por el controlador del DocType.

---

## El campo clave: `is_anonymous`

`PQR Entry` tiene un campo `is_anonymous` (Check, default `0`) y un controlador (`pqr_entry.py:15-24`) que aplica la siguiente regla en `validate()`:

```python
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
```

Esto significa que **incluso si alguien intenta forzar valores en esos campos al crear/editar**, el `validate` los limpia antes de persistir. La PQR queda sin rastro del remitente.

---

## Caso 1: Anónimo explícito (usuario autenticado opta por anonimato)

**Escenario**: el ciudadano está logueado en el portal (tiene `X-User-Contact-Token` válido) y marca el checkbox "Enviar de forma anónima".

**Precondiciones del frontend** (`pqr-tool.component.html:131-147`):

- `!isAnonymousUser()` (está logueado).
- `allowAnonymous()` (`pqr_allow_anonymous=1` en la `Service Portal Tool`).

Solo bajo estas dos condiciones aparece el checkbox `sendAsAnonymous`.

**Llamada**:

```bash
curl -X POST '/api/method/pqr_management.api.entries.create_entry_from_portal' \
  -H 'X-User-Contact-Token: TOKEN' \
  --data-urlencode 'pqr_type=denuncia' \
  --data-urlencode 'subject=...' \
  --data-urlencode 'description=...' \
  --data-urlencode 'is_anonymous=1'
```

**Comportamiento del endpoint** (`endpoints.py:133-145`):

```python
is_anonymous_bool = bool(int(is_anonymous)) if is_anonymous else False
# is_anonymous_bool = True

if not is_anonymous_bool:
    authenticated_contact = get_current_user_contact()
    ...
# (no entra aquí porque is_anonymous_bool=True)

# user_contact queda en None
```

**Resultado en BD**:

- `is_anonymous = 1`
- `user_contact = NULL` (aunque la request iba con token)
- `submitter_name = NULL`, `submitter_email = NULL`, `submitter_phone = NULL`
- `source = "portal"`
- `status = "New"`

**Consecuencias**:

- La PQR **no aparece** en `get_my_pqr` (filtra por `is_anonymous: 0`).
- La PQR **no se puede consultar** en `get_pqr_detail` (`endpoints.py:241-242` lanza `PermissionError` si `is_anonymous` o si `user_contact != authenticated_contact`).
- El ciudadano pierde la capacidad de hacer seguimiento — esto se comunica explícitamente en el frontend: "Si marcas esta opción, tu identidad no quedará asociada a la PQR. No podrás consultar el estado después." (`pqr-tool.component.html:142-145`).

---

## Caso 2: Anónimo automático (visitante sin sesión)

**Escenario**: el ciudadano llega al portal sin haberse autenticado. No tiene `X-User-Contact-Token`.

**Estado del frontend**:

- `isAnonymousUser()=true`.
- Si `pqr_allow_anonymous=0` en la `Service Portal Tool`, el componente muestra error "Esta herramienta requiere iniciar sesión." y bloquea (`pqr-tool.component.ts:124-126`).
- Si `pqr_allow_anonymous=1`, se muestra un aviso visual "Estás enviando como anónimo" (`pqr-tool.component.html:150-162`) con CTA opcional para registrarse.

**Comportamiento del frontend al enviar** (`pqr-tool.component.ts:160`):

```typescript
const isAnonymous = this.isAnonymousUser() ? true : this.sendAsAnonymous();
```

Si el usuario es anónimo, **siempre** envía `is_anonymous=1`.

**Llamada**:

```bash
curl -X POST '/api/method/pqr_management.api.entries.create_entry_from_portal' \
  --data-urlencode 'pqr_type=sugerencia' \
  --data-urlencode 'subject=...' \
  --data-urlencode 'description=...' \
  --data-urlencode 'is_anonymous=1'
```

**Comportamiento del endpoint**: idéntico al Caso 1 — `is_anonymous_bool=True` desde el inicio.

**Backup del backend**: aunque por error la request llegara con `is_anonymous=0` y sin token, el endpoint **fuerza** anonimato (`endpoints.py:139-145`):

```python
user_contact = None
if not is_anonymous_bool:
    authenticated_contact = get_current_user_contact()
    if authenticated_contact:
        user_contact = authenticated_contact
    else:
        is_anonymous_bool = True  # ← fuerza a anónimo
```

Esto garantiza que **nunca** se cree una PQR no-anónima sin `user_contact`, lo cual sería un estado inconsistente.

**Resultado en BD**: exactamente igual al Caso 1.

---

## Caso 3: Autenticada normal (asociada al `user_contact`)

**Escenario**: el ciudadano está logueado y no marca el checkbox anónimo (o no le aparece el checkbox porque el tool no permite anonimato).

**Llamada**:

```bash
curl -X POST '/api/method/pqr_management.api.entries.create_entry_from_portal' \
  -H 'X-User-Contact-Token: TOKEN' \
  --data-urlencode 'pqr_type=peticion' \
  --data-urlencode 'subject=...' \
  --data-urlencode 'description=...' \
  --data-urlencode 'is_anonymous=0'
```

**Comportamiento del endpoint**:

1. `is_anonymous_bool=False`.
2. `get_current_user_contact()` → devuelve el `User contact` (ej. `UC-00042`).
3. `user_contact = "UC-00042"`.
4. `_build_pqr_entry(...)`:
   - `doc.user_contact = "UC-00042"`.
   - `doc.is_anonymous = 0`.

**Resultado en BD**:

- `is_anonymous = 0`
- `user_contact = "UC-00042"`
- `submitter_name`, `submitter_email`, `submitter_phone` se persisten **solo si llegaron como argumentos** (no se autopopulan del `User contact`).
- `source = "portal"`, `status = "New"`.

**Consecuencias**:

- Aparece en `get_my_pqr` del contacto.
- Se puede consultar en `get_pqr_detail`.
- El ciudadano hace seguimiento de su PQR completamente.

---

## Diagrama de decisión

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend recibe envío de PQR                                    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │ isAnonymousUser() (no token)?   │
              └─┬───────────────────────────┬───┘
                │ sí                        │ no
                ▼                           ▼
       ┌─────────────────┐         ┌────────────────────┐
       │ allowAnonymous? │         │ sendAsAnonymous?   │
       └─┬──────────┬────┘         └──┬─────────────┬───┘
         │ no       │ sí              │ sí          │ no
         ▼          ▼                 ▼             ▼
   ┌──────────┐ ┌──────────┐    ┌──────────┐  ┌──────────┐
   │ Bloquea  │ │ Caso 2:  │    │ Caso 1:  │  │ Caso 3:  │
   │ "requiere│ │ anónimo  │    │ anónimo  │  │ asociada │
   │  login"  │ │ auto     │    │ explícito│  │ al token │
   └──────────┘ └────┬─────┘    └────┬─────┘  └────┬─────┘
                    │                │             │
                    └────────────────┴─────────────┘
                                  │
                                  ▼
                       Endpoint /api/.../create_entry_from_portal
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
        is_anonymous=1    is_anonymous=1    is_anonymous=0
        sin token         sin token         con token
                │                 │                 │
                └─────────┬───────┘                 │
                          ▼                         ▼
              user_contact = None       user_contact = authenticated
              is_anonymous = True       is_anonymous = False
                          │                         │
                          └────────────┬────────────┘
                                       ▼
                          doc.validate() (controlador):
                            si is_anonymous → limpia campos
                                       │
                                       ▼
                                  PQR creada
```

---

## Filtrado en endpoints de lectura

Una PQR anónima **nunca** se devuelve por los endpoints de lectura del portal:

### `get_my_pqr` (`endpoints.py:178`)

```python
filters = {"user_contact": user_contact, "is_anonymous": 0}
```

El filtro `is_anonymous: 0` es redundante (las anónimas tienen `user_contact=NULL`, no harían match contra el `user_contact` autenticado), pero es **defensa en profundidad**.

### `get_pqr_detail` (`endpoints.py:241-242`)

```python
if pqr.is_anonymous or pqr.user_contact != user_contact:
    frappe.throw(_("Not authorized to view this PQR"), frappe.PermissionError)
```

Check explícito: aunque alguien adivine un `pqr_name` válido, si la PQR es anónima no se puede consultar nunca por esta vía.

---

## ¿Cómo se gestionan las anónimas internamente?

Una vez creadas, las PQR anónimas se gestionan desde el Desk igual que cualquier otra:

- `PQR Manager` y `System Manager` ven todas (incluyendo anónimas).
- `PQR Agent` ve las que tenga asignadas (`assigned_to`), aunque sean anónimas.
- El campo `is_anonymous` queda visible en la list view (`in_list_view=1`) para que el agente sepa que no debe contactar al remitente (no hay datos).

**No se pueden notificar resultados al ciudadano** (no hay email/teléfono). Si la entidad necesita responder, debe publicar la respuesta por otra vía (cartelera, web pública, etc.).

---

## Resumen comparativo

| Aspecto | Caso 1 (anónimo explícito) | Caso 2 (anónimo automático) | Caso 3 (autenticada normal) |
|---|---|---|---|
| Token enviado | sí | no | sí |
| `is_anonymous` recibido | `1` | `1` (o cualquiera) | `0` |
| `user_contact` final | `NULL` | `NULL` | el del token |
| `submitter_*` finales | `NULL` | `NULL` | lo que se haya enviado |
| Aparece en `get_my_pqr` | no | no | sí |
| Accesible en `get_pqr_detail` | no | no | sí (si pertenece al token) |
| `pqr_allow_anonymous=0` lo permite | no (UI lo oculta) | no (UI bloquea) | sí |
