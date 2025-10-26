// Copyright (c) 2025, Luis and contributors
// For license information, please see license.txt

frappe.ui.form.on('FacturaSend Queue', {
	refresh: function(frm) {
		// Botón para cargar documentos pendientes
		frm.add_custom_button(__('Cargar Documentos'), function() {
			load_pending_documents(frm);
		});

		// Botón para previsualizar JSON
		frm.add_custom_button(__('Previsualizar JSON'), function() {
			preview_json(frm);
		}, __('Acciones'));

		// Botón para enviar lote
		frm.add_custom_button(__('Enviar Seleccionados'), function() {
			send_selected_documents(frm);
		}, __('Acciones'));
		
		// Botón para resetear reintentos
		frm.add_custom_button(__('Resetear Reintentos'), function() {
			reset_retries(frm);
		}, __('Acciones'));

		// Botón para descargar KUDEs
		frm.add_custom_button(__('Descargar KUDEs'), function() {
			download_kudes(frm);
		}, __('Acciones'));

		// Cargar documentos al abrir el formulario
		if (!frm.doc.__islocal) {
			load_pending_documents(frm);
		}
	}
});

function load_pending_documents(frm) {
	frappe.call({
		method: 'facturasend_integration.facturasend_integration.api.get_pending_documents',
		args: {
			tipo_documento: frm.doc.tipo_documento,
			desde_fecha: frm.doc.desde_fecha,
			hasta_fecha: frm.doc.hasta_fecha
		},
		callback: function(r) {
			if (r.message) {
				render_document_list(frm, r.message);
			}
		}
	});
}

function render_document_list(frm, documents) {
	if (!documents || documents.length === 0) {
		frappe.msgprint(__('No se encontraron documentos'));
		return;
	}

	let html = `
		<div class="facturasend-documents">
			<p><strong>${documents.length} documento(s) encontrado(s)</strong></p>
			<table class="table table-bordered">
				<thead>
					<tr>
						<th><input type="checkbox" id="select-all"></th>
						<th>Documento</th>
						<th>Cliente</th>
						<th>Fecha</th>
						<th>Total</th>
						<th>Estado FS</th>
						<th>CDC</th>
						<th>Acciones</th>
					</tr>
				</thead>
				<tbody id="documents-tbody">
	`;

	documents.forEach(function(doc) {
		let status_badge = '';
		if (doc.facturasend_estado) {
			let color = doc.facturasend_estado === 'Aprobado' ? 'green' : 
			           doc.facturasend_estado === 'Rechazado' ? 'red' : 
			           doc.facturasend_estado === 'Error' ? 'orange' : 'blue';
			status_badge = `<span class="badge" style="background-color: ${color}">${doc.facturasend_estado}</span>`;
		} else {
			status_badge = `<span class="badge" style="background-color: gray">Pendiente</span>`;
		}

		let retry_btn = '';
		if (doc.facturasend_estado === 'Error' || doc.facturasend_estado === 'Rechazado') {
			retry_btn = `<button class="btn btn-xs btn-warning retry-btn" data-doctype="${doc.doctype}" data-name="${doc.name}">Reintentar</button>`;
		}

		html += `
			<tr>
				<td><input type="checkbox" class="doc-checkbox" data-doctype="${doc.doctype}" data-name="${doc.name}"></td>
				<td><a href="/app/${doc.doctype.toLowerCase().replace(/ /g, '-')}/${doc.name}">${doc.name}</a></td>
				<td>${doc.customer_name || ''}</td>
				<td>${doc.posting_date || ''}</td>
				<td>${format_currency(doc.grand_total || 0, doc.currency)}</td>
				<td>${status_badge}</td>
				<td>${doc.facturasend_cdc || ''}</td>
				<td>${retry_btn}</td>
			</tr>
		`;
	});

	html += `
				</tbody>
			</table>
		</div>
	`;

	// Usar el campo HTML documents_html
	frm.fields_dict.documents_html.$wrapper.html(html);

	// Event handlers - usar setTimeout para asegurar que el DOM esté listo
	setTimeout(function() {
		$('#select-all').on('change', function() {
			$('.doc-checkbox').prop('checked', $(this).is(':checked'));
		});

		$('.retry-btn').on('click', function() {
			let doctype = $(this).data('doctype');
			let name = $(this).data('name');
			retry_document(doctype, name);
		});
	}, 100);
}

