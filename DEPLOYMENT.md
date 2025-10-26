# Guía de Deployment - FacturaSend Integration

## Pre-requisitos

- Servidor con ERPNext v15 instalado
- Acceso SSH al servidor
- Usuario con permisos de bench
- Git instalado
- Cuenta de FacturaSend con API Key

## Deployment en Producción

### Paso 1: Preparar Repositorio GitHub

1. Crear repositorio en GitHub:
```bash
# En tu máquina local
cd c:\Users\luis\Documents\Programación\FacturaSend_ERPNext
git init
git add .
git commit -m "Initial commit - FacturaSend Integration v0.0.1"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/facturasend_integration.git
git push -u origin main
```

2. Verificar que todos los archivos estén incluidos:
   - ✅ facturasend_integration/ (directorio principal)
   - ✅ setup.py
   - ✅ requirements.txt
   - ✅ README.md
   - ✅ license.txt
   - ✅ .gitignore
   - ✅ MANIFEST.in

### Paso 2: Instalar en Servidor

1. Conectar al servidor:
```bash
ssh usuario@servidor.com
```

2. Navegar al directorio de bench:
```bash
cd ~/frappe-bench
```

3. Obtener la app desde GitHub:
```bash
bench get-app https://github.com/TU_USUARIO/facturasend_integration.git
```

4. Instalar la app en el sitio:
```bash
bench --site tu-sitio.com install-app facturasend_integration
```

5. Migrar la base de datos:
```bash
bench --site tu-sitio.com migrate
```

6. Clear cache:
```bash
bench --site tu-sitio.com clear-cache
bench --site tu-sitio.com clear-website-cache
```

7. Reiniciar servicios:
```bash
bench restart
```

### Paso 3: Configuración Post-Instalación

1. Acceder al sitio: `https://tu-sitio.com`

2. Ir a **FacturaSend > FacturaSend Settings**

3. Configurar:
   - API Key de FacturaSend
   - Tenant ID
   - Establecimiento por defecto
   - Punto de expedición por defecto
   - Emails de notificación

4. Configurar Naming Series:
   - Settings > Naming Series > Sales Invoice
   - Agregar series según formato

5. Activar Scheduler:
```bash
bench --site tu-sitio.com enable-scheduler
```

6. Verificar que el scheduler esté funcionando:
```bash
bench --site tu-sitio.com scheduler status
```

### Paso 4: Configurar Datos Maestros

1. Actualizar Customers con datos de FacturaSend
2. Actualizar Items con códigos de barras
3. Actualizar Users con datos de documento

### Paso 5: Testing en Producción

1. Crear una factura de prueba
2. Enviar a FacturaSend
3. Verificar CDC recibido
4. Descargar KUDE
5. Esperar 5 minutos y verificar actualización de estado

## Actualización de la App

### Actualizar desde GitHub

```bash
# En el servidor
cd ~/frappe-bench

# Actualizar código
bench get-app facturasend_integration --branch main

# O si ya está instalada
cd apps/facturasend_integration
git pull origin main
cd ../..

# Migrar
bench --site tu-sitio.com migrate

# Clear cache
bench --site tu-sitio.com clear-cache

# Reiniciar
bench restart
```

### Actualizar Versión

1. Actualizar `__version__` en `facturasend_integration/__init__.py`
2. Commit y push a GitHub
3. En servidor, hacer pull y migrate

## Monitoreo en Producción

### Logs

```bash
# Ver logs en tiempo real
tail -f ~/frappe-bench/logs/[sitio]/worker.log
tail -f ~/frappe-bench/logs/[sitio]/web.log
tail -f ~/frappe-bench/logs/[sitio]/schedule.log

# Ver errores específicos de FacturaSend
grep -i "facturasend" ~/frappe-bench/logs/[sitio]/*.log
```

### Verificar Scheduled Jobs

```bash
# Ver estado del scheduler
bench --site tu-sitio.com scheduler status

# Ver scheduled events
bench --site tu-sitio.com scheduler

# Ejecutar manualmente el job de estados
bench --site tu-sitio.com execute facturasend_integration.facturasend_integration.api.check_document_status
```

### Verificar Performance

```bash
# Ver procesos de bench
bench --site tu-sitio.com doctor

# Ver uso de memoria
free -h

# Ver procesos Python
ps aux | grep python
```

## Backup y Restore

### Backup

```bash
# Backup completo del sitio
bench --site tu-sitio.com backup

# Backup solo de base de datos
bench --site tu-sitio.com backup --only-db

# Los backups se guardan en:
# ~/frappe-bench/sites/[sitio]/private/backups/
```

### Restore

```bash
# Restaurar desde backup
bench --site tu-sitio.com restore [archivo-backup]
```

## Configuración de Nginx (si aplica)

Si necesitas configurar timeout para descargas de PDF grandes:

