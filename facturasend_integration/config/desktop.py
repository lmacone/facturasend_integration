from frappe import _


def get_data():
	return [
		{
			"label": _("FacturaSend"),
			"items": [
				{
					"type": "doctype",
					"name": "FacturaSend Settings",
					"label": _("FacturaSend Settings"),
					"description": _("Configuración de la integración con FacturaSend")
				},
				{
					"type": "doctype",
					"name": "FacturaSend Queue",
					"label": _("FacturaSend Queue"),
					"description": _("Gestionar envío de documentos electrónicos")
				},
				{
					"type": "doctype",
					"name": "FacturaSend Log",
					"label": _("FacturaSend Log"),
					"description": _("Historial de lotes enviados")
				}
			]
		}
	]
