# Instalación de la app `pqr_management`

## Requisitos previos

- Frappe Framework (bench operativo).
- App requerida instalada **antes** de instalar `pqr_management`:
  - `common_configurations`

La dependencia está declarada en `pqr_management/hooks.py:11`:

```python
required_apps = ["common_configurations"]
```

Y se valida defensivamente en el `after_install` (`pqr_management/install.py:19-26`):

```python
def _validate_dependencies():
    installed = frappe.get_installed_apps()
    if "common_configurations" not in installed:
        frappe.throw(
            "pqr_management requires common_configurations. "
            "Please install it first: bench install-app common_configurations"
        )
```

Si intentas instalar sin `common_configurations`, el install aborta con error explícito.

---

## Comandos de instalación

```bash
# Desde el directorio frappe-bench/

# 1. (Si no está) instalar common_configurations primero
bench --site <tu-sitio> install-app common_configurations

# 2. Obtener e instalar pqr_management
bench get-app pqr_management <url-del-repo>
bench --site <tu-sitio> install-app pqr_management

# 3. Sincronizar fixtures (roles, tool types, custom fields, PQR types pre-cargados)
bench --site <tu-sitio> migrate
bench --site <tu-sitio> clear-cache
```

`install-app` dispara `after_install` (declarado en `pqr_management/hooks.py:44`):

```python
after_install = "pqr_management.install.after_install"
```

`migrate` sincroniza los fixtures listados en `hooks.py` (`Role`, `Tool Type`, `Custom Field`, `PQR Type`).

---

## `install.py`

Archivo: `pqr_management/install.py`. Función pública: `after_install()`.

```python
def after_install():
    _validate_dependencies()
    _install_custom_fields()
```

### `_validate_dependencies()`

Aborta si `common_configurations` no está instalado en el sitio. Garantiza que los DocTypes `Service Portal Tool`, `User contact` y `API Service` (que se van a extender) existen.

### `_install_custom_fields()`

Crea **4 custom fields** de forma idempotente: cada uno se omite si ya existe (`frappe.db.exists("Custom Field", name)`).

#### 1. `Service Portal Tool-pqr_allowed_types`

```python
{
    "dt": "Service Portal Tool",
    "fieldname": "pqr_allowed_types",
    "fieldtype": "Table",
    "options": "PQR Tool Type",
    "label": "PQR Allowed Types",
    "description": "Types of PQR shown in this tool",
    "insert_after": "is_enabled",
    "depends_on": "eval:doc.tool_type=='pqr'",
    "mandatory_depends_on": "eval:doc.tool_type=='pqr'",
}
```

Child table donde el admin selecciona qué `PQR Type`s se ofrecen al ciudadano en esa instancia del portal. Solo aparece y es obligatoria cuando `tool_type=='pqr'`.

#### 2. `Service Portal Tool-pqr_allow_anonymous`

```python
{
    "dt": "Service Portal Tool",
    "fieldname": "pqr_allow_anonymous",
    "fieldtype": "Check",
    "label": "Allow Anonymous PQR",
    "description": "Allow citizens to submit PQR anonymously",
    "default": "1",
    "insert_after": "pqr_allowed_types",
    "depends_on": "eval:doc.tool_type=='pqr'",
}
```

Flag que controla si un **usuario autenticado** puede elegir enviar anónimamente. Si está en `0`, los usuarios logueados no ven el checkbox "Enviar de forma anónima"; los visitantes sin sesión siguen pudiendo enviar (como anónimos automáticos) salvo que el frontend bloquee el acceso (lo hace si `allow_anonymous=false` + usuario anónimo → muestra error "requiere iniciar sesión", ver `pqr-tool.component.ts:124-126`).

#### 3. `API Service-section_pqr`

```python
{
    "dt": "API Service",
    "fieldname": "section_pqr",
    "fieldtype": "Section Break",
    "label": "PQR Configuration",
    "insert_after": "enable_register_contact",
}
```

Encabezado de sección para agrupar la configuración PQR dentro del DocType `API Service`.

#### 4. `API Service-enable_create_pqr`

