# Ejemplos de Uso - FacturaSend Integration

## Configuración Inicial

### 1. Configurar Customer (Cliente Contribuyente)

```python
import frappe

customer = frappe.get_doc({
    "doctype": "Customer",
    "customer_name": "Marcos Adrian Jara Rodriguez",
    "customer_type": "Company",
    "customer_group": "Commercial",
    "territory": "Paraguay",
    
    # Datos FacturaSend
    "facturasend_contribuyente": 1,
    "facturasend_ruc": "2005001-1",
    "facturasend_nombre_fantasia": "Marcos Adrian Jara Rodriguez",
    "facturasend_tipo_operacion": "1 - B2B",
    "facturasend_tipo_contribuyente": "1 - Persona Física",
    
    # Documento
    "facturasend_documento_tipo": "1 - Cédula",
    "facturasend_documento_numero": "2324234",
    "facturasend_telefono": "061229382",
    "facturasend_celular": "0983123765",
    "email_id": "cliente@empresa.com",
    
    # Ubicación
    "facturasend_departamento": 11,
    "facturasend_departamento_desc": "ALTO PARANA",
    "facturasend_distrito": 143,
    "facturasend_distrito_desc": "DOMINGO MARTINEZ DE IRALA",
    "facturasend_ciudad": 3344,
    "facturasend_ciudad_desc": "PASO ITA (INDIGENA)",
    
    # Dirección
    "facturasend_direccion": "Avda Calle Segunda y Proyectada",
    "facturasend_numero_casa": "1515",
    "facturasend_pais": "PRY",
    "facturasend_pais_desc": "Paraguay",
    "facturasend_codigo": "1548"
})

customer.insert()
frappe.db.commit()
print(f"Cliente creado: {customer.name}")
```

### 2. Configurar Item

```python
import frappe

item = frappe.get_doc({
    "doctype": "Item",
    "item_code": "A-001",
    "item_name": "Combo de avena sin gluten",
    "item_group": "Products",
    "stock_uom": "Nos",
    "is_stock_item": 1,
    "standard_rate": 120000,
    
    # Datos FacturaSend
    "facturasend_barcode": "7937638273256",
    "facturasend_ncm": "123456"
})

item.insert()
frappe.db.commit()
print(f"Item creado: {item.name}")
```

### 3. Configurar User

```python
import frappe

user = frappe.get_doc("User", "usuario@ejemplo.com")
user.facturasend_documento_tipo = "1 - Cédula"
user.facturasend_documento_numero = "157264"
user.facturasend_cargo = "Vendedor"
user.save()
frappe.db.commit()
```

## Crear Documentos

### 1. Crear Sales Invoice (Factura)

```python
import frappe
from frappe.utils import nowdate, add_days

invoice = frappe.get_doc({
    "doctype": "Sales Invoice",
    "naming_series": "FC-001-001-.#######",
    "customer": "Marcos Adrian Jara Rodriguez",
    "posting_date": nowdate(),
    "due_date": add_days(nowdate(), 30),
    "currency": "PYG",
    
    # Datos FacturaSend
    "facturasend_tipo_emision": "1 - Normal",
    "facturasend_tipo_transaccion": "1 - Venta de Mercadería",
    "facturasend_tipo_impuesto": "1 - IVA",
    "facturasend_presencia": "1 - Operación Presencial",
    "facturasend_descripcion": "Venta de productos",
    "facturasend_observacion": "Gracias por su compra",
    
    # Items
    "items": [{
        "item_code": "A-001",
        "qty": 1,
        "rate": 120000,
        "uom": "Nos"
    }, {
        "item_code": "1492",
        "qty": 2,
        "rate": 11300,
        "uom": "Nos"
    }]
})

invoice.insert()
invoice.submit()
frappe.db.commit()
print(f"Factura creada: {invoice.name}")
```

### 2. Crear Credit Note (Nota de Crédito)

```python
import frappe

# Primero crear la factura original
original_invoice = frappe.get_doc("Sales Invoice", "FC-001-001-0000001")

# Crear return
credit_note = frappe.get_doc({
    "doctype": "Sales Invoice",
    "naming_series": "NC-001-001-.#######",
    "is_return": 1,
    "return_against": original_invoice.name,
    "customer": original_invoice.customer,
    "posting_date": nowdate(),
    "currency": "PYG",
    
    # Datos FacturaSend
    "facturasend_tipo_emision": "1 - Normal",
    "facturasend_tipo_transaccion": "1 - Venta de Mercadería",
    "facturasend_tipo_impuesto": "1 - IVA",
    "facturasend_presencia": "1 - Operación Presencial",
    "facturasend_descripcion": "Devolución de productos",
    
    # Items (con cantidades negativas)
    "items": [{
        "item_code": "A-001",
        "qty": -1,
        "rate": 120000,
        "uom": "Nos"
    }]
})

credit_note.insert()
credit_note.submit()
frappe.db.commit()
print(f"Nota de Crédito creada: {credit_note.name}")
```

