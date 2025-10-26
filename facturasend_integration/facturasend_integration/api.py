# Copyright (c) 2025, Luis and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe import _
from datetime import datetime
from frappe.utils import get_datetime, now_datetime, getdate


@frappe.whitelist()
def get_pending_documents(tipo_documento=None, desde_fecha=None, hasta_fecha=None):
	"""Obtiene lista de documentos pendientes de enviar a FacturaSend"""
	
	doctypes = []
	if tipo_documento:
		doctypes = [tipo_documento]
	else:
		doctypes = ["Sales Invoice", "Sales Invoice", "Sales Invoice"]  # Credit Note y Debit Note son is_return en Sales Invoice
	
	documents = []
	
	# Sales Invoices (facturas normales)
	if not tipo_documento or tipo_documento == "Sales Invoice":
		filters = {
			"docstatus": 1,
			"is_return": 0
		}
		if desde_fecha:
			filters["posting_date"] = [">=", desde_fecha]
		if hasta_fecha:
			if desde_fecha:
				# Si desde_fecha está en filters, necesitamos modificar el filtro
				filters["posting_date"] = [[">=", desde_fecha], ["<=", hasta_fecha]]
			else:
				filters["posting_date"] = ["<=", hasta_fecha]
		
		try:
			invoices = frappe.get_all("Sales Invoice",
				filters=filters,
				fields=["name", "customer", "customer_name", "posting_date", "grand_total", 
				        "currency"],
				order_by="posting_date desc"
			)
			
			# Obtener campos personalizados por separado para evitar errores si no existen
			for inv in invoices:
				inv['doctype'] = 'Sales Invoice'
				
				# Intentar obtener campos FacturaSend de forma segura
				try:
					doc = frappe.get_doc("Sales Invoice", inv.name)
					inv['facturasend_cdc'] = getattr(doc, 'facturasend_cdc', None)
					inv['facturasend_estado'] = getattr(doc, 'facturasend_estado', None)
					inv['facturasend_mensaje_estado'] = getattr(doc, 'facturasend_mensaje_estado', None)
					inv['facturasend_lote_id'] = getattr(doc, 'facturasend_lote_id', None)
				except:
					inv['facturasend_cdc'] = None
					inv['facturasend_estado'] = None
					inv['facturasend_mensaje_estado'] = None
					inv['facturasend_lote_id'] = None
				
				documents.append(inv)
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Error obteniendo Sales Invoices")
			frappe.throw(_(f"Error obteniendo facturas: {str(e)}"))
	
	# Credit Notes
	if not tipo_documento or tipo_documento == "Credit Note":
		filters = {
			"docstatus": 1,
			"is_return": 1,
			"is_debit_note": 0
		}
		if desde_fecha:
			filters["posting_date"] = [">=", desde_fecha]
		if hasta_fecha:
			filters["posting_date"] = ["<=", hasta_fecha]
		
		credit_notes = frappe.get_all("Sales Invoice",
			filters=filters,
			fields=["name", "customer", "customer_name", "posting_date", "grand_total", 
			        "currency", "facturasend_cdc", "facturasend_estado", 
			        "facturasend_mensaje_estado", "facturasend_lote_id"]
		)
		
		for cn in credit_notes:
			cn['doctype'] = 'Credit Note'
			documents.append(cn)
	
	# Debit Notes
	if not tipo_documento or tipo_documento == "Debit Note":
		filters = {
			"docstatus": 1,
			"is_debit_note": 1
		}
		if desde_fecha:
			filters["posting_date"] = [">=", desde_fecha]
		if hasta_fecha:
			filters["posting_date"] = ["<=", hasta_fecha]
		
		debit_notes = frappe.get_all("Sales Invoice",
			filters=filters,
			fields=["name", "customer", "customer_name", "posting_date", "grand_total", 
			        "currency", "facturasend_cdc", "facturasend_estado", 
			        "facturasend_mensaje_estado", "facturasend_lote_id"]
		)
		
		for dn in debit_notes:
			dn['doctype'] = 'Debit Note'
			documents.append(dn)
	
	return documents


