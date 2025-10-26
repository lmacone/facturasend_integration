# ✅ Checklist de Instalación y Verificación

## Pre-instalación

- [ ] ERPNext v15 instalado y funcionando
- [ ] Acceso a cuenta de FacturaSend con API Key
- [ ] Git instalado en el servidor
- [ ] Permisos de bench en el servidor

## Instalación

### 1. Obtener la App

```bash
cd ~/frappe-bench
bench get-app https://github.com/TU_USUARIO/facturasend_integration.git
```

**Verificar:**
- [ ] App descargada en `~/frappe-bench/apps/facturasend_integration`
- [ ] Todos los archivos presentes

### 2. Instalar en Sitio

```bash
bench --site tu-sitio.com install-app facturasend_integration
```

**Verificar:**
- [ ] Instalación completada sin errores
- [ ] Custom fields creados automáticamente
- [ ] DocTypes creados

### 3. Migrar Base de Datos

```bash
bench --site tu-sitio.com migrate
```

**Verificar:**
- [ ] Migración exitosa
- [ ] Sin errores en consola

### 4. Clear Cache y Reiniciar

```bash
bench --site tu-sitio.com clear-cache
bench restart
```

**Verificar:**
- [ ] Cache limpiado
- [ ] Servicios reiniciados

## Configuración

### 1. FacturaSend Settings

Ir a: **FacturaSend > FacturaSend Settings**

Configurar:
- [ ] API Key (de FacturaSend)
- [ ] Base URL: `https://api.facturasend.com.py`
- [ ] Tenant ID (de FacturaSend)
- [ ] Establecimiento: `001`
- [ ] Punto de Expedición: `001`
- [ ] Intervalo de Consulta: `5` minutos
- [ ] Máximo de Reintentos: `3`
- [ ] Emails de Notificación
- [ ] Enviar Notificaciones: ✓

**Guardar y verificar:**
- [ ] Settings guardado correctamente
- [ ] API Key encriptado

### 2. Naming Series

Ir a: **Settings > Naming Series**

Seleccionar: **Sales Invoice**

Agregar series:
- [ ] `FCO-001-001-.#######` (Factura Contado)
- [ ] `FC-001-001-.#######` (Factura Crédito)
- [ ] `NC-001-001-.#######` (Nota Crédito)
- [ ] `ND-001-001-.#######` (Nota Débito)

**Guardar y verificar:**
- [ ] Series guardadas correctamente

### 3. Scheduler

```bash
bench --site tu-sitio.com enable-scheduler
bench --site tu-sitio.com scheduler status
```

**Verificar:**
- [ ] Scheduler habilitado
- [ ] Estado: "enabled"

## Verificación de Custom Fields

### Customer

Abrir un Customer y verificar campos:

**Sección FacturaSend:**
- [ ] Es Contribuyente (Check)
- [ ] RUC (Data)
- [ ] Nombre Fantasía (Data)
- [ ] Tipo de Operación (Select)
- [ ] Tipo de Contribuyente (Select)

**Documento de Identidad:**
- [ ] Tipo de Documento (Select)
- [ ] Número de Documento (Data)
- [ ] Teléfono (Data)
- [ ] Celular (Data)

**Ubicación Paraguay:**
- [ ] Departamento Código (Int)
- [ ] Departamento Descripción (Data)
- [ ] Distrito Código (Int)
- [ ] Distrito Descripción (Data)
- [ ] Ciudad Código (Int)
- [ ] Ciudad Descripción (Data)

**Dirección:**
- [ ] Dirección (Data)
- [ ] Número de Casa (Data)
- [ ] País (Data)
- [ ] Código Cliente (Data)

### Sales Invoice

Abrir una Sales Invoice y verificar campos:

**Sección FacturaSend:**
- [ ] CDC (Data, read-only)
- [ ] Estado FacturaSend (Select, read-only)
- [ ] Lote ID (Data, read-only)
- [ ] Fecha de Envío (Datetime, read-only)
- [ ] Reintentos (Int, read-only)
- [ ] Mensaje de Estado (Text, read-only)

**Configuración DE:**
- [ ] Establecimiento (Data)
- [ ] Punto de Expedición (Data)
- [ ] Tipo de Emisión (Select)
- [ ] Tipo de Transacción (Select)
- [ ] Tipo de Impuesto (Select)
- [ ] Descripción (Small Text)
- [ ] Observación (Small Text)
- [ ] Presencia (Select)

### Item

Abrir un Item y verificar campos:

**Sección FacturaSend:**
- [ ] Código de Barras (Data)
- [ ] Código NCM (Data)

### User

Abrir un User y verificar campos:

**Sección FacturaSend:**
- [ ] Tipo de Documento (Select)
- [ ] Número de Documento (Data)
- [ ] Cargo (Data)

## Verificación de DocTypes

### FacturaSend Settings
- [ ] Accesible desde: FacturaSend > FacturaSend Settings
- [ ] Es Single DocType
- [ ] Todos los campos visibles

### FacturaSend Queue
- [ ] Accesible desde: FacturaSend > FacturaSend Queue
- [ ] Filtros funcionando
- [ ] Botón "Cargar Documentos" visible

### FacturaSend Log
- [ ] Accesible desde: FacturaSend > FacturaSend Log
- [ ] List view funcionando
- [ ] Permisos correctos

## Verificación de Botones JavaScript

### Sales Invoice (Factura Normal)

