// Copyright (c) 2025, Luis and contributors
// For license information, please see license.txt

// Similar functionality for Debit Notes
frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.is_debit_note) {
			// Botón para enviar a FacturaSend
			if (!frm.doc.facturasend_cdc || frm.doc.facturasend_estado === 'Error' || frm.doc.facturasend_estado === 'Rechazado') {
				frm.add_custom_button(__('Enviar ND a FacturaSend'), function() {
					send_debit_note_to_facturasend(frm);
				}, __('FacturaSend'));
			}
			
			// Botón para descargar KUDE si ya tiene CDC
			if (frm.doc.facturasend_cdc) {
				frm.add_custom_button(__('Descargar KUDE'), function() {
					download_kude(frm);
				}, __('FacturaSend'));
			}
		}
	}
});

function send_debit_note_to_facturasend(frm) {
	frappe.confirm(
		__('¿Está seguro de enviar esta Nota de Débito a FacturaSend?'),
		function() {
			frappe.call({
				method: 'facturasend_integration.facturasend_integration.api.send_batch_to_facturasend',
				args: {
					documents: [{
						doctype: 'Debit Note',
						name: frm.doc.name
					}]
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint(__('Nota de Débito enviada exitosamente a FacturaSend'));
						frm.reload_doc();
						
						// Descargar KUDE automáticamente si hay CDCs
						if (r.message.cdcs && r.message.cdcs.length > 0) {
							setTimeout(function() {
								download_kude_by_cdcs(r.message.cdcs);
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
				doctype: 'Debit Note',
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

function download_kude_by_cdcs(cdcs) {
	frappe.call({
		method: 'facturasend_integration.facturasend_integration.api.download_kude_by_cdc',
		args: {
			cdcs: cdcs
		},
		callback: function(r) {
			if (r.message && r.message.pdf_url) {
				window.open(r.message.pdf_url, '_blank');
			} else if (r.message && r.message.error) {
				frappe.msgprint(__('Error al descargar KUDE: ') + r.message.error);
			}
		}
	});
}
