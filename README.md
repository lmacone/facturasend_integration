# FacturaSend Integration para ERPNext

Integración completa de FacturaSend Paraguay con ERPNext v15 para facturación electrónica.

## Características

- ✅ Envío de Facturas Electrónicas a FacturaSend
- ✅ Envío de Notas de Crédito Electrónicas
- ✅ Envío de Notas de Débito Electrónicas
- ✅ Envío en lotes de hasta 50 documentos
- ✅ Gestión de cola de documentos pendientes
- ✅ Consulta automática de estados cada 5 minutos
- ✅ Descarga de KUDEs en PDF
- ✅ Sistema de reintentos automáticos (hasta 3 intentos)
- ✅ Notificaciones por email en caso de errores
- ✅ Configuración de establecimiento y punto de expedición por serie
- ✅ Soporte para múltiples tipos de clientes (contribuyentes y no contribuyentes)
- ✅ Mapeo automático de datos de ERPNext a formato FacturaSend

## Instalación

### Requisitos

- ERPNext v15
- Python 3.10+
- Frappe Framework v15

### Pasos de instalación

1. Obtener la app desde GitHub:

```bash
cd ~/frappe-bench
bench get-app https://github.com/tu-usuario/facturasend_integration.git
```

2. Instalar la app en el sitio:

```bash
bench --site tu-sitio.local install-app facturasend_integration
```

3. Migrar la base de datos:

```bash
bench --site tu-sitio.local migrate
```

4. Reiniciar bench:

```bash
bench restart
```

## Configuración Inicial

### 1. Configurar FacturaSend Settings

1. Ve a: **FacturaSend > FacturaSend Settings**
2. Configura los siguientes campos:
   - **API Key**: Tu API Key de FacturaSend
   - **Base URL**: `https://api.facturasend.com.py` (por defecto)
   - **Tenant ID**: Tu ID de tenant en FacturaSend
   - **Establecimiento**: Código de establecimiento por defecto (ej: 001)
   - **Punto de Expedición**: Código de punto de expedición por defecto (ej: 001)
   - **Intervalo de Consulta**: Minutos entre consultas de estado (recomendado: 5)
   - **Máximo de Reintentos**: Número de reintentos automáticos (recomendado: 3)
   - **Emails de Notificación**: Emails separados por coma para recibir notificaciones de errores
   - **Enviar Notificaciones de Errores**: Activar para recibir emails en caso de errores

### 2. Configurar Naming Series

Configura las series de numeración con el formato: `PREFIJO-ESTAB-PUNTO-.#######`

Ejemplos:
- Factura Contado: `FCO-001-001-.#######`
- Factura Crédito: `FC-001-001-.#######`
- Nota de Crédito: `NC-001-001-.#######`
- Nota de Débito: `ND-001-001-.#######`

Para configurar:
1. Ve a: **Settings > Naming Series**
2. Selecciona el DocType (Sales Invoice)
3. Agrega las series según el formato indicado

### 3. Configurar Customers

Para cada cliente, completa los campos de FacturaSend:

**Datos básicos:**
- Es Contribuyente
- RUC (si es contribuyente)
- Nombre Fantasía
- Tipo de Operación
- Tipo de Contribuyente

**Documento de Identidad:**
- Tipo de Documento
- Número de Documento
- Teléfono
- Celular

**Ubicación Paraguay:**
- Departamento (Código)
- Departamento Descripción
- Distrito (Código)
- Distrito Descripción
- Ciudad (Código)
- Ciudad Descripción

**Dirección:**
- Dirección
- Número de Casa
- País (PRY por defecto)

### 4. Configurar Items (Opcional)

Para cada item, puedes configurar:
- **Código de Barras**: Se enviará en el campo extras.barCode
- **Código NCM**: Nomenclatura Común del Mercosur (opcional)

### 5. Configurar Users

Para cada usuario que creará facturas, configura:
- **Tipo de Documento**: Tipo de documento de identidad
- **Número de Documento**: Número de cédula/pasaporte
- **Cargo**: Cargo del usuario (ej: Vendedor, Cajero)

## Uso

### Envío Individual

1. Crea una Sales Invoice, Credit Note o Debit Note normalmente
2. Una vez guardada y enviada (Submit), aparecerá el botón **"Enviar a FacturaSend"**
3. Haz clic en el botón y confirma
4. El KUDE se descargará automáticamente
5. El estado se actualizará automáticamente cada 5 minutos

### Envío en Lotes

1. Ve a: **FacturaSend > FacturaSend Queue**
2. Opcionalmente, aplica filtros:
   - Tipo de Documento
   - Rango de fechas
3. Haz clic en **"Cargar Documentos"**
4. Selecciona los documentos a enviar (máximo 50)
5. Haz clic en **"Enviar Seleccionados"**
6. El PDF con todos los KUDEs se descargará automáticamente

### Reintentar Documentos con Error

Si un documento tiene estado "Error" o "Rechazado":

**Desde el documento:**
1. Abre el documento
2. Haz clic en **"Enviar a FacturaSend"** nuevamente

**Desde FacturaSend Queue:**
1. El botón **"Reintentar"** aparecerá en la lista
2. Haz clic para reenviar el documento

### Descargar KUDEs

**Individual:**
- Abre el documento
- Haz clic en **FacturaSend > Descargar KUDE**

**En lote:**
- En FacturaSend Queue, selecciona los documentos
- Haz clic en **Acciones > Descargar KUDEs**

## Estados de Documentos

- **Pendiente**: No se ha enviado a FacturaSend
- **Enviado**: Enviado exitosamente, esperando confirmación
- **Aprobado**: Documento aprobado por SET (Sistema de Facturación Electrónica)
- **Rechazado**: Documento rechazado por SET
- **Error**: Error en el envío o procesamiento

## Consulta Automática de Estados

El sistema consulta automáticamente el estado de los documentos enviados cada 5 minutos (configurable).

Para verificar manualmente:
- Abre el documento
- Haz clic en **FacturaSend > Consultar Estado**

## Logs y Auditoría

Todos los envíos se registran en:
- **FacturaSend > FacturaSend Log**

Cada log contiene:
- Lote ID
- Fecha de envío
- Tipo de documento
- Cantidad de documentos
- Estado del lote
- Lista de documentos incluidos con sus CDCs

## Notificaciones

Si está configurado, recibirás emails cuando:
- Hay errores en el envío
- Un documento es rechazado
- Se alcanza el máximo de reintentos

## Troubleshooting

### Error: "No se puede conectar a FacturaSend"
- Verifica que el API Key sea correcto
- Verifica que el Base URL sea correcto
- Verifica que el Tenant ID sea correcto
- Verifica la conexión a Internet

### Error: "Documento rechazado por SET"
- Revisa los datos del cliente (RUC, dirección, etc.)
- Verifica que los items tengan precios correctos
- Revisa el mensaje de estado en el documento para más detalles

### Los estados no se actualizan automáticamente
- Verifica que el scheduler de Frappe esté activo: `bench --site tu-sitio.local enable-scheduler`
- Revisa los Error Logs en ERPNext

### No se descarga el KUDE
- Verifica que el documento tenga CDC
- Verifica que el estado sea "Aprobado"
- Revisa la consola del navegador para errores

## Soporte

Para reportar problemas o solicitar nuevas características:
- GitHub Issues: https://github.com/tu-usuario/facturasend_integration/issues
- Email: luis@example.com

## Licencia

MIT License

## Créditos

Desarrollado para la integración de FacturaSend Paraguay con ERPNext v15.