@frappe.whitelist()
def send_batch_to_facturasend(documents):
	"""Envía un lote de documentos a FacturaSend"""
	
	if isinstance(documents, str):
		documents = json.loads(documents)
	
	# Validaciones
	if len(documents) > 50:
		return {"success": False, "error": "No se pueden enviar más de 50 documentos a la vez"}
	
	if len(documents) == 0:
		return {"success": False, "error": "No hay documentos para enviar"}
	
	# Verificar que todos sean del mismo tipo
	tipo = documents[0]['doctype']
	if not all(doc['doctype'] == tipo for doc in documents):
		return {"success": False, "error": "Todos los documentos deben ser del mismo tipo"}
	
	try:
		settings = get_facturasend_settings()
		
		# Preparar datos para FacturaSend
		batch_data = []
		for doc_info in documents:
			doc = frappe.get_doc("Sales Invoice", doc_info['name'])
			
			# Verificar reintentos
			if doc.facturasend_reintentos and doc.facturasend_reintentos >= settings.max_retries:
				continue
			
			# Convertir documento a formato FacturaSend
			fs_data = convert_document_to_facturasend(doc, settings)
			if fs_data:
				batch_data.append(fs_data)
		
		if not batch_data:
			return {"success": False, "error": "No hay documentos válidos para enviar"}
		
		# Enviar a FacturaSend API
		response = send_to_facturasend_api(batch_data, settings)
		
		if response.get('success'):
			# Crear log
			log = create_facturasend_log(response, documents, tipo)
			
			# Actualizar documentos
			update_documents_after_send(documents, response, log.name)
			
			return {
				"success": True, 
				"lote_id": response['result'].get('loteId'),
				"log_name": log.name
			}
		else:
			# Actualizar documentos con error
			for doc_info in documents:
				doc = frappe.get_doc("Sales Invoice", doc_info['name'])
				doc.facturasend_estado = "Error"
				doc.facturasend_mensaje_estado = response.get('error', 'Error desconocido')
				doc.facturasend_reintentos = (doc.facturasend_reintentos or 0) + 1
				doc.save(ignore_permissions=True)
			
			frappe.db.commit()
			
			# Enviar notificación de error
			send_error_notification(documents, response.get('error'))
			
			return {"success": False, "error": response.get('error')}
			
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "FacturaSend - Error al enviar lote")
		return {"success": False, "error": str(e)}


