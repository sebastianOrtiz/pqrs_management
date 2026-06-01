# PQRs Management

App de Frappe para la **recepción y gestión de PQRs** (Peticiones, Quejas, Reclamos, Sugerencias, Felicitaciones y Denuncias) provenientes de ciudadanía a través de un Service Portal público, integraciones externas (chatbots, apps móviles) o registro interno desde el Desk.

- **Publisher**: Nexora Online SAS
- **Email**: sebastianortiz989@gmail.com
- **Licencia**: MIT
- **Apps requeridas**: [`common_configurations`](../common_configurations)
- **Módulo Frappe**: `Pqr Management`
- **Roles propios**: `PQR Manager`, `PQR Agent`

---

## Propósito y casos de uso

La app provee una infraestructura de gestión de PQRs con tres canales de entrada:

1. **Service Portal (Angular)**: ciudadanía envía PQRs con o sin autenticación (token de `User contact`). Soporta envío anónimo.
2. **Integraciones externas (API Key)**: chatbots, apps móviles u otros sistemas pueden registrar PQRs a nombre de un ciudadano vía `X-API-Key`.
3. **Desk interno**: agentes y administradores pueden crear/editar PQRs directamente desde el backend.

Cada PQR se clasifica con un **tipo configurable** (PQR Type) y queda asignable a un agente para su trámite y resolución.

---

## Características principales

- **6 tipos pre-cargados via fixture**: `peticion`, `queja`, `reclamo`, `sugerencia`, `felicitacion`, `denuncia` (con icono Lucide, color y descripción).
- **Catálogo extensible de tipos** (`PQR Type`): cualquier administrador puede crear nuevos tipos sin tocar código.
- **2 tools del Service Portal**:
  - `pqr` — formulario de envío.
  - `my_pqr` — historial y seguimiento de las PQRs propias (solo usuarios autenticados).
- **Sistema de anonimato a tres bandas**:
  - PQR anónima explícita (usuario logueado marca el checkbox).
  - PQR anónima automática (visitante sin token).
  - PQR autenticada normal (asociada al `User contact`).
- **API modular** (`api/entries`, `api/types`, `api/external`) con rate limiting, honeypot y sanitización por IP.
- **Endpoint externo con API Key** habilitado por flag `enable_create_pqr` en `API Service`.
- **Permisos por rol scoped**: `PQR Manager` ve todo, `PQR Agent` solo lo asignado a él, otros sin acceso.
- **Configuración por instancia de tool**: cada `Service Portal Tool` con `tool_type='pqr'` define sus tipos permitidos (child table `pqr_allowed_types`) y si admite anonimato (`pqr_allow_anonymous`).
- **Auto-stamping de `resolved_at`** al pasar el estado a `Resolved`/`Closed`.

---

## Arquitectura general

```
pqr_management/
├── hooks.py                       # fixtures, permission hooks, after_install
├── install.py                     # creación idempotente de custom fields
├── fixtures/
│   ├── role.json                  # PQR Manager, PQR Agent
│   ├── tool_type.json             # tools 'pqr' y 'my_pqr'
│   ├── pqr_type.json              # 6 tipos pre-cargados
│   └── custom_field.json          # 4 custom fields (Service Portal Tool + API Service)
├── pqr_management/                # módulo Frappe (DocTypes)
│   └── doctype/
│       ├── pqr_type/              # catálogo de tipos
│       ├── pqr_entry/             # entrada principal (controlador + permisos)
│       └── pqr_tool_type/         # child table de Service Portal Tool
├── api/
│   ├── entries/                   # endpoints del portal (create, get_my, get_detail)
│   ├── types/                     # consulta del catálogo (get_tool_types, get_all_types)
│   └── external/                  # endpoint con API Key (create_pqr)
└── translations/                  # es.csv, es-CO.csv
```

### DocTypes

| DocType | Propósito |
|---|---|
| `PQR Type` | Catálogo de tipos (label, icono, color, orden). |
| `PQR Entry` | Entrada principal: una PQR enviada. |
| `PQR Tool Type` | Child table para enlazar PQR Types a una `Service Portal Tool`. |

### Frontend Angular

Vive en `common_configurations/front_apps/service-portal/`:

- `features/tools/pqr/` — componente del envío.
- `features/tools/my-pqr/` — componente del seguimiento.

---

## Dependencias

`pqr_management` depende exclusivamente de:

- **`common_configurations`**: aporta `User contact`, `Service Portal`, `Service Portal Tool`, `Tool Type`, `API Service`, autenticación por token (`X-User-Contact-Token`), API Key (`X-API-Key`), helpers compartidos (`check_rate_limit`, `check_honeypot`, `get_current_user_contact`, `require_api_key`, `sanitize_string`).

Esta dependencia está declarada en `hooks.py`:

```python
required_apps = ["common_configurations"]
```

Y se valida defensivamente en `after_install` (`pqr_management/install.py:19-26`).

---

## Instalación

```bash
# Desde el directorio frappe-bench/

# 1. Asegurate de tener common_configurations instalado
bench --site <tu-sitio> install-app common_configurations

# 2. Obtener e instalar pqr_management
bench get-app pqr_management <url-del-repo>
bench --site <tu-sitio> install-app pqr_management

# 3. Sincronizar fixtures (roles, tool types, custom fields, PQR types)
bench --site <tu-sitio> migrate
bench --site <tu-sitio> clear-cache
```

Tras la instalación deberían existir:

- Roles: `PQR Manager`, `PQR Agent`.
- DocTypes: `PQR Type`, `PQR Entry`, `PQR Tool Type`.
- 6 PQR Types: `peticion`, `queja`, `reclamo`, `sugerencia`, `felicitacion`, `denuncia`.
- 2 Tool Types: `pqr`, `my_pqr`.
- 4 Custom Fields:
  - `Service Portal Tool-pqr_allowed_types`
  - `Service Portal Tool-pqr_allow_anonymous`
  - `API Service-section_pqr`
  - `API Service-enable_create_pqr`

Detalles completos en [`docs/INSTALL.md`](docs/INSTALL.md).

---

## Documentación

La documentación detallada está en [`docs/`](docs/README.md):

- **DocTypes**: campos uno por uno, validaciones, permisos.
- **APIs**: parámetros, autenticación, rate limits, ejemplos curl.
- **Features**: anonimato, tools del portal, permisos.
- **hooks.py** completo y proceso de instalación.

Comenzar por [`docs/README.md`](docs/README.md).

---

## Contributing

Esta app usa `pre-commit` para formateo y lint. Para activarlo:

```bash
cd apps/pqr_management
pre-commit install
```

Herramientas configuradas:

- `ruff` (Python)
- `eslint` (JS)
- `prettier` (formato)
- `pyupgrade` (Python modernization)

---

## Licencia

MIT — ver [`license.txt`](license.txt).
