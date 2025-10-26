# Guía de Desarrollo - FacturaSend Integration

## Estructura del Proyecto

```
facturasend_integration/
├── facturasend_integration/
│   ├── __init__.py
│   ├── api.py                          # API principal con métodos whitelisted
│   ├── install.py                      # Scripts de instalación
│   ├── hooks.py                        # Configuración de hooks de Frappe
│   ├── config/
│   │   ├── desktop.py                  # Configuración del módulo en desktop
│   │   └── docs.py                     # Configuración de documentación
│   ├── doctype/
│   │   ├── facturasend_settings/       # Configuración de la integración
│   │   ├── facturasend_log/            # Logs de envíos
│   │   ├── facturasend_log_item/       # Items de logs (child table)
│   │   └── facturasend_queue/          # UI para gestión de cola
│   ├── fixtures/                        # Custom fields en formato JSON
│   │   ├── custom_fields_customer.json
│   │   ├── custom_fields_sales_invoice.json
│   │   ├── custom_fields_item.json
│   │   └── custom_fields_user.json
│   └── public/
│       └── js/                         # Scripts JavaScript
│           ├── sales_invoice.js
│           ├── credit_note.js
│           └── debit_note.js
├── README.md
├── NAMING_SERIES.md
├── requirements.txt
├── setup.py
├── license.txt
└── .gitignore
```

## Arquitectura

### Backend (Python)

#### api.py - Módulo Principal

**Funciones Whitelisted (accesibles desde frontend):**

1. `get_pending_documents(tipo_documento, desde_fecha, hasta_fecha)`
   - Obtiene documentos pendientes de enviar
   - Filtra por tipo y rango de fechas
   - Retorna lista con datos para UI

2. `send_batch_to_facturasend(documents)`
   - Envía lote de documentos a FacturaSend
   - Valida límite de 50 documentos
   - Maneja reintentos automáticos
   - Retorna respuesta con lote_id

3. `download_batch_kude(documents)`
   - Descarga KUDEs en PDF de múltiples documentos
   - Retorna PDF en base64

4. `download_lote_kude(lote_id)`
   - Descarga KUDE completo de un lote
   - Retorna PDF en base64

**Funciones Internas:**

1. `convert_document_to_facturasend(doc, settings)`
   - Transforma documento ERPNext a formato FacturaSend
   - Mapea todos los campos requeridos
   - Maneja clientes contribuyentes y no contribuyentes

2. `prepare_payment_condition(doc)`
   - Prepara condiciones de pago (contado/crédito)
   - Mapea modos de pago
   - Genera información de cuotas

3. `send_to_facturasend_api(batch_data, settings)`
   - Realiza llamada HTTP a API de FacturaSend
   - Maneja autenticación con Bearer token
   - Retorna respuesta parseada

4. `check_document_status()`
   - Scheduled job que se ejecuta cada 5 minutos
   - Consulta estados de documentos enviados
   - Actualiza estados en ERPNext

5. `send_error_notification(documents, error_message)`
   - Envía emails cuando hay errores
   - Usa configuración de notificaciones

**Funciones Auxiliares:**

- `extract_establecimiento_punto()`: Extrae códigos de la serie
- `extract_document_number()`: Extrae número secuencial
- `extract_number()`: Parsea valores "1 - Descripción"
- `map_payment_mode_to_fs()`: Mapea modos de pago
- `get_currency_description()`: Obtiene descripción de moneda

### Frontend (JavaScript)

#### sales_invoice.js

Maneja facturas normales:
- Botón "Enviar a FacturaSend"
- Botón "Descargar KUDE"
- Botón "Consultar Estado"
- Auto-extrae establecimiento y punto de la serie

#### credit_note.js

Maneja notas de crédito (Sales Invoice con is_return=1)

#### debit_note.js

Maneja notas de débito (Sales Invoice con is_debit_note=1)

#### facturasend_queue.js

UI completa para gestión de cola:
- Tabla interactiva con selección múltiple
- Filtros por tipo, fecha
- Botones: Enviar, Reintentar, Descargar
- Estados con colores (badges)

## Flujo de Datos

### Envío de Documentos

```
1. Usuario selecciona documentos
   ↓
2. Frontend valida (max 50, mismo tipo)
   ↓
3. Llama a send_batch_to_facturasend()
   ↓
4. Backend obtiene cada documento
   ↓
5. convert_document_to_facturasend() mapea datos
   ↓
6. send_to_facturasend_api() envía a API
   ↓
7. create_facturasend_log() registra el envío
   ↓
8. update_documents_after_send() actualiza ERPNext
   ↓
9. Frontend descarga KUDE automáticamente
```

### Consulta de Estados

```
1. Scheduled job ejecuta cada 5 minutos
   ↓
2. check_document_status() busca documentos "Enviado"
   ↓
3. Agrupa por lote_id
   ↓
4. get_lote_status() consulta API por lote
   ↓
5. update_documents_status() actualiza estados
   ↓
6. Si hay errores, send_error_notification()
```