def convert_document_to_facturasend(doc, settings):
	"""Convierte un documento de ERPNext al formato requerido por FacturaSend"""
	
	try:
		# Determinar tipo de documento
		tipo_documento = 1  # Factura
		if doc.is_return and not doc.is_debit_note:
			tipo_documento = 5  # Nota de Crédito
		elif doc.is_debit_note:
			tipo_documento = 4  # Nota de Débito
		
		# Extraer establecimiento y punto de la serie
		establecimiento, punto = extract_establecimiento_punto(doc.name, settings)
		
		# Obtener datos del cliente
		customer = frappe.get_doc("Customer", doc.customer)
		
		# Preparar datos del cliente
		cliente_data = {
			"contribuyente": customer.get("facturasend_contribuyente", True),
			"razonSocial": customer.customer_name,
			"nombreFantasia": customer.get("facturasend_nombre_fantasia") or customer.customer_name,
			"tipoOperacion": extract_number(customer.get("facturasend_tipo_operacion", "1")),
			"pais": customer.get("facturasend_pais", "PRY"),
			"paisDescripcion": customer.get("facturasend_pais_desc", "Paraguay"),
			"tipoContribuyente": extract_number(customer.get("facturasend_tipo_contribuyente", "1")),
			"documentoTipo": extract_number(customer.get("facturasend_documento_tipo", "1")),
			"documentoNumero": customer.get("facturasend_documento_numero", ""),
			"telefono": customer.get("facturasend_telefono", ""),
			"celular": customer.get("facturasend_celular", ""),
			"email": customer.get("email_id", ""),
			"codigo": customer.get("facturasend_codigo", customer.name)
		}
		
		# Agregar RUC si es contribuyente
		if cliente_data["contribuyente"]:
			cliente_data["ruc"] = customer.get("facturasend_ruc", "")
		
		# Agregar dirección si está disponible
		if customer.get("facturasend_direccion"):
			cliente_data["direccion"] = customer.get("facturasend_direccion")
			cliente_data["numeroCasa"] = customer.get("facturasend_numero_casa", "")
		
		# Agregar ubicación si está disponible
		if customer.get("facturasend_departamento"):
			cliente_data["departamento"] = customer.get("facturasend_departamento")
			cliente_data["departamentoDescripcion"] = customer.get("facturasend_departamento_desc", "")
		
		if customer.get("facturasend_distrito"):
			cliente_data["distrito"] = customer.get("facturasend_distrito")
			cliente_data["distritoDescripcion"] = customer.get("facturasend_distrito_desc", "")
		
		if customer.get("facturasend_ciudad"):
			cliente_data["ciudad"] = customer.get("facturasend_ciudad")
			cliente_data["ciudadDescripcion"] = customer.get("facturasend_ciudad_desc", "")
		
		# Obtener datos del usuario
		user = frappe.get_doc("User", doc.owner)
		usuario_data = {
			"documentoTipo": extract_number(user.get("facturasend_documento_tipo", "1")),
			"documentoNumero": user.get("facturasend_documento_numero", ""),
			"nombre": user.full_name,
			"cargo": user.get("facturasend_cargo", "")
		}
		
		# Preparar items
		items_data = []
		for item in doc.items:
			item_doc = frappe.get_doc("Item", item.item_code)
			
			# Determinar tipo de IVA
			iva_tipo = 1  # 10%
			iva_tasa = 10
			if item.get("item_tax_template"):
				# Aquí deberías mapear según tu configuración de impuestos
				# Por ahora usamos valor por defecto
				pass
			
			item_data = {
				"codigo": item.item_code,
				"descripcion": item.description or item.item_name,
				"unidadMedida": 77,  # Unidad por defecto
				"cantidad": item.qty,
				"precioUnitario": item.rate,
				"cambio": 0.0,
				"ivaTipo": iva_tipo,
				"ivaBase": 100,
				"iva": iva_tasa
			}
			
			# Agregar observación si existe
			if item.get("description"):
				item_data["observacion"] = item.description
			
			# Agregar código de barras si existe
			if item_doc.get("facturasend_barcode"):
				if "extras" not in item_data:
					item_data["extras"] = {}
				item_data["extras"]["barCode"] = item_doc.get("facturasend_barcode")
			
			# Agregar NCM si existe
			if item_doc.get("facturasend_ncm"):
				item_data["ncm"] = item_doc.get("facturasend_ncm")
			
			items_data.append(item_data)
		
		# Preparar condición de pago
		condicion_data = prepare_payment_condition(doc)
		
		# Construir el documento completo
		facturasend_doc = {
			"tipoDocumento": tipo_documento,
			"establecimiento": int(establecimiento),
			"punto": punto,
			"numero": extract_document_number(doc.name),
			"descripcion": doc.get("facturasend_descripcion", ""),
			"observacion": doc.get("facturasend_observacion", ""),
			"fecha": doc.posting_date.strftime("%Y-%m-%dT%H:%M:%S") if isinstance(doc.posting_date, datetime) else f"{doc.posting_date}T00:00:00",
			"tipoEmision": extract_number(doc.get("facturasend_tipo_emision", "1")),
			"tipoTransaccion": extract_number(doc.get("facturasend_tipo_transaccion", "1")),
			"tipoImpuesto": extract_number(doc.get("facturasend_tipo_impuesto", "1")),
			"moneda": doc.currency,
			"cliente": cliente_data,
			"usuario": usuario_data,
			"factura": {
				"presencia": extract_number(doc.get("facturasend_presencia", "1"))
			},
			"condicion": condicion_data,
			"items": items_data
		}
		
		return facturasend_doc
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Error convirtiendo documento {doc.name}")
		return None


