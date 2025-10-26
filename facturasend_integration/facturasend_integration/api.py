# Copyright (c) 2025, Luis and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe import _
from datetime import datetime
from frappe.utils import get_datetime, now_datetime, getdate


@frappe.whitelist()
def reset_document_retries(documents):
	"""Resetea el contador de reintentos de documentos con error"""
	
	if isinstance(documents, str):
		documents = json.loads(documents)
	
	try:
		for doc_info in documents:
			doc = frappe.get_doc("Sales Invoice", doc_info['name'])
			doc.facturasend_reintentos = 0
			doc.facturasend_estado = "Pendiente"
			doc.facturasend_mensaje_estado = "Reintentos reseteados - Listo para reenviar"
			doc.save(ignore_permissions=True)
		
		frappe.db.commit()
		
		return {
			"success": True,
			"message": f"Se resetearon {len(documents)} documentos"
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Error reseteando reintentos")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def preview_facturasend_payload(documents):
	"""Previsualiza el JSON que se enviará a FacturaSend SIN enviarlo"""
	
	if isinstance(documents, str):
		documents = json.loads(documents)
	
	try:
		settings = get_facturasend_settings()
		
		# Preparar datos para FacturaSend
		batch_data = []
		errors = []
		
		for doc_info in documents:
			try:
				doc = frappe.get_doc("Sales Invoice", doc_info['name'])
				fs_data = convert_document_to_facturasend(doc, settings)
				if fs_data:
					batch_data.append(fs_data)
				else:
					errors.append(f"{doc.name}: Conversión retornó None")
			except Exception as e:
				errors.append(f"{doc.name}: {str(e)}")
				frappe.log_error(frappe.get_traceback(), f"Preview Error {doc.name}")
		
		return {
			"success": True,
			"payload": batch_data,
			"payload_json": json.dumps(batch_data, indent=2, ensure_ascii=False),
			"errors": errors,
			"document_count": len(batch_data)
		}
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Preview Payload Error")
		return {
			"success": False,
			"error": str(e)
		}


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
		filters = [
			["Sales Invoice", "docstatus", "=", 1],
			["Sales Invoice", "is_return", "=", 0]
		]
		
		if desde_fecha:
			filters.append(["Sales Invoice", "posting_date", ">=", desde_fecha])
		if hasta_fecha:
			filters.append(["Sales Invoice", "posting_date", "<=", hasta_fecha])
		
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
		filters = [
			["Sales Invoice", "docstatus", "=", 1],
			["Sales Invoice", "is_return", "=", 1],
			["Sales Invoice", "is_debit_note", "=", 0]
		]
		if desde_fecha:
			filters.append(["Sales Invoice", "posting_date", ">=", desde_fecha])
		if hasta_fecha:
			filters.append(["Sales Invoice", "posting_date", "<=", hasta_fecha])
		
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
		filters = [
			["Sales Invoice", "docstatus", "=", 1],
			["Sales Invoice", "is_debit_note", "=", 1]
		]
		if desde_fecha:
			filters.append(["Sales Invoice", "posting_date", ">=", desde_fecha])
		if hasta_fecha:
			filters.append(["Sales Invoice", "posting_date", "<=", hasta_fecha])
		
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
		conversion_errors = []
		
		frappe.log_error(f"Procesando {len(documents)} documentos: {[d['name'] for d in documents]}", "FacturaSend Batch Processing")
		
		for doc_info in documents:
			doc = frappe.get_doc("Sales Invoice", doc_info['name'])
			
			# Verificar si ya está aprobado (no reintentar documentos exitosos)
			if doc.facturasend_estado == "Aprobado":
				error_msg = f"{doc.name}: Ya está aprobado en FacturaSend"
				conversion_errors.append(error_msg)
				frappe.log_error(error_msg, "FacturaSend Skip Document")
				continue
			
			# Verificar reintentos solo si tiene error
			if doc.facturasend_estado == "Error" and doc.facturasend_reintentos and doc.facturasend_reintentos >= settings.max_retries:
				error_msg = f"{doc.name}: Máximo de reintentos alcanzado ({doc.facturasend_reintentos}/{settings.max_retries})"
				conversion_errors.append(error_msg)
				frappe.log_error(error_msg, "FacturaSend Skip Document")
				continue
			
			# Convertir documento a formato FacturaSend
			try:
				frappe.log_error(f"Convirtiendo {doc.name} (estado: {doc.facturasend_estado}, reintentos: {doc.facturasend_reintentos})", "FacturaSend Converting")
				fs_data = convert_document_to_facturasend(doc, settings)
				if fs_data:
					batch_data.append(fs_data)
					frappe.log_error(f"{doc.name} convertido exitosamente", "FacturaSend Converted OK")
				else:
					conversion_errors.append(f"{doc.name}: Conversión retornó None")
			except Exception as e:
				error_msg = f"{doc.name}: {str(e)}"
				conversion_errors.append(error_msg)
				frappe.log_error(frappe.get_traceback(), f"Error convirtiendo {doc.name}")
		
		frappe.log_error(f"Resultado: {len(batch_data)} documentos listos para enviar, {len(conversion_errors)} errores", "FacturaSend Batch Summary")
		
		if not batch_data:
			error_detail = "\n".join(conversion_errors) if conversion_errors else "Razón desconocida"
			# Guardar en log Y retornar al usuario
			frappe.log_error(error_detail, "FacturaSend Conversion Errors")
			return {"success": False, "error": f"No hay documentos válidos para enviar", "details": conversion_errors}
		
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
				
				# Solo incrementar reintentos si ya tenía estado de error
				if doc.facturasend_estado == "Error":
					doc.facturasend_reintentos = (doc.facturasend_reintentos or 0) + 1
				else:
					doc.facturasend_reintentos = 1
				
				doc.facturasend_estado = "Error"
				doc.facturasend_mensaje_estado = response.get('error', 'Error desconocido')
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
		frappe.log_error(f"Iniciando conversión de {doc.name}", "FacturaSend Conversion Debug")
		
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
		
		# Obtener contacto principal del cliente
		contact = get_customer_primary_contact(customer.name)
		
		# Preparar datos del cliente
		# Convertir contribuyente a boolean
		es_contribuyente = customer.get("facturasend_contribuyente", 1) == 1 or customer.get("facturasend_contribuyente", 1) == True
		
		# Generar código del cliente (3-15 caracteres)
		# Si es contribuyente, usar RUC sin guión
		# Si no, usar hash del nombre o documento
		if es_contribuyente and customer.get("facturasend_ruc"):
			codigo_cliente = customer.get("facturasend_ruc", "").replace("-", "")[:15]
		elif customer.get("facturasend_documento_numero"):
			codigo_cliente = customer.get("facturasend_documento_numero", "")[:15]
		else:
			# Usar hash del nombre (primeros 10 caracteres)
			import hashlib
			codigo_cliente = hashlib.md5(customer.name.encode()).hexdigest()[:10]
		
		cliente_data = {
			"contribuyente": es_contribuyente,  # Boolean, no int
			"razonSocial": customer.customer_name,
			"nombreFantasia": customer.get("facturasend_nombre_fantasia") or customer.customer_name,
			"tipoOperacion": extract_number(customer.get("facturasend_tipo_operacion", "1")),
			"pais": customer.get("facturasend_pais", "PRY"),
			"paisDescripcion": customer.get("facturasend_pais_desc", "Paraguay"),
			"tipoContribuyente": extract_number(customer.get("facturasend_tipo_contribuyente", "1")),
			"telefono": contact.get("phone", "") if contact else "",
			"celular": contact.get("mobile_no", "") if contact else "",
			"email": contact.get("email_id", "") if contact else "",
			"codigo": codigo_cliente
		}
		
		# documentoTipo y documentoNumero solo si NO es contribuyente
		if not es_contribuyente:
			cliente_data["documentoTipo"] = extract_number(customer.get("facturasend_documento_tipo", "1"))
			cliente_data["documentoNumero"] = customer.get("facturasend_documento_numero", "")
		
		# Agregar RUC si es contribuyente
		if es_contribuyente:
			cliente_data["ruc"] = customer.get("facturasend_ruc", "")
		
		# Agregar dirección SOLO si tienes ciudad y distrito (campos obligatorios)
		# Si tipoOperacion != 4, ciudad y distrito son obligatorios
		tiene_ciudad = customer.get("facturasend_ciudad")
		tiene_distrito = customer.get("facturasend_distrito")
		
		# Solo agregar dirección si tienes los campos mínimos requeridos
		if tiene_ciudad and tiene_distrito:
			address = get_customer_primary_address(customer.name)
			if address:
				address_line = address.get("address_line1", "")
				if address.get("address_line2"):
					address_line += " " + address.get("address_line2")
				
				if address_line:
					cliente_data["direccion"] = address_line
					cliente_data["numeroCasa"] = customer.get("facturasend_numero_casa", "0")  # Usar custom field o default "0"
			
			# Agregar ubicación (ahora sabemos que existen)
			cliente_data["ciudad"] = tiene_ciudad
			cliente_data["ciudadDescripcion"] = customer.get("facturasend_ciudad_desc", "")
			cliente_data["distrito"] = tiene_distrito
			cliente_data["distritoDescripcion"] = customer.get("facturasend_distrito_desc", "")
			
			# Departamento es opcional pero lo agregamos si existe
			if customer.get("facturasend_departamento"):
				cliente_data["departamento"] = customer.get("facturasend_departamento")
				cliente_data["departamentoDescripcion"] = customer.get("facturasend_departamento_desc", "")
		
		# Si no tiene ciudad/distrito, NO enviar dirección ni ubicación
		
		# Obtener datos del usuario
		user = frappe.get_doc("User", doc.owner)
		usuario_data = {
			"documentoTipo": extract_number(user.get("facturasend_documento_tipo", "1")),
			"documentoNumero": user.get("facturasend_documento_numero", "") or "",
			"nombre": user.full_name,
			"cargo": user.get("facturasend_cargo", "") or ""
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
			
			# Obtener barcode del item
			barcode = item.item_code  # Default al código del item
			
			# Intentar obtener barcode de la tabla Item Barcode
			if item_doc.barcodes and len(item_doc.barcodes) > 0:
				barcode = item_doc.barcodes[0].barcode
			
			# Para PYG, no usar decimales
			cantidad = item.qty
			precio_unitario = item.rate
			
			if doc.currency == "PYG":
				precio_unitario = int(round(item.rate))
			
			item_data = {
				"codigo": item.item_code,
				"descripcion": item.description or item.item_name,
				"unidadMedida": 77,  # Unidad por defecto
				"cantidad": cantidad,
				"precioUnitario": precio_unitario,
				"cambio": 0.0,
				"ivaTipo": iva_tipo,
				"ivaBase": 100,
				"iva": iva_tasa,
				"extras": {
					"barCode": barcode
				}
			}
			
			# Agregar observación si existe
			if item.get("description"):
				item_data["observacion"] = item.description
			
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
			"punto": str(punto).zfill(3),  # Asegurar formato "001"
			"numero": extract_document_number(doc.name),
			"descripcion": doc.get("facturasend_descripcion") or "",
			"observacion": doc.get("facturasend_observacion") or "",
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
	
	# Determinar si es contado o crédito basado en payment_schedule
	if doc.payment_schedule and len(doc.payment_schedule) > 0:
		# Es a crédito
		condicion["tipo"] = 2
		
		# La entrega siempre va, aunque sea a crédito
		tipo_pago = 1  # Efectivo por defecto
		
		# Verificar si tiene un custom field para modo de pago
		if hasattr(doc, 'facturasend_modo_pago') and doc.facturasend_modo_pago:
			tipo_pago = extract_number(doc.facturasend_modo_pago)
		
		# Para PYG, monto como string sin decimales
		monto_entrega = doc.grand_total
		if doc.currency == "PYG":
			monto_entrega = str(int(round(doc.grand_total)))
		else:
			monto_entrega = str(doc.grand_total)
		
		entrega = {
			"tipo": tipo_pago,
			"monto": monto_entrega,
			"moneda": doc.currency,
			"monedaDescripcion": get_currency_description(doc.currency),
			"cambio": 0.0
		}
		condicion["entregas"].append(entrega)
		
		# Preparar información de crédito
		total_cuotas = len(doc.payment_schedule)
		cuotas_info = []
		
		# Calcular días totales del crédito
		primera_fecha = doc.payment_schedule[0].due_date if doc.payment_schedule else doc.posting_date
		ultima_fecha = doc.payment_schedule[-1].due_date if doc.payment_schedule else doc.posting_date
		
		# Calcular diferencia en días
		if hasattr(primera_fecha, 'toordinal') and hasattr(ultima_fecha, 'toordinal'):
			dias_plazo = (ultima_fecha.toordinal() - getdate(doc.posting_date).toordinal())
		else:
			dias_plazo = 30  # Default
		
		for cuota in doc.payment_schedule:
			# Para PYG, montos sin decimales
			monto_cuota = cuota.payment_amount
			if doc.currency == "PYG":
				monto_cuota = int(round(cuota.payment_amount))
			
			cuotas_info.append({
				"moneda": doc.currency,
				"monto": monto_cuota
			})
		
		# montoEntrega sin decimales para PYG
		monto_entrega_num = 0.0
		if doc.currency == "PYG":
			monto_entrega_num = 0
		
		condicion["credito"] = {
			"tipo": 1,  # Plazo
			"plazo": f"{dias_plazo} días",
			"cuotas": total_cuotas,
			"montoEntrega": monto_entrega_num,
			"infoCuotas": cuotas_info
		}
	else:
		# Es contado
		tipo_pago = 1  # Efectivo por defecto
		
		# Verificar si tiene un custom field para modo de pago
		if hasattr(doc, 'facturasend_modo_pago') and doc.facturasend_modo_pago:
			tipo_pago = extract_number(doc.facturasend_modo_pago)
		
		# Para PYG, monto como string sin decimales
		monto_entrega = doc.grand_total
		if doc.currency == "PYG":
			monto_entrega = str(int(round(doc.grand_total)))
		else:
			monto_entrega = str(doc.grand_total)
		
		entrega = {
			"tipo": tipo_pago,
			"monto": monto_entrega,
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
		
		# Obtener API key
		api_key = settings.get_password('api_key')
		if not api_key:
			return {
				"success": False,
				"error": "API Key no configurado en FacturaSend Settings"
			}
		
		headers = {
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json"
		}
		
		# Log completo para debugging
		frappe.log_error(f"URL: {url}\n\nHeaders: {json.dumps({k: v[:20] + '...' if k == 'Authorization' else v for k, v in headers.items()}, indent=2)}\n\nJSON Completo:\n{json.dumps(batch_data, indent=2, ensure_ascii=False)}", "FacturaSend Request")
		
		# Enviar como JSON en el body (equivalente a axios.post(url, data, {headers}))
		response = requests.post(
			url, 
			data=json.dumps(batch_data, ensure_ascii=False).encode('utf-8'),
			headers=headers, 
			timeout=30
		)
		
		# Log de respuesta
		response_text = response.text
		frappe.log_error(f"Status: {response.status_code}\n\nRespuesta:\n{response_text}", "FacturaSend Response")
		
		if response.status_code == 200:
			response_data = response.json()
			# Verificar si hay errores en la respuesta exitosa
			if not response_data.get('success') and response_data.get('errores'):
				# Construir mensaje de error detallado
				error_msg = response_data.get('error', 'Error desconocido')
				errores_detalle = []
				for err in response_data.get('errores', []):
					index = err.get('index', 'N/A')
					error_txt = err.get('error', 'Sin detalle')
					errores_detalle.append(f"[Documento {index}] {error_txt}")
				
				error_completo = f"{error_msg}\n\nDetalles:\n" + "\n".join(errores_detalle)
				
				return {
					"success": False,
					"error": error_completo,
					"errores": response_data.get('errores', []),
					"response": response_text
				}
			
			return response_data
		else:
			# Incluir response completo en el error
			try:
				error_data = response.json()
				# Si el response tiene errores detallados
				if error_data.get('errores'):
					error_msg = error_data.get('error', f'Error HTTP {response.status_code}')
					errores_detalle = []
					for err in error_data.get('errores', []):
						index = err.get('index', 'N/A')
						error_txt = err.get('error', 'Sin detalle')
						errores_detalle.append(f"[Documento {index}] {error_txt}")
					
					error_completo = f"{error_msg}\n\nDetalles:\n" + "\n".join(errores_detalle)
					
					return {
						"success": False,
						"error": error_completo,
						"errores": error_data.get('errores', []),
						"status_code": response.status_code,
						"response": response_text
					}
			except:
				pass
			
			return {
				"success": False,
				"error": f"Error HTTP {response.status_code}: {response_text}",
				"status_code": response.status_code,
				"response": response_text
			}
			
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "FacturaSend API Error")
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
		
		# Llamar a la API para obtener PDFs - POST /de/pdf según documentación
		url = f"{settings.base_url}/{settings.tenant_id}/de/pdf"
		
		api_key = settings.get_password('api_key')
		if not api_key:
			return {"success": False, "error": "API Key no configurado"}
		
		headers = {
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json"
		}
		
		# Enviar CDCs en el body como array
		payload = {
			"cdcList": cdcs
		}
		
		frappe.log_error(f"POST {url}\nPayload: {json.dumps(payload, indent=2)}", "FacturaSend KUDE Request")
		
		response = requests.post(url, json=payload, headers=headers, timeout=30)
		
		frappe.log_error(f"Status: {response.status_code}\nResponse: {response.text[:500]}", "FacturaSend KUDE Response")
		
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
		
		# Obtener CDCs de todos los documentos del lote
		docs = frappe.get_all("Sales Invoice",
			filters={
				"facturasend_lote_id": lote_id,
				"facturasend_cdc": ["!=", ""]
			},
			fields=["facturasend_cdc"]
		)
		
		if not docs:
			return {"success": False, "error": "No se encontraron documentos con CDC para este lote"}
		
		cdcs = [doc.facturasend_cdc for doc in docs]
		
		# Usar el endpoint POST /de/pdf según documentación
		url = f"{settings.base_url}/{settings.tenant_id}/de/pdf"
		
		api_key = settings.get_password('api_key')
		if not api_key:
			return {"success": False, "error": "API Key no configurado"}
		
		headers = {
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json"
		}
		
		payload = {
			"cdcList": cdcs
		}
		
		frappe.log_error(f"POST {url}\nLote: {lote_id}\nCDCs: {len(cdcs)}", "FacturaSend Lote KUDE Request")
		
		response = requests.post(url, json=payload, headers=headers, timeout=30)
		
		frappe.log_error(f"Status: {response.status_code}", "FacturaSend Lote KUDE Response")
		
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
	
	try:
		# Obtener configuración
		settings = get_facturasend_settings()
		if not settings:
			frappe.log_error("No se encontró FacturaSend Settings", "FacturaSend Status Check")
			return
		
		# Buscar documentos enviados que necesitan actualización
		pending_docs = frappe.get_all("Sales Invoice",
			filters={
				"docstatus": 1,
				"facturasend_estado": ["in", ["Enviado"]],
				"facturasend_cdc": ["!=", ""]
			},
			fields=["name", "facturasend_cdc"],
			limit=100
		)
		
		frappe.log_error(f"Encontrados {len(pending_docs)} documentos pendientes de actualización", "FacturaSend Status Check")
		
		if not pending_docs:
			return
		
		# Consultar estado de cada documento individualmente por CDC
		for doc_info in pending_docs:
			try:
				frappe.log_error(f"Consultando estado de {doc_info.name} con CDC {doc_info.facturasend_cdc}", "FacturaSend Status Check Doc")
				status_data = get_document_status_by_cdc(doc_info.facturasend_cdc, settings)
				
				if status_data and status_data.get('success'):
					frappe.log_error(f"Documento {doc_info.name} consultado exitosamente", "FacturaSend Status Check OK")
					update_single_document_status(doc_info.name, status_data)
				else:
					frappe.log_error(f"Error consultando {doc_info.name}: {status_data.get('error', 'Unknown')}", "FacturaSend Status Check Error")
			except Exception as e:
				frappe.log_error(frappe.get_traceback(), f"Error consultando estado del documento {doc_info.name}")
		
		frappe.log_error(f"Consulta de estados completada para {len(pending_docs)} documentos", "FacturaSend Status Check Complete")
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "FacturaSend Status Check Fatal Error")


def get_document_status_by_cdc(cdc, settings):
	"""Consulta el estado de un documento electrónico por CDC"""
	
	try:
		url = f"{settings.base_url}/{settings.tenant_id}/de/estado"
		
		api_key = settings.get_password('api_key')
		if not api_key:
			return {"success": False, "error": "API Key no configurado"}
		
		headers = {
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json"
		}
		
		payload = {
			"cdc": cdc
		}
		
		frappe.log_error(f"POST {url}\nPayload: {json.dumps(payload, indent=2)}", "FacturaSend Status Query Request")
		
		response = requests.post(url, json=payload, headers=headers, timeout=30)
		
		frappe.log_error(f"Status: {response.status_code}\nResponse: {response.text}", "FacturaSend Status Query Response")
		
		if response.status_code == 200:
			return response.json()
		else:
			return {"success": False, "error": f"Error HTTP {response.status_code}: {response.text}"}
			
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "FacturaSend Status Query Error")
		return {"success": False, "error": str(e)}