## Enviar a FacturaSend

### 1. Envío Individual desde Python

```python
from facturasend_integration.facturasend_integration.api import send_batch_to_facturasend

documents = [{
    'doctype': 'Sales Invoice',
    'name': 'FC-001-001-0000001'
}]

result = send_batch_to_facturasend(documents)

if result['success']:
    print(f"Enviado exitosamente. Lote ID: {result['lote_id']}")
else:
    print(f"Error: {result['error']}")
```

### 2. Envío en Lote

```python
from facturasend_integration.facturasend_integration.api import send_batch_to_facturasend

# Máximo 50 documentos
documents = [
    {'doctype': 'Sales Invoice', 'name': 'FC-001-001-0000001'},
    {'doctype': 'Sales Invoice', 'name': 'FC-001-001-0000002'},
    {'doctype': 'Sales Invoice', 'name': 'FC-001-001-0000003'},
]

result = send_batch_to_facturasend(documents)

if result['success']:
    print(f"Lote enviado. ID: {result['lote_id']}")
    print(f"Log: {result['log_name']}")
else:
    print(f"Error: {result['error']}")
```

### 3. Obtener Documentos Pendientes

```python
from facturasend_integration.facturasend_integration.api import get_pending_documents

# Todos los documentos
pending = get_pending_documents()

# Filtrar por tipo
invoices = get_pending_documents(tipo_documento="Sales Invoice")

# Filtrar por fecha
from frappe.utils import today, add_days
recent = get_pending_documents(
    desde_fecha=add_days(today(), -7),
    hasta_fecha=today()
)

for doc in pending:
    print(f"{doc['doctype']}: {doc['name']} - Estado: {doc.get('facturasend_estado', 'Pendiente')}")
```

## Consultar Estados

### 1. Consulta Manual de Estados

```python
from facturasend_integration.facturasend_integration.api import check_document_status

# Esto consulta todos los documentos "Enviado" y actualiza sus estados
check_document_status()
```

### 2. Ver Estado de un Documento

```python
import frappe

doc = frappe.get_doc("Sales Invoice", "FC-001-001-0000001")

print(f"CDC: {doc.facturasend_cdc}")
print(f"Estado: {doc.facturasend_estado}")
print(f"Lote ID: {doc.facturasend_lote_id}")
print(f"Fecha Envío: {doc.facturasend_fecha_envio}")
print(f"Mensaje: {doc.facturasend_mensaje_estado}")
print(f"Reintentos: {doc.facturasend_reintentos}")
```

## Descargar KUDEs

### 1. Descargar KUDE Individual

```python
from facturasend_integration.facturasend_integration.api import download_batch_kude
import base64

documents = [{
    'doctype': 'Sales Invoice',
    'name': 'FC-001-001-0000001'
}]

result = download_batch_kude(documents)

if result['success']:
    # Guardar PDF
    pdf_data = base64.b64decode(result['pdf_content'])
    with open('kude.pdf', 'wb') as f:
        f.write(pdf_data)
    print("KUDE descargado: kude.pdf")
else:
    print(f"Error: {result['error']}")
```

## Consultas Útiles

### 1. Documentos por Estado

```python
import frappe

# Documentos pendientes
pending = frappe.get_all("Sales Invoice",
    filters={"docstatus": 1, "facturasend_estado": ["in", ["", "Pendiente"]]},
    fields=["name", "customer", "grand_total", "posting_date"]
)

# Documentos enviados
sent = frappe.get_all("Sales Invoice",
    filters={"facturasend_estado": "Enviado"},
    fields=["name", "facturasend_lote_id", "facturasend_fecha_envio"]
)

# Documentos aprobados
approved = frappe.get_all("Sales Invoice",
    filters={"facturasend_estado": "Aprobado"},
    fields=["name", "facturasend_cdc"]
)

# Documentos con error
errors = frappe.get_all("Sales Invoice",
    filters={"facturasend_estado": "Error"},
    fields=["name", "facturasend_mensaje_estado", "facturasend_reintentos"]
)
```

### 2. Logs de Envío

```python
import frappe

# Últimos 10 envíos
logs = frappe.get_all("FacturaSend Log",
    fields=["name", "lote_id", "fecha_envio", "cantidad_documentos", "estado"],
    order_by="creation desc",
    limit=10
)

for log in logs:
    print(f"Lote {log.lote_id}: {log.cantidad_documentos} docs - {log.estado}")
```

