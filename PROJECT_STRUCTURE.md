# Estructura del Proyecto FacturaSend Integration

```
FacturaSend_ERPNext/
│
├── facturasend_integration/              # Módulo principal de la app
│   ├── __init__.py                       # Versión de la app
│   ├── app.json                          # Metadata de la app
│   ├── hooks.py                          # Configuración de hooks Frappe
│   ├── install.py                        # Scripts de instalación
│   │
│   ├── config/                           # Configuración del módulo
│   │   ├── __init__.py
│   │   ├── desktop.py                    # Configuración desktop
│   │   └── docs.py                       # Configuración documentación
│   │
│   ├── facturasend_integration/          # Código principal
│   │   ├── __init__.py
│   │   ├── api.py                        # ⭐ API principal con toda la lógica
│   │   │
│   │   └── doctype/                      # DocTypes personalizados
│   │       ├── __init__.py
│   │       │
│   │       ├── facturasend_settings/     # 📋 Configuración
│   │       │   ├── __init__.py
│   │       │   ├── facturasend_settings.json
│   │       │   └── facturasend_settings.py
│   │       │
│   │       ├── facturasend_log/          # 📊 Logs de envíos
│   │       │   ├── __init__.py
│   │       │   ├── facturasend_log.json
│   │       │   └── facturasend_log.py
│   │       │
│   │       ├── facturasend_log_item/     # 📄 Items de logs (child)
│   │       │   ├── __init__.py
│   │       │   ├── facturasend_log_item.json
│   │       │   └── facturasend_log_item.py
│   │       │
│   │       └── facturasend_queue/        # 🎯 UI de gestión de cola
│   │           ├── __init__.py
│   │           ├── facturasend_queue.json
│   │           ├── facturasend_queue.py
│   │           └── facturasend_queue.js  # Frontend interactivo
│   │
│   ├── fixtures/                         # Custom Fields
│   │   ├── __init__.py
│   │   ├── custom_fields_customer.json   # 👤 Campos de cliente
│   │   ├── custom_fields_sales_invoice.json  # 🧾 Campos de factura
│   │   ├── custom_fields_item.json       # 📦 Campos de item
│   │   └── custom_fields_user.json       # 👨‍💼 Campos de usuario
│   │
│   └── public/                           # Archivos públicos
│       ├── __init__.py
│       └── js/                           # JavaScript
│           ├── __init__.py
│           ├── sales_invoice.js          # JS para facturas
│           ├── credit_note.js            # JS para notas crédito
│           └── debit_note.js             # JS para notas débito
│
├── .gitignore                            # Archivos ignorados por Git
├── DEPLOYMENT.md                         # 🚀 Guía de deployment
├── DEVELOPMENT.md                        # 💻 Guía de desarrollo
├── EXAMPLES.md                           # 📚 Ejemplos de uso
├── license.txt                           # Licencia MIT
├── MANIFEST.in                           # Archivos incluidos en package
├── NAMING_SERIES.md                      # 🔢 Guía de series
├── README.md                             # 📖 Documentación principal
├── requirements.txt                      # Dependencias Python
└── setup.py                              # Setup de instalación

```

## Archivos Clave

### Backend (Python)

#### 🌟 api.py - Archivo Principal
El corazón de la integración. Contiene:

**Funciones Whitelisted (Frontend → Backend):**
- `get_pending_documents()` - Lista documentos pendientes
- `send_batch_to_facturasend()` - Envía lote a FacturaSend
- `download_batch_kude()` - Descarga KUDEs de documentos

**Funciones Internas:**
- `convert_document_to_facturasend()` - Mapea ERPNext → FacturaSend
- `prepare_payment_condition()` - Prepara condiciones de pago
- `send_to_facturasend_api()` - Llamada HTTP a API
- `check_document_status()` - Scheduled job (cada 5 min)
- `create_facturasend_log()` - Registra envíos
- `update_documents_after_send()` - Actualiza documentos
- `send_error_notification()` - Envía emails de error

**Funciones Auxiliares:**
- `extract_establecimiento_punto()` - Extrae de serie
- `extract_document_number()` - Extrae número
- `extract_number()` - Parsea "1 - Texto"
- `map_payment_mode_to_fs()` - Mapea pagos
- `get_currency_description()` - Descripción moneda

### Frontend (JavaScript)

#### facturasend_queue.js
UI completa para gestión:
- Tabla interactiva con checkboxes
- Filtros por tipo y fecha
- Botones: Enviar, Reintentar, Descargar
- Estados visuales con badges de colores
- Validaciones (max 50, mismo tipo)

#### sales_invoice.js, credit_note.js, debit_note.js
Botones en documentos individuales:
- "Enviar a FacturaSend"
- "Descargar KUDE"
- "Consultar Estado"
- Auto-extracción de establecimiento/punto

### DocTypes

#### 1. FacturaSend Settings (Single)
Configuración global:
- API Key (encriptado)
- Base URL
- Tenant ID
- Establecimiento y Punto por defecto
- Intervalo de consulta (minutos)
- Máximo de reintentos
- Emails de notificación

#### 2. FacturaSend Log
Registro de envíos:
- Lote ID
- Fecha de envío
- Tipo de documento
- Cantidad
- Estado
- Documentos (child table)

#### 3. FacturaSend Log Item (Child)
Detalle por documento:
- Tipo de documento
- Nombre
- CDC
- Estado
- Mensaje

#### 4. FacturaSend Queue (Single)
UI de gestión:
- Filtros de búsqueda
- Vista de documentos
- Acciones en lote

### Custom Fields