def update_single_document_status(doc_name, status_data):
	"""Actualiza el estado de un documento según la respuesta de FacturaSend"""
	
	try:
		# La respuesta tiene la estructura:
		# {"success": true, "message": "Consulta exitosa", "estado": "Aprobado", ...}
		
		doc = frappe.get_doc("Sales Invoice", doc_name)
		
		# Mapear estado de FacturaSend a nuestro estado
		estado_fs = status_data.get('estado', 'Enviado')
		
		if estado_fs == 'Aprobado' or estado_fs == '2':
			doc.facturasend_estado = 'Aprobado'
		elif estado_fs == 'Rechazado' or estado_fs == '4':
			doc.facturasend_estado = 'Rechazado'
		else:
			doc.facturasend_estado = 'Enviado'
		
		# Actualizar mensaje con la información del estado
		mensaje_partes = []
		if status_data.get('message'):
			mensaje_partes.append(status_data.get('message'))
		if status_data.get('estadoDescripcion'):
			mensaje_partes.append(f"Estado: {status_data.get('estadoDescripcion')}")
		
		doc.facturasend_mensaje_estado = ' - '.join(mensaje_partes) if mensaje_partes else estado_fs
		doc.save(ignore_permissions=True)
		
		frappe.db.commit()
		
		frappe.log_error(f"Documento {doc_name} actualizado a estado {doc.facturasend_estado}", "FacturaSend Update Status")
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Error actualizando estado de {doc_name}")


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
		punto = str(parts[2]).zfill(3)  # Asegurar formato "001"
	else:
		# Usar valores por defecto de la configuración
		establecimiento = settings.establecimiento
		punto = str(settings.punto_expedicion).zfill(3)
	
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


def get_customer_primary_contact(customer_name):
	"""Obtiene el contacto principal del cliente"""
	
	try:
		# Buscar el vínculo entre Customer y Contact
		links = frappe.get_all("Dynamic Link",
			filters={
				"link_doctype": "Customer",
				"link_name": customer_name,
				"parenttype": "Contact"
			},
			fields=["parent"],
			limit=1
		)
		
		if links:
			contact = frappe.get_doc("Contact", links[0].parent)
			return contact
		
		return None
	except Exception as e:
		frappe.log_error(f"Error obteniendo contacto de {customer_name}: {str(e)}", "Get Customer Contact")
		return None


def get_customer_primary_address(customer_name):
	"""Obtiene la dirección principal del cliente"""
	
	try:
		# Buscar el vínculo entre Customer y Address
		links = frappe.get_all("Dynamic Link",
			filters={
				"link_doctype": "Customer",
				"link_name": customer_name,
				"parenttype": "Address"
			},
			fields=["parent"],
			limit=1
		)
		
		if links:
			address = frappe.get_doc("Address", links[0].parent)
			return address
		
		return None
	except Exception as e:
		frappe.log_error(f"Error obteniendo dirección de {customer_name}: {str(e)}", "Get Customer Address")
		return None