## Automatización

### 1. Enviar Todas las Facturas del Día Automáticamente

```python
import frappe
from frappe.utils import today
from facturasend_integration.facturasend_integration.api import send_batch_to_facturasend

def send_today_invoices():
    # Obtener facturas del día sin enviar
    invoices = frappe.get_all("Sales Invoice",
        filters={
            "docstatus": 1,
            "posting_date": today(),
            "facturasend_estado": ["in", ["", "Pendiente"]],
            "is_return": 0
        },
        fields=["name"],
        limit=50  # Límite de lote
    )
    
    if invoices:
        documents = [{"doctype": "Sales Invoice", "name": inv.name} for inv in invoices]
        result = send_batch_to_facturasend(documents)
        
        if result['success']:
            print(f"Enviadas {len(documents)} facturas. Lote ID: {result['lote_id']}")
        else:
            print(f"Error: {result['error']}")
    else:
        print("No hay facturas pendientes")

# Ejecutar
send_today_invoices()
```

### 2. Reintentar Documentos con Error

```python
import frappe
from facturasend_integration.facturasend_integration.api import send_batch_to_facturasend

def retry_failed_documents():
    # Obtener documentos con error que no alcanzaron el máximo de reintentos
    failed = frappe.get_all("Sales Invoice",
        filters={
            "docstatus": 1,
            "facturasend_estado": "Error",
            "facturasend_reintentos": ["<", 3]
        },
        fields=["name"],
        limit=50
    )
    
    for doc in failed:
        result = send_batch_to_facturasend([{"doctype": "Sales Invoice", "name": doc.name}])
        
        if result['success']:
            print(f"Reenviado: {doc.name}")
        else:
            print(f"Error en {doc.name}: {result['error']}")

# Ejecutar
retry_failed_documents()
```

## Testing

### Script de Prueba Completo

```python
import frappe
from frappe.utils import nowdate
from facturasend_integration.facturasend_integration.api import (
    send_batch_to_facturasend,
    get_pending_documents,
    check_document_status
)

def test_facturasend_integration():
    print("=== Test FacturaSend Integration ===\n")
    
    # 1. Verificar configuración
    print("1. Verificando configuración...")
    settings = frappe.get_doc("FacturaSend Settings", "FacturaSend Settings")
    print(f"   Tenant ID: {settings.tenant_id}")
    print(f"   Establecimiento: {settings.establecimiento}")
    print(f"   Punto: {settings.punto_expedicion}\n")
    
    # 2. Obtener documentos pendientes
    print("2. Obteniendo documentos pendientes...")
    pending = get_pending_documents()
    print(f"   Documentos pendientes: {len(pending)}\n")
    
    if pending:
        # 3. Enviar primer documento
        print("3. Enviando primer documento...")
        doc = pending[0]
        result = send_batch_to_facturasend([{"doctype": doc['doctype'], "name": doc['name']}])
        
        if result['success']:
            print(f"   ✓ Enviado exitosamente")
            print(f"   Lote ID: {result['lote_id']}\n")
            
            # 4. Verificar estado
            print("4. Verificando estado del documento...")
            updated_doc = frappe.get_doc("Sales Invoice", doc['name'])
            print(f"   Estado: {updated_doc.facturasend_estado}")
            print(f"   CDC: {updated_doc.facturasend_cdc}\n")
        else:
            print(f"   ✗ Error: {result['error']}\n")
    
    print("=== Test Completado ===")

# Ejecutar test
test_facturasend_integration()
```

## Monitoreo

### Dashboard Simple

```python
import frappe

def facturasend_dashboard():
    total_invoices = frappe.db.count("Sales Invoice", {"docstatus": 1})
    
    pending = frappe.db.count("Sales Invoice", {
        "docstatus": 1,
        "facturasend_estado": ["in", ["", "Pendiente"]]
    })
    
    sent = frappe.db.count("Sales Invoice", {"facturasend_estado": "Enviado"})
    approved = frappe.db.count("Sales Invoice", {"facturasend_estado": "Aprobado"})
    rejected = frappe.db.count("Sales Invoice", {"facturasend_estado": "Rechazado"})
    errors = frappe.db.count("Sales Invoice", {"facturasend_estado": "Error"})
    
    print("=== FacturaSend Dashboard ===")
    print(f"Total Facturas: {total_invoices}")
    print(f"Pendientes: {pending}")
    print(f"Enviados: {sent}")
    print(f"Aprobados: {approved}")
    print(f"Rechazados: {rejected}")
    print(f"Errores: {errors}")
    print(f"\nTasa de éxito: {(approved / total_invoices * 100):.2f}%" if total_invoices > 0 else "N/A")

facturasend_dashboard()
```