Crear y enviar una Sales Invoice, verificar botones:
- [ ] Botón "FacturaSend" visible
- [ ] "Enviar a FacturaSend" disponible
- [ ] Establecimiento y Punto se auto-rellenan de la serie

### Credit Note

Crear una nota de crédito, verificar:
- [ ] Botón "Enviar NC a FacturaSend" visible

### Debit Note

Crear una nota de débito, verificar:
- [ ] Botón "Enviar ND a FacturaSend" visible

## Testing Funcional

### 1. Crear Customer de Prueba

```python
# bench --site tu-sitio.com console

import frappe

customer = frappe.get_doc({
    "doctype": "Customer",
    "customer_name": "Cliente Prueba FS",
    "facturasend_contribuyente": 1,
    "facturasend_ruc": "12345678-9",
    "facturasend_tipo_operacion": "1 - B2B",
    "facturasend_documento_tipo": "1 - Cédula",
    "facturasend_documento_numero": "123456",
    "facturasend_pais": "PRY"
})
customer.insert()
frappe.db.commit()
```

- [ ] Customer creado exitosamente

### 2. Crear Item de Prueba

```python
item = frappe.get_doc({
    "doctype": "Item",
    "item_code": "TEST-001",
    "item_name": "Producto Prueba",
    "item_group": "Products",
    "stock_uom": "Nos",
    "standard_rate": 10000,
    "facturasend_barcode": "1234567890"
})
item.insert()
frappe.db.commit()
```

- [ ] Item creado exitosamente

### 3. Crear y Enviar Factura de Prueba

Desde la UI:
1. Crear nueva Sales Invoice
2. Seleccionar serie: `FC-001-001-.#######`
3. Agregar customer de prueba
4. Agregar item de prueba
5. Submit

Verificar:
- [ ] Factura creada
- [ ] Establecimiento = "001"
- [ ] Punto = "001"
- [ ] Botón "Enviar a FacturaSend" visible

### 4. Enviar a FacturaSend

Click en "Enviar a FacturaSend"

**Verificar:**
- [ ] Confirmación mostrada
- [ ] Envío exitoso
- [ ] CDC recibido
- [ ] Estado = "Enviado"
- [ ] KUDE descargado automáticamente

### 5. Verificar en FacturaSend Queue

Ir a: **FacturaSend > FacturaSend Queue**

- [ ] Click "Cargar Documentos"
- [ ] Factura de prueba aparece
- [ ] Estado mostrado correctamente
- [ ] Botones disponibles

### 6. Verificar Log

Ir a: **FacturaSend > FacturaSend Log**

- [ ] Log del envío creado
- [ ] Lote ID correcto
- [ ] Documento incluido en lista
- [ ] CDC registrado

### 7. Esperar Actualización de Estado

Esperar 5-10 minutos

**Verificar:**
- [ ] Scheduled job ejecutado
- [ ] Estado actualizado automáticamente
- [ ] Si aprobado: Estado = "Aprobado"

### 8. Descargar KUDE

Desde la factura:
- [ ] Click "FacturaSend > Descargar KUDE"
- [ ] PDF descargado
- [ ] KUDE válido

## Verificación de Logs

### Error Logs

```bash
tail -f ~/frappe-bench/logs/[sitio]/worker.log
tail -f ~/frappe-bench/logs/[sitio]/schedule.log
```

**Verificar:**
- [ ] Sin errores de Python
- [ ] Sin errores de FacturaSend
- [ ] Scheduled job ejecutándose

### Activity Log

En ERPNext UI: **Settings > Activity Log**

**Verificar:**
- [ ] Registros de creación de custom fields
- [ ] Registros de envío a FacturaSend

## Verificación de Seguridad

- [ ] HTTPS habilitado
- [ ] API Key encriptado en BD
- [ ] Permisos de roles correctos
- [ ] Backups configurados

## Problemas Comunes

### ❌ "App not installed"
**Solución:**
```bash
bench --site tu-sitio.com list-apps
bench --site tu-sitio.com install-app facturasend_integration
```

### ❌ "Custom Field already exists"
**Solución:**
```bash
bench --site tu-sitio.com console
>>> frappe.db.sql("DELETE FROM `tabCustom Field` WHERE module='FacturaSend Integration'")
>>> frappe.db.commit()
bench --site tu-sitio.com migrate
```

### ❌ "Scheduler not running"
**Solución:**
```bash
bench --site tu-sitio.com enable-scheduler
sudo supervisorctl restart all
```

### ❌ "Connection to FacturaSend failed"
**Verificar:**
- API Key correcta
- Tenant ID correcto
- Conexión a Internet
- URL correcta

## Checklist Final

- [ ] ✅ App instalada y funcionando
- [ ] ✅ Custom fields creados
- [ ] ✅ DocTypes accesibles
- [ ] ✅ FacturaSend Settings configurado
- [ ] ✅ Naming Series configuradas
- [ ] ✅ Scheduler habilitado
- [ ] ✅ Test de envío exitoso
- [ ] ✅ CDC recibido
- [ ] ✅ KUDE descargado
- [ ] ✅ Estado actualizado automáticamente
- [ ] ✅ Logs sin errores
- [ ] ✅ Notificaciones funcionando

## Soporte

Si algo no funciona:

1. Revisar logs: `tail -f ~/frappe-bench/logs/[sitio]/*.log`
2. Verificar Error Log en ERPNext UI
3. Ejecutar: `bench --site tu-sitio.com console` y probar funciones
4. Revisar documentación de FacturaSend
5. Contactar: luis@example.com

---

**¡Instalación completada exitosamente! 🎉**