## Mapeo de Datos

### ERPNext → FacturaSend

#### Documento Principal

| ERPNext | FacturaSend | Notas |
|---------|-------------|-------|
| Sales Invoice | tipoDocumento: 1 | Factura |
| Credit Note | tipoDocumento: 5 | Nota de Crédito |
| Debit Note | tipoDocumento: 4 | Nota de Débito |
| Serie (FC-001-001) | establecimiento: 1, punto: "001" | Extraído de serie |
| name (número) | numero | Extraído de serie |
| posting_date | fecha | Formato ISO |
| currency | moneda | PYG, USD, etc. |

#### Cliente

| ERPNext Custom Field | FacturaSend | Tipo |
|---------------------|-------------|------|
| facturasend_contribuyente | contribuyente | Boolean |
| facturasend_ruc | ruc | String |
| customer_name | razonSocial | String |
| facturasend_nombre_fantasia | nombreFantasia | String |
| facturasend_tipo_operacion | tipoOperacion | Int (1-4) |
| facturasend_departamento | departamento | Int |
| facturasend_ciudad | ciudad | Int |

#### Items

| ERPNext | FacturaSend | Notas |
|---------|-------------|-------|
| item_code | codigo | Código del item |
| item_name | descripcion | Nombre del item |
| qty | cantidad | Cantidad |
| rate | precioUnitario | Precio unitario |
| facturasend_barcode | extras.barCode | Código de barras |
| Tax Template | ivaTipo | 1=10%, 2=5%, etc. |

#### Condición de Pago

| ERPNext | FacturaSend | Notas |
|---------|-------------|-------|
| payment_schedule (vacío) | tipo: 1 | Contado |
| payment_schedule (con items) | tipo: 2 | Crédito |
| Payment Entry | entregas[] | Tipos de pago |
| Payment Schedule | credito.infoCuotas[] | Cuotas |

## Desarrollo

### Agregar Nuevos Campos

1. Editar archivo en `fixtures/custom_fields_[doctype].json`
2. Agregar campo en formato JSON
3. Ejecutar: `bench --site [site] migrate`
4. Los campos se crearán automáticamente

### Modificar Mapeo de Datos

1. Editar `api.py`
2. Modificar función `convert_document_to_facturasend()`
3. Agregar/modificar campos según especificación de FacturaSend
4. Probar con documento de prueba

### Agregar Validaciones

1. En `send_batch_to_facturasend()` agregar validaciones antes del envío
2. Retornar `{"success": False, "error": "mensaje"}` si falla validación
3. Frontend mostrará el error al usuario

### Cambiar Intervalo de Consulta de Estados

1. Editar `hooks.py`
2. Modificar la expresión cron en `scheduler_events`
3. Ejemplo: `"*/10 * * * *"` para cada 10 minutos
4. Reiniciar: `bench restart`

## Testing

### Probar Envío Individual

```python
# En bench console
bench --site [sitio] console

import frappe
from facturasend_integration.facturasend_integration.api import send_batch_to_facturasend

documents = [{
    'doctype': 'Sales Invoice',
    'name': 'FC-001-001-0000001'
}]

result = send_batch_to_facturasend(documents)
print(result)
```

### Probar Mapeo de Datos

```python
from facturasend_integration.facturasend_integration.api import convert_document_to_facturasend, get_facturasend_settings

doc = frappe.get_doc('Sales Invoice', 'FC-001-001-0000001')
settings = get_facturasend_settings()

fs_data = convert_document_to_facturasend(doc, settings)
print(json.dumps(fs_data, indent=2))
```

### Probar Consulta de Estados

```python
from facturasend_integration.facturasend_integration.api import check_document_status

check_document_status()
```

## Troubleshooting

### Logs de Errores

Ver logs en ERPNext:
- **Error Log**: Settings > Error Log
- **Activity Log**: Settings > Activity Log

Ver logs en consola:
```bash
tail -f logs/[sitio]/worker.log
tail -f logs/[sitio]/web.log
```

### Debug Mode

Activar debug en `site_config.json`:
```json
{
  "developer_mode": 1,
  "server_script_enabled": 1
}
```

### Scheduler No Funciona

```bash
# Verificar estado
bench --site [sitio] scheduler status

# Activar
bench --site [sitio] enable-scheduler

# Ejecutar manualmente
bench --site [sitio] execute facturasend_integration.facturasend_integration.api.check_document_status
```

## Contribuir

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -am 'Agregar nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Crea un Pull Request

## Convenciones de Código

- Seguir PEP 8 para Python
- Usar docstrings en funciones
- Comentar código complejo
- Usar nombres descriptivos en español para UI
- Usar nombres en inglés para código interno

## Versioning

Seguimos Semantic Versioning:
- MAJOR: Cambios incompatibles
- MINOR: Nueva funcionalidad compatible
- PATCH: Correcciones de bugs

Versión actual: 0.0.1
