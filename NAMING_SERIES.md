# Configuración de Series de Numeración para FacturaSend

## Naming Series para Sales Invoice

Para configurar las series de numeración en ERPNext:

1. Ve a: **Settings > Naming Series**
2. Selecciona el DocType: **Sales Invoice**
3. Agrega las siguientes series según tu necesidad:

### Series Recomendadas

#### Facturas de Contado
```
FCO-001-001-.#######
```

#### Facturas a Crédito
```
FC-001-001-.#######
```

#### Notas de Crédito
```
NC-001-001-.#######
```

#### Notas de Débito
```
ND-001-001-.#######
```

### Formato de Series

El formato de las series debe seguir el patrón:
```
[PREFIJO]-[ESTABLECIMIENTO]-[PUNTO]-.#######
```

Donde:
- **PREFIJO**: Identificador del tipo de documento (FC, FCO, NC, ND)
- **ESTABLECIMIENTO**: Código de 3 dígitos del establecimiento (001, 002, etc.)
- **PUNTO**: Código de 3 dígitos del punto de expedición (001, 002, etc.)
- **.#######**: Numeración secuencial de 7 dígitos

### Ejemplos con Múltiples Puntos de Expedición

Si tienes múltiples puntos de expedición:

```
FC-001-001-.#######  # Sucursal Central, Punto 1
FC-001-002-.#######  # Sucursal Central, Punto 2
FC-002-001-.#######  # Sucursal 2, Punto 1
```

### Configuración en ERPNext

1. **Settings > Naming Series**
2. Selecciona **Sales Invoice**
3. En "Set Naming Series Options", agrega cada serie en una línea:

```
FCO-001-001-.#######
FC-001-001-.#######
NC-001-001-.#######
ND-001-001-.#######
```

4. Guarda los cambios

### Selección de Serie al Crear Documento

Al crear una nueva factura:
1. El campo "Series" mostrará todas las series disponibles
2. Selecciona la serie apropiada según el tipo de documento
3. El sistema extraerá automáticamente el establecimiento y punto para FacturaSend

### Notas Importantes

- Las series DEBEN seguir el formato especificado para que la integración funcione correctamente
- El establecimiento y punto se extraen automáticamente de la serie
- Si la serie no sigue el formato, se usarán los valores por defecto de FacturaSend Settings
- Asegúrate de que los códigos de establecimiento y punto coincidan con los registrados en SET

### Verificación

Después de configurar:
1. Crea una nueva Sales Invoice
2. Selecciona una serie
3. Verifica que los campos "Establecimiento" y "Punto de Expedición" se llenen automáticamente
4. Si no se llenan, revisa que la serie siga el formato correcto
