# Copyright (c) 2025, Luis and contributors
# For license information, please see license.txt

import frappe
import json
import os


def after_install():
	"""Ejecutar después de instalar la app"""
	
	print("Instalando FacturaSend Integration...")
	
	# Crear custom fields
	create_custom_fields()
	
	# Crear FacturaSend Settings si no existe
	create_default_settings()
	
	print("FacturaSend Integration instalado exitosamente")


def create_custom_fields():
	"""Crea los custom fields desde los fixtures"""
	
	fixtures_path = frappe.get_app_path("facturasend_integration", "fixtures")
	
	# Lista de archivos de fixtures
	fixture_files = [
		"custom_fields_customer.json",
		"custom_fields_sales_invoice.json",
		"custom_fields_item.json",
		"custom_fields_user.json"
	]
	
	for fixture_file in fixture_files:
		file_path = os.path.join(fixtures_path, fixture_file)
		
		if os.path.exists(file_path):
			with open(file_path, 'r', encoding='utf-8') as f:
				custom_fields = json.load(f)
			
			for field in custom_fields:
				try:
					dt = field.get('dt')
					fieldname = field.get('fieldname')
					
					# Verificar si el campo ya existe
					if not frappe.db.exists('Custom Field', {'dt': dt, 'fieldname': fieldname}):
						custom_field = frappe.get_doc({
							'doctype': 'Custom Field',
							'dt': dt,
							'fieldname': fieldname,
							'fieldtype': field.get('fieldtype'),
							'label': field.get('label'),
							'insert_after': field.get('insert_after'),
							'options': field.get('options'),
							'default': field.get('default'),
							'read_only': field.get('read_only', 0),
							'reqd': field.get('reqd', 0),
							'description': field.get('description'),
							'collapsible': field.get('collapsible', 0),
							'length': field.get('length')
						})
						custom_field.insert(ignore_permissions=True)
						print(f"Campo creado: {dt}.{fieldname}")
					else:
						print(f"Campo ya existe: {dt}.{fieldname}")
				
				except Exception as e:
					print(f"Error creando campo {dt}.{fieldname}: {str(e)}")
	
	frappe.db.commit()


def create_default_settings():
	"""Crea configuración por defecto de FacturaSend Settings"""
	
	if not frappe.db.exists("FacturaSend Settings", "FacturaSend Settings"):
		settings = frappe.get_doc({
			"doctype": "FacturaSend Settings",
			"base_url": "https://api.facturasend.com.py",
			"establecimiento": "001",
			"punto_expedicion": "001",
			"status_check_interval": 5,
			"max_retries": 3,
			"send_error_notifications": 1
		})
		settings.insert(ignore_permissions=True)
		frappe.db.commit()
		print("FacturaSend Settings creado")
	else:
		print("FacturaSend Settings ya existe")