def prepare_payment_condition(doc):
	"""Prepara la condición de pago para FacturaSend"""
	
	condicion = {
		"tipo": 1,  # Contado por defecto
		"entregas": []
	}
	
	# Determinar si es contado o crédito
	if doc.payment_schedule and len(doc.payment_schedule) > 0:
		# Es a crédito
		condicion["tipo"] = 2
		
		# Preparar entregas (si hay pagos parciales)
		if hasattr(doc, 'payments') and doc.payments:
			for payment in doc.payments:
				entrega = {
					"tipo": map_payment_mode_to_fs(payment.mode_of_payment),
					"monto": str(int(payment.amount)),
					"moneda": doc.currency,
					"monedaDescripcion": get_currency_description(doc.currency),
					"cambio": 0.0
				}
				condicion["entregas"].append(entrega)
		else:
			# Si no hay pagos, agregar el total como efectivo
			entrega = {
				"tipo": 1,  # Efectivo
				"monto": str(int(doc.grand_total)),
				"moneda": doc.currency,
				"monedaDescripcion": get_currency_description(doc.currency),
				"cambio": 0.0
			}
			condicion["entregas"].append(entrega)
		
		# Preparar información de crédito
		total_cuotas = len(doc.payment_schedule)
		cuotas_info = []
		
		for cuota in doc.payment_schedule:
			cuotas_info.append({
				"moneda": doc.currency,
				"monto": cuota.payment_amount,
				"vencimiento": cuota.due_date.strftime("%Y-%m-%d") if hasattr(cuota.due_date, 'strftime') else str(cuota.due_date)
			})
		
		condicion["credito"] = {
			"tipo": 1,  # Plazo
			"plazo": f"{total_cuotas} cuotas",
			"cuotas": total_cuotas,
			"montoEntrega": 0.0,
			"infoCuotas": cuotas_info
		}
	else:
		# Es contado
		entrega = {
			"tipo": 1,  # Efectivo por defecto
			"monto": str(int(doc.grand_total)),
			"moneda": doc.currency,
			"monedaDescripcion": get_currency_description(doc.currency),
			"cambio": 0.0
		}
		condicion["entregas"].append(entrega)
	
	return condicion


def send_to_facturasend_api(batch_data, settings):
	"""Envía los datos a la API de FacturaSend"""
	
	try:
		url = f"{settings.base_url}/{settings.tenant_id}/lote/create"
		
		headers = {
			"Authorization": f"Bearer {settings.get_password('api_key')}",
			"Content-Type": "application/json"
		}
		
		response = requests.post(url, json=batch_data, headers=headers, timeout=30)
		
		if response.status_code == 200:
			return response.json()
		else:
			return {
				"success": False,
				"error": f"Error HTTP {response.status_code}: {response.text}"
			}
			
	except Exception as e:
		return {
			"success": False,
			"error": str(e)
		}


def create_facturasend_log(response, documents, tipo_documento):
	"""Crea un registro de log del envío"""
	
	log = frappe.get_doc({
		"doctype": "FacturaSend Log",
		"lote_id": str(response['result'].get('loteId')),
		"fecha_envio": now_datetime(),
		"tipo_documento": tipo_documento,
		"cantidad_documentos": len(documents),
		"estado": "Enviado",
		"mensaje": json.dumps(response)
	})
	
	# Agregar documentos al log
	for i, doc_info in enumerate(documents):
		de_info = response['result'].get('deList', [])[i] if i < len(response['result'].get('deList', [])) else {}
		
		log.append("documentos", {
			"documento_tipo": "Sales Invoice",
			"documento_nombre": doc_info['name'],
			"cdc": de_info.get('cdc', ''),
			"estado": "Enviado",
			"mensaje_estado": ""
		})
	
	log.insert(ignore_permissions=True)
	frappe.db.commit()
	
	return log


def update_documents_after_send(documents, response, log_name):
	"""Actualiza los documentos después del envío exitoso"""
	
	de_list = response['result'].get('deList', [])
	lote_id = response['result'].get('loteId')
	
	for i, doc_info in enumerate(documents):
		doc = frappe.get_doc("Sales Invoice", doc_info['name'])
		
		if i < len(de_list):
			de_info = de_list[i]
			doc.facturasend_cdc = de_info.get('cdc', '')
			doc.facturasend_estado = "Enviado"
			doc.facturasend_lote_id = str(lote_id)
			doc.facturasend_fecha_envio = now_datetime()
			doc.facturasend_mensaje_estado = f"Enviado exitosamente. CDC: {de_info.get('cdc', '')}"
		else:
			doc.facturasend_estado = "Error"
			doc.facturasend_mensaje_estado = "No se recibió respuesta del servidor"
		
		doc.save(ignore_permissions=True)
	
	frappe.db.commit()


