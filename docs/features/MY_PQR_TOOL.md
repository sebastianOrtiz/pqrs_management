# Feature: Tool del Portal `my_pqr` (Mis PQRs)

Tool del Service Portal que permite a un ciudadano **autenticado** consultar las PQRs que ha enviado y ver su estado/resolución.

- **Tool Type registrado**: `my_pqr` (fixture `pqr_management/fixtures/tool_type.json`)
- **Label**: `Mis PQRs`
- **Icon**: `Inbox` (Lucide)
- **Componente Angular**: `common_configurations/front_apps/service-portal/src/app/features/tools/my-pqr/`
  - `my-pqr-tool.component.ts`
  - `my-pqr-tool.component.html`
  - `my-pqr-tool.component.scss`
- **Backend API**: `pqr_management.api.entries.get_my_pqr` + `pqr_management.api.entries.get_pqr_detail`

---

## Tool Type (fixture)

```json
{
  "doctype": "Tool Type",
  "name": "my_pqr",
  "tool_name": "my_pqr",
  "tool_label": "Mis PQRs",
  "app_name": "pqr_management",
  "icon": "Inbox",
  "description": "Permite a los ciudadanos ver el estado de las PQR que han enviado",
  "is_active": 1
}
```

---

## Configuración por instancia

**No requiere configuración adicional**: no se añaden custom fields al `Service Portal Tool` cuando `tool_type='my_pqr'`. Solo se necesita crear la tool dentro del `Service Portal` y dejarla `is_enabled=1`.

> A diferencia de la tool `pqr`, aquí no hay catálogo configurable: la herramienta muestra exclusivamente las PQRs del `user_contact` autenticado.

---

## Flujo del usuario (UI)

### Estado bloqueado: usuario anónimo

Si `isAnonymousUser()` (no hay `X-User-Contact-Token`), el componente muestra el estado `auth-required-state` (`my-pqr-tool.component.html:10-18`):

- Icono `Lock`.
- Título: "Acceso restringido".
- Mensaje: "Para ver tus PQRs necesitas iniciar sesión."
- Botón "Registrarse / Iniciar sesión" → navega a `/portal/<portal_name>/register`.

`ngOnInit` retorna temprano sin llamar a la API:

```typescript
ngOnInit(): void {
    if (this.isAnonymousUser()) return;
    this.loadPqrs();
}
```

(`my-pqr-tool.component.ts:75-78`)

### Lista de PQRs

Si está autenticado, llama a `pqr_management.api.entries.get_my_pqr` (`my-pqr-tool.component.ts:80-100`):

```typescript
const response = await this.frappeApi.callMethod<PQRListItem[]>(
    'pqr_management.api.entries.get_my_pqr',
    {},
    true  // tercer arg = requiere token
).toPromise();
```

Estados de UI según resultado:

| Estado | Condición | Vista |
|---|---|---|
| Loading | `loading()=true` | Spinner + "Cargando tus PQRs..." |
| Vacío | `pqrs().length === 0` | Icono `Inbox`, "Aún no has enviado PQRs" |
| Error | `error()` no nulo | `alert-error` con mensaje + botón cerrar |
| OK | hay PQRs | filtros + lista |

### Filtros

Tres botones de filtro (`my-pqr-tool.component.html:39-61`):

| Filtro | Computed | Estados incluidos |
|---|---|---|
| `all` | `pqrs()` completo | todos |
| `open` | `!['Resolved','Closed','Rejected'].includes(p.status)` | `New`, `In Review`, `In Process` |
| `closed` | `['Resolved','Closed','Rejected'].includes(p.status)` | `Resolved`, `Closed`, `Rejected` |

(`my-pqr-tool.component.ts:63-73`)

### Lista (`pqr-list`)

Cada PQR se renderiza como una tarjeta clicable con:

- Icono del tipo (Lucide `pqr_type_icon`) con color de acento (`pqr_type_color`).
- Nombre del tipo: `pqr_type_label`.
- Status badge con clase CSS según estado y label traducido (`translateStatus`).
- Asunto: `subject`.
- Fecha de recepción: `formatDate(received_at)` con formato `es-ES` (`my-pqr-tool.component.ts:157-167`).
- Número: `name` (ej. `PQR-2026-00012`).
- Chevron `ChevronRight` indicando que es clicable.

### Status badges (CSS)

Mapeo `getStatusClass` (`my-pqr-tool.component.ts:169-179`):

| Status backend | CSS class | Label español (`translateStatus`) |
|---|---|---|
| `New` | `status-new` | Nueva |
| `In Review` | `status-review` | En revisión |
| `In Process` | `status-process` | En proceso |
| `Resolved` | `status-resolved` | Resuelta |
| `Closed` | `status-closed` | Cerrada |
| `Rejected` | `status-rejected` | Rechazada |
| (otro) | `status-default` | (passthrough) |

