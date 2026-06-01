# Feature: Tool del Portal `pqr` (Envío de PQR)

Tool del Service Portal que permite a la ciudadanía **enviar PQRs** (con o sin autenticación). Es el componente principal de cara al ciudadano.

- **Tool Type registrado**: `pqr` (fixture `pqr_management/fixtures/tool_type.json`)
- **Label**: `PQRs`
- **Icon**: `MessageSquare` (Lucide)
- **Componente Angular**: `common_configurations/front_apps/service-portal/src/app/features/tools/pqr/`
  - `pqr-tool.component.ts`
  - `pqr-tool.component.html`
  - `pqr-tool.component.scss`
- **Backend API**: `pqr_management.api.types.get_tool_types` + `pqr_management.api.entries.create_entry_from_portal`

---

## Tool Type (fixture)

```json
{
  "doctype": "Tool Type",
  "name": "pqr",
  "tool_name": "pqr",
  "tool_label": "PQRs",
  "app_name": "pqr_management",
  "icon": "MessageSquare",
  "description": "Permite a los ciudadanos enviar Peticiones, Quejas, Reclamos y otras retroalimentaciones",
  "is_active": 1
}
```

---

## Configuración por instancia (`Service Portal Tool`)

Cada `Service Portal Tool` con `tool_type='pqr'` configura **dos campos extra** (custom fields aportados por `pqr_management`):

### `pqr_allowed_types` (Table → `PQR Tool Type`)

- Custom Field: `Service Portal Tool-pqr_allowed_types` (fixture + install)
- `depends_on / mandatory_depends_on: eval:doc.tool_type=='pqr'`
- Obligatorio: debe tener al menos una fila para guardar la tool.

Cada fila es un `PQR Tool Type` con:

- `pqr_type`: `Link → PQR Type` (ej. `peticion`, `queja`, `denuncia`).
- `is_enabled`: Check (default `1`).

Solo los tipos con `is_enabled=1` se ofrecen al ciudadano en el portal.

Ver [doctypes/PQR_TOOL_TYPE.md](../doctypes/PQR_TOOL_TYPE.md).

### `pqr_allow_anonymous` (Check)

- Custom Field: `Service Portal Tool-pqr_allow_anonymous`
- Default: `1`.
- `depends_on: eval:doc.tool_type=='pqr'`.

Controla si la tool admite envíos anónimos:

- `1` → usuarios logueados ven el checkbox "Enviar de forma anónima"; visitantes sin sesión pueden enviar.
- `0` → usuarios logueados no ven el checkbox (la PQR siempre se asocia a su `user_contact`); visitantes sin sesión ven mensaje "Esta herramienta requiere iniciar sesión." y no pueden enviar.

Ver [features/ANONYMOUS_PQR.md](ANONYMOUS_PQR.md).

---

## Flujo del usuario (UI)

El componente tiene tres "vistas" gestionadas por la signal `view: ViewState = 'list' | 'form' | 'confirm'`.

### Vista `list` — Selección de tipo

1. Al montarse, el componente lee `selectedPortal().tools` y busca uno con `tool_type === 'pqr'` (`pqr-tool.component.ts:96-106`).
2. Llama a `pqr_management.api.types.get_tool_types({ tool_name })` (`pqr-tool.component.ts:114`).
3. La respuesta incluye:
   - `allow_anonymous: bool`
   - `types: PQRType[]` ordenados por `display_order`.
4. Si `isAnonymousUser() && !allow_anonymous` → error "Esta herramienta requiere iniciar sesión.".
5. Renderiza una grilla con tarjetas (`pqr-types-grid`), una por tipo:
   - Icono Lucide (`type.icon`).
   - Label (`type.label`).
   - Descripción corta (`type.description`).
   - Color de acento (`--accent: type.color`).
6. Si la lista está vacía → estado vacío "No hay tipos de PQR disponibles" (`pqr-tool.component.html:33-38`).

### Vista `form` — Formulario de envío

Al hacer click en una tarjeta:

```typescript
protected selectType(type: PQRType): void {
    this.selectedType.set(type);
    this.subject.set('');
    this.description.set('');
    // Default: if user is anonymous (not logged in), force anonymous submission
    this.sendAsAnonymous.set(this.isAnonymousUser());
    this.view.set('form');
}
```

(`pqr-tool.component.ts:136-143`)

El formulario muestra:

- Cabecera con icono y descripción del tipo seleccionado.
- Input **Asunto** (`subject`, max 200 chars, requerido).
- Textarea **Descripción** (`description`, max 10 000 chars, requerido).
- Componente `<app-voice-input>` para dictar la descripción (`pqr-tool.component.html:120-126`).
- **Checkbox de anonimato** (solo si `!isAnonymousUser() && allowAnonymous()`):
  - Label: "Enviar de forma anónima"
  - Hint: "Si marcas esta opción, tu identidad no quedará asociada a la PQR. No podrás consultar el estado después."
- **Aviso de anonimato automático** (solo si `isAnonymousUser()`):
  - "Estás enviando como anónimo"
  - "No has iniciado sesión, por lo que tu PQR se enviará sin asociar a tu cuenta."
  - Link **"Inicia sesión"** → navega a `/portal/<portal_name>/register`.
- Botones: **Cancelar** (vuelve a `list`) y **Enviar PQR** (deshabilitado mientras `loading()`).

`canSubmit()` es un computed (`pqr-tool.component.ts:87-93`):

```typescript
protected canSubmit = computed(() => {
    return (
        !!this.subject().trim() &&
        !!this.description().trim() &&
        !this.loading()
    );
});
```

Al hacer submit:

```typescript
const isAnonymous = this.isAnonymousUser() ? true : this.sendAsAnonymous();

await this.frappeApi.callMethod<CreatedPQR>(
    'pqr_management.api.entries.create_entry_from_portal',
    {
        pqr_type: type.name,
        subject: this.subject().trim(),
        description: this.description().trim(),
        is_anonymous: isAnonymous ? 1 : 0,
        honeypot: '',
    }
).toPromise();
```

(`pqr-tool.component.ts:151-184`)

### Vista `confirm` — Confirmación

Modal con:

- Icono check verde.
- Título: "¡PQR enviada con éxito!"
- Resumen de la PQR creada (`name`, `subject`, `status`, indicador "Enviada de forma anónima" si aplica).
- Mensaje informativo (solo si NO es anónima): "Puedes consultar el estado de esta PQR en cualquier momento desde la sección **Mis PQRs**".
- Botón "Volver al inicio" → cierra modal, resetea estado, y navega al portal.

---

## Diagrama de flujo

```
┌────────────────────────────────────────────────────────────┐
│ Usuario navega a /portal/<portal>/tool/<tool_name>         │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  ngOnInit → loadTypes │
              │  GET get_tool_types   │
              └───────────┬───────────┘
                          │
              ┌───────────┴───────────┐
              │ allow_anonymous?      │
              └──┬─────────────────┬──┘
                 │ true            │ false
                 ▼                 ▼
       ┌────────────────┐   ┌─────────────────────┐
       │ View 'list'    │   │ Si user anónimo →   │
       │ con tarjetas   │   │ error "requiere     │
       │                │   │  iniciar sesión"    │
       └────────┬───────┘   └─────────────────────┘
                │
            click en tipo
                │
                ▼
       ┌────────────────┐
       │  View 'form'   │
       │  selectedType  │
       └────────┬───────┘
                │
       usuario llena form
                │
            click "Enviar"
                │
                ▼
       ┌────────────────────────────────────┐
       │ POST create_entry_from_portal      │
       │ (con token si tiene; honeypot='')  │
       └────────────┬───────────────────────┘
                    │
            ┌───────┴────────┐
            │ éxito          │ error
            ▼                ▼
   ┌────────────────┐   ┌────────────────┐
   │ View 'confirm' │   │ alert-error    │
   │  Modal éxito   │   │ + form abierto │
   └────────┬───────┘   └────────────────┘
            │
       click "Volver al inicio"
            │
            ▼
   navega /portal/<portal>
```

---

## Estado del componente

Signals declaradas (`pqr-tool.component.ts:66-85`):

| Signal | Tipo | Default | Propósito |
|---|---|---|---|
| `view` | `'list' \| 'form' \| 'confirm'` | `'list'` | Vista actual. |
| `loading` | `boolean` | `false` | Mientras se envía un POST. |
| `loadingTypes` | `boolean` | `false` | Mientras se carga el catálogo. |
| `error` | `string \| null` | `null` | Mensaje de error visible en alert. |
| `types` | `PQRType[]` | `[]` | Catálogo recibido. |
| `allowAnonymous` | `boolean` | `true` | Flag de la tool. |
| `selectedType` | `PQRType \| null` | `null` | Tipo elegido para el form. |
| `subject` | `string` | `''` | Asunto del form. |
| `description` | `string` | `''` | Descripción del form. |
| `sendAsAnonymous` | `boolean` | `false` | Estado del checkbox anónimo. |
| `createdPQR` | `CreatedPQR \| null` | `null` | PQR creada (vista confirm). |

---

## Validaciones combinadas (frontend + backend)

| Validación | Frontend | Backend |
|---|---|---|
| `subject` no vacío | `canSubmit()` (trim) | `_validate_pqr_inputs` |
| `description` no vacío | `canSubmit()` (trim) | `_validate_pqr_inputs` |
| `pqr_type` existe | implícito (solo tipos del catálogo se ofrecen) | `_validate_pqr_inputs` (`frappe.db.exists`) |
| `pqr_type` activo | implícito (catálogo ya filtra `is_active=1`) | `_validate_pqr_inputs` (`is_active`) |
| Rate limit | (no) | `check_rate_limit("pqr_create_entry", 5/60s)` |
| Honeypot | siempre vacío (`honeypot: ''`) | `check_honeypot` |
| Anonimato consistente | `isAnonymous` se calcula en client | `_validate_anonymous_consistency` en `validate()` |
| Asociación a `user_contact` | (no aplica) | `get_current_user_contact()` solo si `!is_anonymous` |

---

## Reutilización (`VoiceInputComponent`)

El form usa el componente compartido `<app-voice-input>` de `common_configurations/.../shared/components/voice-input/`:

```html
<app-voice-input
  [language]="'es-ES'"
  [continuous]="true"
  [interimResults]="true"
  [buttonLabel]="'Dictar por voz'"
  (transcriptChange)="description.set($event)"
></app-voice-input>
```

(`pqr-tool.component.html:120-126`)

Permite al ciudadano dictar la descripción usando la Web Speech API.

---

## Manejo de errores

El método helper `extractErrorMessage` (`pqr-tool.component.ts:209-222`):

```typescript
private extractErrorMessage(err: any, fallback: string): string {
    const message = err?.error?.message || err?.error?._server_messages;
    if (message) {
        try {
            const parsed = JSON.parse(message);
            return typeof parsed === 'string'
                ? parsed
                : parsed[0]?.message || fallback;
        } catch {
            return typeof message === 'string' ? message : fallback;
        }
    }
    return err?.message || fallback;
}
```

Decodifica los errores `_server_messages` típicos de Frappe (JSON con array de mensajes traducidos).
