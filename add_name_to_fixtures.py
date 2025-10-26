import json
import os

# Lista de archivos de fixtures
fixture_files = [
    'facturasend_integration/fixtures/custom_fields_customer.json',
    'facturasend_integration/fixtures/custom_fields_sales_invoice.json',
    'facturasend_integration/fixtures/custom_fields_item.json',
    'facturasend_integration/fixtures/custom_fields_user.json'
]

for fixture_file in fixture_files:
    if not os.path.exists(fixture_file):
        print(f"Archivo no encontrado: {fixture_file}")
        continue
    
    print(f"Procesando: {fixture_file}")
    
    # Leer el archivo JSON
    with open(fixture_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Agregar el campo "name" a cada objeto si no existe
    for item in data:
        if 'name' not in item and 'dt' in item and 'fieldname' in item:
            item['name'] = f"{item['dt']}-{item['fieldname']}"
            # Reordenar para que "name" esté después de "doctype"
            ordered_item = {}
            ordered_item['doctype'] = item.pop('doctype')
            ordered_item['name'] = item.pop('name')
            ordered_item.update(item)
            # Actualizar el item en la lista
            idx = data.index(item)
            data[idx] = ordered_item
    
    # Guardar el archivo con formato correcto
    with open(fixture_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent='\t', ensure_ascii=False)
        f.write('\n')
    
    print(f"  ✓ {len(data)} campos actualizados")

print("\n¡Todos los archivos de fixtures han sido actualizados!")