@frappe.whitelist()
def download_batch_kude(documents):
	"""Descarga los KUDEs de un lote de documentos"""
	
	if isinstance(documents, str):
		documents = json.loads(documents)
	
	try:
		settings = get_facturasend_settings()
		
		# Obtener CDCs de los documentos
		cdcs = []
		for doc_info in documents:
			doc = frappe.get_doc("Sales Invoice", doc_info['name'])
			if doc.facturasend_cdc:
				cdcs.append(doc.facturasend_cdc)
		
		if not cdcs:
			return {"success": False, "error": "Los documentos seleccionados no tienen CDC"}
		
		# Llamar a la API para obtener PDFs
		url = f"{settings.base_url}/{settings.tenant_id}/kude"
		
		headers = {
			"Authorization": f"Bearer {settings.get_password('api_key')}"
		}
		
		params = {
			"cdcs": ",".join(cdcs)
		}
		
		response = requests.get(url, headers=headers, params=params, timeout=30)
		
		if response.status_code == 200:
			# Guardar PDF temporalmente y retornar URL
			import base64
			pdf_content = base64.b64encode(response.content).decode()
			
			return {
				"success": True,
				"pdf_content": pdf_content,
				"pdf_url": f"data:application/pdf;base64,{pdf_content}"
			}
		else:
			return {"success": False, "error": f"Error al descargar KUDEs: {response.text}"}
			
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error descargando KUDEs")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def download_lote_kude(lote_id):
	"""Descarga el PDF del KUDE de un lote completo"""
	
	try:
		settings = get_facturasend_settings()
		
		url = f"{settings.base_url}/{settings.tenant_id}/lote/{lote_id}/kude"
		
		headers = {
			"Authorization": f"Bearer {settings.get_password('api_key')}"
		}
		
		response = requests.get(url, headers=headers, timeout=30)
		
		if response.status_code == 200:
			import base64
			pdf_content = base64.b64encode(response.content).decode()
			
			return {
				"success": True,
				"pdf_content": pdf_content,
				"pdf_url": f"data:application/pdf;base64,{pdf_content}"
			}
		else:
			return {"success": False, "error": f"Error al descargar KUDE del lote: {response.text}"}
			
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error descargando KUDE del lote")
		return {"success": False, "error": str(e)}


def check_document_status():
	"""Scheduled job para consultar estados de documentos enviados"""
	
	# Obtener configuración
	settings = get_facturasend_settings()
	if not settings:
		return
	
	# Buscar documentos enviados que necesitan actualización
	pending_docs = frappe.get_all("Sales Invoice",
		filters={
			"docstatus": 1,
			"facturasend_estado": ["in", ["Enviado"]],
			"facturasend_lote_id": ["!=", ""]
		},
		fields=["name", "facturasend_lote_id", "facturasend_cdc"],
		limit=100
	)
	
	# Agrupar por lote_id
	lotes = {}
	for doc in pending_docs:
		lote_id = doc.facturasend_lote_id
		if lote_id not in lotes:
			lotes[lote_id] = []
		lotes[lote_id].append(doc)
	
	# Consultar estado de cada lote
	for lote_id, docs in lotes.items():
		try:
			status_data = get_lote_status(lote_id, settings)
			
			if status_data and status_data.get('success'):
				update_documents_status(docs, status_data)
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), f"Error consultando estado del lote {lote_id}")


def get_lote_status(lote_id, settings):
	"""Consulta el estado de un lote en FacturaSend"""
	
	try:
		url = f"{settings.base_url}/{settings.tenant_id}/lote/{lote_id}/consulta"
		
		headers = {
			"Authorization": f"Bearer {settings.get_password('api_key')}"
		}
		
		response = requests.get(url, headers=headers, timeout=30)
		
		if response.status_code == 200:
			return response.json()
		else:
			return {"success": False, "error": f"Error HTTP {response.status_code}"}
			
	except Exception as e:
		return {"success": False, "error": str(e)}