```nginx
# /etc/nginx/sites-available/[sitio]

location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    
    # Aumentar timeouts para FacturaSend
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
}
```

Reiniciar Nginx:
```bash
sudo systemctl restart nginx
```

## Configuración de Supervisor

Verificar que bench esté corriendo con supervisor:

```bash
sudo supervisorctl status

# Deberías ver:
# frappe-bench-web:frappe-bench-web-8000    RUNNING
# frappe-bench-workers:frappe-bench-workers RUNNING
```

## Seguridad

### 1. Proteger API Key

La API Key se guarda encriptada en la base de datos automáticamente por Frappe (campo tipo Password).

### 2. HTTPS

Asegúrate de que el sitio esté usando HTTPS:

```bash
# Instalar certificado SSL con Let's Encrypt
sudo bench setup lets-encrypt [sitio]
```

### 3. Firewall

Asegurar que solo los puertos necesarios estén abiertos:

```bash
sudo ufw status
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 22/tcp    # SSH
sudo ufw enable
```

### 4. Permisos de Archivos

```bash
# Verificar permisos correctos
cd ~/frappe-bench
chmod -R 755 sites/[sitio]
chown -R frappe:frappe sites/[sitio]
```

## Troubleshooting en Producción

### Error: "App not installed"

```bash
bench --site tu-sitio.com list-apps
# Si no aparece facturasend_integration:
bench --site tu-sitio.com install-app facturasend_integration
```

### Error: "Module not found"

```bash
# Verificar instalación
cd ~/frappe-bench/apps
ls -la | grep facturasend

# Reinstalar si es necesario
bench get-app [url-github] --branch main
```

### Error: "Scheduler not running"

```bash
# Verificar
bench --site tu-sitio.com scheduler status

# Habilitar
bench --site tu-sitio.com enable-scheduler

# Reiniciar supervisor
sudo supervisorctl restart all
```

### Error: "Database migration failed"

```bash
# Ver detalles del error
bench --site tu-sitio.com migrate --verbose

# Si hay problemas con custom fields, eliminar y recrear:
bench --site tu-sitio.com console
>>> frappe.db.sql("DELETE FROM `tabCustom Field` WHERE module='FacturaSend Integration'")
>>> frappe.db.commit()
>>> exit()

bench --site tu-sitio.com migrate
```

### Performance Issues

```bash
# Optimizar base de datos
bench --site tu-sitio.com mariadb
> OPTIMIZE TABLE `tabSales Invoice`;
> OPTIMIZE TABLE `tabFacturaSend Log`;
> exit

# Clear cache
bench --site tu-sitio.com clear-cache
bench build --app facturasend_integration
```

## Rollback

Si necesitas revertir a una versión anterior:

```bash
# 1. Restaurar código
cd ~/frappe-bench/apps/facturasend_integration
git log --oneline  # Ver commits
git checkout [hash-del-commit-anterior]

# 2. Restaurar base de datos desde backup
bench --site tu-sitio.com restore [archivo-backup]

# 3. Reiniciar
bench restart
```

## Monitoring Continuo

### Setup de Cron para Monitoreo

Crear script de monitoreo:

```bash
# ~/monitor_facturasend.sh
#!/bin/bash

SITE="tu-sitio.com"
EMAIL="admin@tu-sitio.com"

# Contar documentos con error
ERROR_COUNT=$(bench --site $SITE console <<EOF
import frappe
print(frappe.db.count('Sales Invoice', {'facturasend_estado': 'Error'}))
EOF
)

if [ "$ERROR_COUNT" -gt 10 ]; then
    echo "ALERTA: $ERROR_COUNT documentos con error en FacturaSend" | mail -s "FacturaSend Alert" $EMAIL
fi
```

Agregar a crontab:

```bash
crontab -e

# Ejecutar cada hora
0 * * * * /home/frappe/monitor_facturasend.sh
```

## Checklist de Deployment

- [ ] Repositorio GitHub creado y código subido
- [ ] App instalada en servidor con `bench get-app`
- [ ] App instalada en sitio con `bench install-app`
- [ ] Migración ejecutada exitosamente
- [ ] FacturaSend Settings configurado con API Key
- [ ] Naming Series configuradas
- [ ] Scheduler habilitado y funcionando
- [ ] SSL/HTTPS configurado
- [ ] Backups automáticos configurados
- [ ] Permisos de roles asignados
- [ ] Customers configurados con datos FacturaSend
- [ ] Test de envío exitoso
- [ ] Test de descarga de KUDE exitoso
- [ ] Monitoreo de logs configurado
- [ ] Notificaciones por email funcionando

## Soporte Post-Deployment

Para problemas o consultas:
- Revisar logs en el servidor
- Verificar Error Log en ERPNext UI
- Consultar documentación de FacturaSend
- Contactar soporte: luis@example.com