function send_selected_documents(frm) {
	let selected = [];
	$('.doc-checkbox:checked').each(function() {
		selected.push({
			doctype: $(this).data('doctype'),
			name: $(this).data('name')
		});
	});

	if (selected.length === 0) {
		frappe.msgprint(__('Por favor seleccione al menos un documento'));
		return;
	}

	if (selected.length > 50) {
		frappe.msgprint(__('No puede enviar más de 50 documentos a la vez'));
		return;
	}

	// Validar que todos sean del mismo tipo
	let tipo = selected[0].doctype;
	let all_same = selected.every(doc => doc.doctype === tipo);
	if (!all_same) {
		frappe.msgprint(__('Todos los documentos deben ser del mismo tipo'));
		return;
	}

	frappe.confirm(
		__('¿Está seguro de enviar {0} documento(s) a FacturaSend?', [selected.length]),
		function() {
			frappe.call({
				method: 'facturasend_integration.facturasend_integration.api.send_batch_to_facturasend',
				args: {
					documents: selected
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint(__('Documentos enviados exitosamente'));
						load_pending_documents(frm);
						
						// Descargar KUDEs automáticamente
						if (r.message.lote_id) {
							download_lote_kude(r.message.lote_id);
						}
					} else {
						// Construir mensaje de error detallado
						let error_html = '<div style="max-height: 400px; overflow-y: auto;">';
						error_html += '<p><strong>' + (r.message.error || 'Error desconocido') + '</strong></p>';
						
						// Si hay errores detallados del API
						if (r.message.errores && r.message.errores.length > 0) {
							error_html += '<div class="alert alert-danger"><strong>Errores de FacturaSend:</strong><ul>';
							r.message.errores.forEach(function(err) {
								error_html += '<li><strong>Documento ' + err.index + ':</strong> ' + err.error + '</li>';
							});
							error_html += '</ul></div>';
						}
						
						// Si hay detalles adicionales de conversión
						if (r.message.details && r.message.details.length > 0) {
							error_html += '<div class="alert alert-warning"><strong>Detalles:</strong><ul>';
							r.message.details.forEach(function(detail) {
								error_html += '<li>' + detail + '</li>';
							});
							error_html += '</ul></div>';
						}
						
						error_html += '</div>';
						
						frappe.msgprint({
							title: __('Error al enviar documentos'),
							message: error_html,
							indicator: 'red',
							primary_action: {
								label: __('Ver en Consola'),
								action: function() {
									console.error('FacturaSend Error:', r.message);
									frappe.msgprint(__('Error mostrado en la consola del navegador'));
								}
							}
						});
						
						// También mostrar en consola para debugging
						console.error('FacturaSend Error:', r.message);
					}
				}
			});
		}
	);
}

function retry_document(doctype, name) {
	frappe.confirm(
		__('¿Reintentar envío del documento {0}?', [name]),
		function() {
			frappe.call({
				method: 'facturasend_integration.facturasend_integration.api.send_batch_to_facturasend',
				args: {
					documents: [{doctype: doctype, name: name}]
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint(__('Documento reenviado exitosamente'));
						frappe.ui.form.get_form('FacturaSend Queue').reload_doc();
					} else {
						frappe.msgprint(__('Error al reenviar: ') + (r.message.error || 'Error desconocido'));
					}
				}
			});
		}
	);
}

function download_kudes(frm) {
	let selected = [];
	$('.doc-checkbox:checked').each(function() {
		selected.push({
			doctype: $(this).data('doctype'),
			name: $(this).data('name')
		});
	});

	if (selected.length === 0) {
		frappe.msgprint(__('Por favor seleccione al menos un documento'));
		return;
	}

	frappe.call({
		method: 'facturasend_integration.facturasend_integration.api.download_batch_kude',
		args: {
			documents: selected
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				// Descargar archivo PDF
				window.open(r.message.pdf_url, '_blank');
			} else {
				frappe.msgprint(__('Error al descargar KUDEs: ') + (r.message.error || 'Error desconocido'));
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

function preview_json(frm) {
	let selected = [];
	$('.doc-checkbox:checked').each(function() {
		selected.push({
			doctype: $(this).data('doctype'),
			name: $(this).data('name')
		});
	});

	if (selected.length === 0) {
		frappe.msgprint(__('Por favor seleccione al menos un documento'));
		return;
	}

	frappe.call({
		method: 'facturasend_integration.facturasend_integration.api.preview_facturasend_payload',
		args: {
			documents: selected
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				// Mostrar JSON en un diálogo
				let d = new frappe.ui.Dialog({
					title: __('JSON que se enviará a FacturaSend'),
					fields: [
						{
							fieldtype: 'HTML',
							fieldname: 'json_preview'
						}
					],
					size: 'extra-large'
				});
				
				let html = `
					<div style="margin-bottom: 10px;">
						<strong>Documentos procesados:</strong> ${r.message.document_count}
					</div>
				`;
				
				if (r.message.errors && r.message.errors.length > 0) {
					html += `
						<div class="alert alert-warning">
							<strong>Errores de conversión:</strong><br>
							${r.message.errors.join('<br>')}
						</div>
					`;
				}
				
				html += `
					<div>
						<button class="btn btn-xs btn-default" onclick="navigator.clipboard.writeText(this.nextElementSibling.textContent); frappe.show_alert('JSON copiado al portapapeles')">
							Copiar JSON
						</button>
						<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 600px; overflow: auto;">${r.message.payload_json}</pre>
					</div>
				`;
				
				d.fields_dict.json_preview.$wrapper.html(html);
				d.show();
				
				// También mostrar en consola
				console.log('FacturaSend Payload:', r.message.payload);
			} else {
				frappe.msgprint({
					title: __('Error'),
					message: r.message.error || 'Error desconocido',
					indicator: 'red'
				});
			}
		}
	});
}

function reset_retries(frm) {
	// Obtener documentos seleccionados
	let selected = get_selected_documents();
	
	if (selected.length === 0) {
		frappe.msgprint(__('Por favor seleccione al menos un documento'));
		return;
	}
	
	frappe.confirm(
		`¿Está seguro de resetear los reintentos de ${selected.length} documento(s)?`,
		function() {
			frappe.call({
				method: 'facturasend_integration.facturasend_integration.api.reset_document_retries',
				args: {
					documents: selected
				},
				callback: function(r) {
					if (r.message.success) {
						frappe.show_alert({
							message: r.message.message,
							indicator: 'green'
						});
						
						// Recargar documentos
						load_pending_documents(frm);
					} else {
						frappe.msgprint({
							title: __('Error'),
							message: r.message.error,
							indicator: 'red'
						});
					}
				}
			});
		}
	);
}