def update_documents_status(docs, status_data):
	"""Actualiza el estado de los documentos según la respuesta de FacturaSend"""
	
	de_list = status_data.get('result', {}).get('deList', [])
	
	# Crear un mapa de CDC a estado
	cdc_status_map = {}
	for de in de_list:
		cdc_status_map[de.get('cdc')] = de
	
	for doc_info in docs:
		if doc_info.facturasend_cdc in cdc_status_map:
			de = cdc_status_map[doc_info.facturasend_cdc]
			
			doc = frappe.get_doc("Sales Invoice", doc_info.name)
			
			# Mapear estado de FacturaSend a nuestro estado
			estado_fs = de.get('estado', 'Enviado')
			if estado_fs == 'Aprobado':
				doc.facturasend_estado = 'Aprobado'
			elif estado_fs == 'Rechazado':
				doc.facturasend_estado = 'Rechazado'
			else:
				doc.facturasend_estado = 'Enviado'
			
			doc.facturasend_mensaje_estado = de.get('mensaje', '')
			doc.save(ignore_permissions=True)
	
	frappe.db.commit()


def send_error_notification(documents, error_message):
	"""Envía notificación por email cuando hay errores"""
	
	settings = get_facturasend_settings()
	
	if not settings.send_error_notifications or not settings.notification_emails:
		return
	
	emails = [email.strip() for email in settings.notification_emails.split(',')]
	
	doc_names = [doc['name'] for doc in documents]
	
	message = f"""
	<p>Se ha producido un error al enviar documentos a FacturaSend:</p>
	<p><strong>Error:</strong> {error_message}</p>
	<p><strong>Documentos afectados:</strong></p>
	<ul>
		{''.join([f'<li>{name}</li>' for name in doc_names])}
	</ul>
	"""
	
	frappe.sendmail(
		recipients=emails,
		subject=_("Error en envío a FacturaSend"),
		message=message
	)


# Funciones auxiliares

def get_facturasend_settings():
	"""Obtiene la configuración de FacturaSend"""
	if not frappe.db.exists("FacturaSend Settings", "FacturaSend Settings"):
		frappe.throw(_("Por favor configure FacturaSend Settings primero"))
	
	return frappe.get_doc("FacturaSend Settings", "FacturaSend Settings")


def extract_establecimiento_punto(doc_name, settings):
	"""Extrae establecimiento y punto de expedición de la serie del documento"""
	
	# Formato esperado: FC-001-001-.#######
	parts = doc_name.split('-')
	
	if len(parts) >= 3:
		establecimiento = parts[1]
		punto = parts[2]
	else:
		# Usar valores por defecto de la configuración
		establecimiento = settings.establecimiento
		punto = settings.punto_expedicion
	
	return establecimiento, punto


def extract_document_number(doc_name):
	"""Extrae el número del documento de la serie"""
	
	# Formato esperado: FC-001-001-.#######
	parts = doc_name.split('-')
	
	if len(parts) >= 4:
		# El último elemento debería ser el número
		try:
			return int(parts[-1])
		except:
			return 1
	
	return 1


def extract_number(value):
	"""Extrae el número de un string tipo '1 - Descripción'"""
	if isinstance(value, int):
		return value
	
	if isinstance(value, str):
		parts = value.split('-')
		try:
			return int(parts[0].strip())
		except:
			return 1
	
	return 1


def map_payment_mode_to_fs(mode_of_payment):
	"""Mapea modo de pago de ERPNext a tipo de FacturaSend"""
	
	mode_map = {
		"Cash": 1,
		"Efectivo": 1,
		"Credit Card": 3,
		"Tarjeta": 3,
		"Cheque": 2,
		"Bank Transfer": 4,
		"Transferencia": 4
	}
	
	return mode_map.get(mode_of_payment, 1)


def get_currency_description(currency):
	"""Obtiene la descripción de la moneda"""
	
	currency_map = {
		"PYG": "Guaraní",
		"USD": "Dólar",
		"EUR": "Euro",
		"BRL": "Real"
	}
	
	return currency_map.get(currency, currency)
