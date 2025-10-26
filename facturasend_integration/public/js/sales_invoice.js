// Copyright (c) 2025, Luis and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.is_return) {
			// Botón para enviar a FacturaSend
			if (!frm.doc.facturasend_cdc || frm.doc.facturasend_estado === 'Error' || frm.doc.facturasend_estado === 'Rechazado') {
				frm.add_custom_button(__('Enviar a FacturaSend'), function() {
					send_to_facturasend(frm);
				}, __('FacturaSend'));
			}
			
			// Botón para descargar KUDE si ya tiene CDC
			if (frm.doc.facturasend_cdc) {
				frm.add_custom_button(__('Descargar KUDE'), function() {
					download_kude(frm);
				}, __('FacturaSend'));
			}
			
			// Botón para consultar estado
			if (frm.doc.facturasend_cdc) {
				frm.add_custom_button(__('Consultar Estado'), function() {
					check_status(frm);
				}, __('FacturaSend'));
			}
		}
		
		// Auto-rellenar establecimiento y punto desde la serie
		if (frm.doc.__islocal) {
			frm.trigger('extract_establecimiento_punto');
		}
	},
	
	naming_series: function(frm) {
		frm.trigger('extract_establecimiento_punto');
	},
	
	extract_establecimiento_punto: function(frm) {
		if (frm.doc.naming_series) {
			// Formato: FC-001-001-.#######
			let parts = frm.doc.naming_series.split('-');
			if (parts.length >= 3) {
				frm.set_value('facturasend_establecimiento', parts[1]);
				frm.set_value('facturasend_punto', parts[2]);
			}
		}
	}
});

function send_to_facturasend(frm) {
	frappe.confirm(
		__('¿Está seguro de enviar este documento a FacturaSend?'),
		function() {
			frappe.call({
				method: 'facturasend_integration.facturasend_integration.api.send_batch_to_facturasend',
				args: {
					documents: [{
						doctype: 'Sales Invoice',
						name: frm.doc.name
					}]
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint(__('Documento enviado exitosamente a FacturaSend'));
						frm.reload_doc();
						
						// Descargar KUDE automáticamente
						if (r.message.lote_id) {
							setTimeout(function() {
								download_lote_kude(r.message.lote_id);
							}, 1000);
						}
					} else {
						frappe.msgprint(__('Error al enviar: ') + (r.message.error || 'Error desconocido'));
					}
				}
			});
		}
	);
}

function download_kude(frm) {
	frappe.call({
		method: 'facturasend_integration.facturasend_integration.api.download_batch_kude',
		args: {
			documents: [{
				doctype: 'Sales Invoice',
				name: frm.doc.name
			}]
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				window.open(r.message.pdf_url, '_blank');
			} else {
				frappe.msgprint(__('Error al descargar KUDE: ') + (r.message.error || 'Error desconocido'));
			}
		}
	});
}

function download_lote_kude(lote_id) {
	frappe.call({
		method: 'facturasend_integration.facturasend_integration.api.download_lote_kude',
		args: {
			lote_id: lote_id
		},
		callback: function(r) {
			if (r.message && r.message.pdf_url) {
				window.open(r.message.pdf_url, '_blank');
			}
		}
	});
}

function check_status(frm) {
	// Esta función se puede implementar para consultar el estado de un documento individual
	frappe.msgprint(__('Consultando estado...'));
	frm.reload_doc();
}
