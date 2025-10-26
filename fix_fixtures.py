import json
import os

# Lista de archivos a procesar
files = [
    'custom_fields_customer.json',
    'custom_fields_sales_invoice.json',
    'custom_fields_item.json',
    'custom_fields_user.json'
]

fixtures_dir = r'c:\Users\luis\Documents\Programación\FacturaSend_ERPNext\facturasend_integration\fixtures'

for filename in files:
    filepath = os.path.join(fixtures_dir, filename)
    
    # Leer archivo
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Agregar doctype a cada item
    for item in data:
        if 'doctype' not in item:
            item['doctype'] = 'Custom Field'
    
    # Guardar archivo
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent='\t', ensure_ascii=False)
    
    print(f'✓ Fixed {filename}')

print('\n✅ All fixture files fixed!')