#### Customer (👤 Cliente)
**Sección FacturaSend:**
- Es Contribuyente (Check)
- RUC (Data)
- Nombre Fantasía (Data)
- Tipo de Operación (Select: B2B, B2C, B2G, B2F)
- Tipo de Contribuyente (Select: Física, Jurídica)

**Documento de Identidad:**
- Tipo de Documento (Select: Cédula, Pasaporte, Otro)
- Número de Documento (Data)
- Teléfono (Data)
- Celular (Data)

**Ubicación Paraguay:**
- Departamento - Código (Int)
- Departamento - Descripción (Data)
- Distrito - Código (Int)
- Distrito - Descripción (Data)
- Ciudad - Código (Int)
- Ciudad - Descripción (Data)

**Dirección:**
- Dirección (Data)
- Número de Casa (Data)
- País (Data) - Default: PRY
- Código Cliente (Data)

#### Sales Invoice (🧾 Factura)
**Sección FacturaSend:**
- CDC (Data, 44 chars, read-only)
- Estado (Select: Pendiente, Enviado, Aprobado, Rechazado, Error)
- Lote ID (Data, read-only)
- Fecha de Envío (Datetime, read-only)
- Reintentos (Int, read-only)
- Mensaje de Estado (Text, read-only)

**Configuración DE:**
- Establecimiento (Data, 3 chars)
- Punto de Expedición (Data, 3 chars)
- Tipo de Emisión (Select: Normal, Contingencia)
- Tipo de Transacción (Select: 12 opciones)
- Tipo de Impuesto (Select: IVA, ISC, Ninguno, IVA-Renta)
- Descripción (Small Text)
- Observación (Small Text)
- Presencia (Select: 5 opciones)

#### Item (📦 Producto)
**Sección FacturaSend:**
- Código de Barras (Data) → extras.barCode
- Código NCM (Data)

#### User (👨‍💼 Usuario)
**Sección FacturaSend:**
- Tipo de Documento (Select)
- Número de Documento (Data)
- Cargo (Data)

## Documentación

### 📖 README.md
- Características principales
- Guía de instalación
- Configuración inicial
- Uso básico
- Troubleshooting

### 🚀 DEPLOYMENT.md
- Pre-requisitos
- Pasos de deployment
- Configuración en producción
- Actualización de versiones
- Monitoreo y logs
- Backup y restore
- Seguridad

### 💻 DEVELOPMENT.md
- Estructura del proyecto
- Arquitectura backend/frontend
- Flujo de datos
- Mapeo de datos
- Desarrollo y testing
- Contribución

### 📚 EXAMPLES.md
- Ejemplos de configuración
- Creación de documentos
- Envío individual y en lote
- Consulta de estados
- Descarga de KUDEs
- Scripts de automatización
- Testing completo

### 🔢 NAMING_SERIES.md
- Formato de series
- Configuración en ERPNext
- Ejemplos con múltiples puntos
- Validación

## Flujo de Trabajo

```
1. CONFIGURACIÓN
   └─ FacturaSend Settings (API Key, Tenant, etc.)

2. DATOS MAESTROS
   ├─ Customers (con campos FacturaSend)
   ├─ Items (con código de barras)
   └─ Users (con documento)

3. CREACIÓN DE DOCUMENTOS
   ├─ Sales Invoice (Factura)
   ├─ Credit Note (is_return)
   └─ Debit Note (is_debit_note)

4. ENVÍO
   ├─ Individual: Botón en documento
   └─ Lote: FacturaSend Queue (hasta 50)
         ├─ Validación (mismo tipo)
         ├─ Conversión a formato FS
         ├─ Envío a API
         ├─ Registro en Log
         ├─ Actualización documentos
         └─ Descarga KUDE automática

5. SEGUIMIENTO
   ├─ Scheduled Job (cada 5 min)
   │   ├─ Consulta estados
   │   └─ Actualiza documentos
   │
   └─ Notificaciones por email (errores)

6. CONSULTA
   ├─ Ver estado en documento
   ├─ Ver logs de envíos
   └─ Dashboard (pendientes, aprobados, etc.)
```

## Tecnologías

- **Backend**: Python 3.10+, Frappe Framework v15
- **Frontend**: JavaScript, jQuery, Frappe UI
- **Base de datos**: MariaDB
- **API**: RESTful (FacturaSend Paraguay)
- **Autenticación**: Bearer Token
- **Scheduled Jobs**: Frappe Scheduler (cron)

## Características Destacadas

✅ **Envío en Lotes**: Hasta 50 documentos simultáneos
✅ **Auto-retry**: 3 intentos automáticos
✅ **Scheduled Sync**: Estados cada 5 minutos
✅ **Notificaciones**: Emails en caso de error
✅ **UI Intuitiva**: Selección múltiple, filtros
✅ **Auto-mapping**: ERPNext → FacturaSend
✅ **Series Parsing**: Auto-extracción estab/punto
✅ **PDF Download**: KUDEs individuales y por lote
✅ **Audit Trail**: Logs completos de envíos
✅ **Flexible Config**: Por documento o global

## Estado del Proyecto

- **Versión**: 0.0.1
- **Estado**: ✅ Completo y listo para deployment
- **ERPNext**: v15
- **Frappe**: v15
- **Licencia**: MIT

## Próximos Pasos

1. **Subir a GitHub**: Crear repositorio y push
2. **Testing**: Probar en ambiente de desarrollo
3. **Deploy**: Instalar en servidor de producción
4. **Configurar**: API Key, tenant, series
5. **Validar**: Envío de prueba y descarga KUDE
6. **Monitorear**: Revisar logs y estados

---

**Desarrollado para**: ERPNext v15 + FacturaSend Paraguay
**Última actualización**: Octubre 2025