### Detalle (modal)

Al hacer click en una tarjeta:

```typescript
const response = await this.frappeApi.callMethod<PQRDetail>(
    'pqr_management.api.entries.get_pqr_detail',
    { pqr_name: pqr.name },
    true
).toPromise();
```

(`my-pqr-tool.component.ts:102-122`)

Modal con (`my-pqr-tool.component.html:102-165`):

- Cabecera con icono del tipo, label del tipo, asunto.
- Botón cerrar (`×`).
- Meta-info:
  - Número (`name`).
  - Status badge.
  - Fecha de recepción.
  - Fecha de resolución (si existe `resolved_at`).
- Sección **Descripción**: texto plano (`description`).
- Sección **Respuesta de la entidad** (si existe `resolution`): renderizada con `[innerHTML]` (es un `Text Editor`).
- Botón **Cerrar**.

El modal se cierra clickeando el overlay, el botón cerrar o el botón Cerrar inferior.

---

## Diagrama de flujo

```
┌──────────────────────────────────────────────────────┐
│ Usuario navega a /portal/<portal>/tool/<my_pqr>      │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
                ┌─────────────────┐
                │ ngOnInit        │
                │ isAnonymous?    │
                └────┬──────────┬─┘
                     │ sí       │ no
                     ▼          ▼
            ┌──────────────┐  ┌────────────────────────┐
            │ Bloquea con  │  │ GET get_my_pqr         │
            │ Auth-required│  │ (X-User-Contact-Token) │
            └──────────────┘  └─────────┬──────────────┘
                                        │
                          ┌─────────────┼─────────────┐
                          │ vacío       │ datos       │ error
                          ▼             ▼             ▼
                   ┌──────────┐  ┌──────────┐  ┌──────────┐
                   │ Empty    │  │ filters  │  │ alert    │
                   │  state   │  │  + lista │  │  error   │
                   └──────────┘  └────┬─────┘  └──────────┘
                                      │
                              click en una PQR
                                      │
                                      ▼
                       ┌──────────────────────────┐
                       │ GET get_pqr_detail       │
                       └────────────┬─────────────┘
                                    │
                                    ▼
                          ┌────────────────┐
                          │ Modal detalle  │
                          └────────────────┘
```

---

## Estado del componente

Signals declaradas (`my-pqr-tool.component.ts:51-65`):

| Signal | Tipo | Default | Propósito |
|---|---|---|---|
| `loading` | `boolean` | `false` | Carga de la lista. |
| `loadingDetail` | `boolean` | `false` | Carga del detalle. |
| `error` | `string \| null` | `null` | Mensaje de error. |
| `pqrs` | `PQRListItem[]` | `[]` | Lista completa. |
| `filterStatus` | `string` | `'all'` | Filtro activo. |
| `selectedPQR` | `PQRDetail \| null` | `null` | PQR seleccionada (modal). |
| `filteredPqrs` | computed | — | Lista filtrada según `filterStatus`. |

---

## PQRs anónimas: invisibles aquí

Las PQRs anónimas **nunca** aparecen en `my_pqr`:

- `get_my_pqr` filtra por `is_anonymous: 0` (`entries/endpoints.py:178`).
- `get_pqr_detail` lanza `PermissionError` si `is_anonymous=1` (`entries/endpoints.py:241`).

Esto se comunica al ciudadano en la tool `pqr` al activar el checkbox anónimo: "No podrás consultar el estado después." (`pqr-tool.component.html:142-145`).

Ver [features/ANONYMOUS_PQR.md](ANONYMOUS_PQR.md).

---

## Formato de fechas

`formatDate(dateStr)` (`my-pqr-tool.component.ts:157-167`) usa `toLocaleDateString('es-ES', {...})`:

```typescript
protected formatDate(dateStr?: string): string {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
```

Ejemplo de salida: `18 de mayo de 2026, 14:32`.

---

## Reutilización vs. tool `pqr`

| Aspecto | `pqr` | `my_pqr` |
|---|---|---|
| Permite usuarios anónimos | sí (depende de `pqr_allow_anonymous`) | **no**, bloquea explícitamente |
| Custom fields propios | `pqr_allowed_types`, `pqr_allow_anonymous` | ninguno |
| Componente Angular | con voice-input | sin voice-input |
| API consumida | `get_tool_types`, `create_entry_from_portal` | `get_my_pqr`, `get_pqr_detail` |
| PQRs visibles | (envía nuevas) | solo del `user_contact` autenticado, no anónimas |