```python
{
    "dt": "API Service",
    "fieldname": "enable_create_pqr",
    "fieldtype": "Check",
    "label": "Enable Create PQR",
    "description": "Allow creating PQR entries via this API service",
    "default": "0",
    "insert_after": "section_pqr",
}
```

Habilita el endpoint `pqr_management.api.external.create_pqr` para esa `API Service`. El decorador `@require_api_key("enable_create_pqr")` valida este flag en cada request.

Al final, `frappe.db.commit()`.

> Los **mismos 4 custom fields** también están declarados como fixture (`pqr_management/fixtures/custom_field.json`). El `install.py` los crea inmediatamente al primer `install-app`; el fixture los sincroniza en cada `bench migrate` (sirve como respaldo y para migrar entre entornos).

---

## Configuración mínima post-instalación

1. **Roles** (ya vienen como fixture): `PQR Manager`, `PQR Agent`. Asignarlos a usuarios desde el Desk.
2. **PQR Types**: los 6 pre-cargados son suficientes para empezar. Activar/desactivar o crear más desde el Desk (`PQRs > PQR Type`).
3. **Configurar un `Service Portal Tool`** con `tool_type='pqr'`:
   - Añadir filas a `pqr_allowed_types` (al menos una con `is_enabled=1`).
   - Decidir `pqr_allow_anonymous` (default `1`).
4. **Configurar un `Service Portal Tool`** con `tool_type='my_pqr'` (no requiere configuración adicional).
5. **(Opcional) Crear un `API Service`** para integraciones externas:
   - Activar `enable_create_pqr`.
   - Generar la API Key (proceso definido en `common_configurations`).

---

## Verificación

Después de instalar, deberían existir:

### Roles
- `PQR Manager` (desk access).
- `PQR Agent` (desk access).

### DocTypes
- `PQR Type`
- `PQR Entry`
- `PQR Tool Type` (child table)

### PQR Types pre-cargados (6 filas en `tabPQR Type`)
- `peticion`, `queja`, `reclamo`, `sugerencia`, `felicitacion`, `denuncia`.

### Tool Types (2 filas en `tabTool Type`)
- `pqr` (label "PQRs").
- `my_pqr` (label "Mis PQRs").

### Custom Fields (4 filas en `tabCustom Field`)
- `Service Portal Tool-pqr_allowed_types`
- `Service Portal Tool-pqr_allow_anonymous`
- `API Service-section_pqr`
- `API Service-enable_create_pqr`

### Comando de verificación rápida

```bash
bench --site <tu-sitio> console
```

```python
import frappe

# Verificar PQR Types
assert frappe.db.count("PQR Type") >= 6

# Verificar Tool Types
assert frappe.db.exists("Tool Type", "pqr")
assert frappe.db.exists("Tool Type", "my_pqr")

# Verificar Custom Fields
for cf in [
    "Service Portal Tool-pqr_allowed_types",
    "Service Portal Tool-pqr_allow_anonymous",
    "API Service-section_pqr",
    "API Service-enable_create_pqr",
]:
    assert frappe.db.exists("Custom Field", cf), f"Falta {cf}"

# Verificar Roles
assert frappe.db.exists("Role", "PQR Manager")
assert frappe.db.exists("Role", "PQR Agent")

print("Instalación OK")
```

---

## Troubleshooting

| Síntoma | Causa probable | Solución |
|---|---|---|
| `pqr_management requires common_configurations` | Falta dependencia | `bench --site <sitio> install-app common_configurations` antes |
| El form de PQR no muestra `pqr_allowed_types` | Custom fields no se sincronizaron | `bench --site <sitio> migrate && bench --site <sitio> clear-cache` |
| El front muestra "Esta herramienta requiere iniciar sesión." | `pqr_allow_anonymous=0` y visitante no autenticado | Activar `pqr_allow_anonymous` o exigir registro |
| PQRs no llegan al agente | El usuario no tiene rol `PQR Agent` o no está en `assigned_to` | Asignar rol y poblar `assigned_to` |
| Endpoint externo devuelve 403 | `enable_create_pqr=0` en la API Service | Activar el flag en el `API Service` correspondiente |
