# QuantEdge: Ubuntu Desktop 24.04 LTS

Guía para una VM de demostración HTTP: Nginx :80 -> Gunicorn 127.0.0.1:8000 -> Django -> MariaDB local. Estos pasos se ejecutan en Linux salvo la exportación indicada para Windows. No reutilizar la .venv de Windows.

## 1. VM y paquetes

Recomendado: 2 vCPU, 6 GB RAM, disco dinámico de 40 GB. NAT: reenviar 127.0.0.1:8080 del host a 80 del invitado y, opcionalmente, 127.0.0.1:2222 a 22 para SSH. Acceso desde Windows: http://127.0.0.1:8080/. Para red puente, añadir la IP real de la VM a DJANGO_ALLOWED_HOSTS.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential pkg-config default-libmysqlclient-dev mariadb-server mariadb-client nginx openssh-server git curl ca-certificates
python3 --version
mariadb --version
```

Ubuntu 24.04 proporciona Python 3.12, compatible con Django 6.0.3. mysqlclient requiere los headers y herramientas de compilación anteriores. No se requieren Node, Docker, Redis ni paquetes SEO.

## 2. Usuario, directorio y código

```bash
sudo useradd --system --user-group --home-dir /srv/quantedge --shell /usr/sbin/nologin quantedge
sudo install -d -o quantedge -g www-data -m 0750 /srv/quantedge /srv/quantedge/app
```

Copiar la versión final revisada a `/srv/quantedge/app`, de modo que `manage.py` quede directamente en ese directorio. Si se usa un repositorio accesible, sustituir la URL:

```bash
sudo -u quantedge git clone URL_REAL_DEL_REPOSITORIO /srv/quantedge/app
```

Para repositorios privados, transferir el código con la cuenta administrativa mediante SCP y copiarlo al destino; no guardar credenciales Git dentro de la aplicación. Un clon solo incluye commits: comprobar que contiene los cambios SEO y deployment antes de continuar. No copiar `.venv`, `.env`, caches, logs ni dumps. Conservar las migraciones, templates y static_dev. `media/` está ignorado por Git: copiar por separado los archivos que se quieran demostrar.

```bash
sudo chown -R quantedge:www-data /srv/quantedge/app
sudo chmod -R u=rwX,g=rX,o= /srv/quantedge/app
cd /srv/quantedge/app
```

## 3. Entorno virtual y dependencias

```bash
sudo -u quantedge python3 -m venv .venv
sudo -u quantedge .venv/bin/python -m pip install --upgrade pip
sudo -u quantedge .venv/bin/python -m pip install -r requirements.txt
sudo -u quantedge .venv/bin/python -m pip check
```

Gunicorn se instala únicamente en Linux por su marker. Todas las dependencias anteriores se conservan.

## 4. MariaDB local

```bash
sudo systemctl enable --now mariadb
sudo mariadb
```

Dentro del cliente SQL, reemplazar la contraseña por una nueva, exclusiva de la VM:

```sql
CREATE DATABASE quantedge_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'quantedge_user'@'localhost' IDENTIFIED BY 'REEMPLAZAR_POR_PASSWORD_LOCAL';
GRANT ALL PRIVILEGES ON quantedge_db.* TO 'quantedge_user'@'localhost';
SELECT VERSION(), @@sql_mode;
EXIT;
```

Mantener MariaDB accesible solo localmente, sin publicar 3306. Verificar Strict Mode (STRICT_TRANS_TABLES o STRICT_ALL_TABLES); no replicar el modo no estricto del entorno Windows. Si falta, configurarlo en MariaDB antes de importar y verificar de nuevo. No otorgar permisos globales ni usar root como usuario Django.

## 5. .env propio de Linux

```bash
sudo -u quantedge cp .env.example .env
sudo chmod 600 .env
sudo -u quantedge nano .env
```

Reemplazar ambos placeholders de secretos; generar una clave aleatoria nueva, por ejemplo con `.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(50))'`. No mostrar esta clave en el video ni subir `.env` a Git.

Variables documentadas en `.env.example`: DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, TWELVE_DATA_API_KEY, TWELVE_DATA_BASE_URL y TWELVE_DATA_TIMEOUT.

Usar DJANGO_DEBUG=False. Los hosts son nombres/IP sin protocolo ni puerto: `127.0.0.1,localhost` para NAT; agregar la IP real si se utiliza red puente. La contraseña debe coincidir con la del usuario MariaDB. DB_HOST=localhost utiliza la conexión local.

Django carga este archivo con python-dotenv; systemd no contiene ni duplica secretos. Con DEBUG=False, la aplicación rechaza claves/contraseñas ausentes o placeholders y hosts vacíos o `*`. Para desarrollo Windows, el .env existente con DEBUG=True conserva el comportamiento local.

No se fuerzan HTTPS, HSTS, cookies Secure ni SECURE_PROXY_SSL_HEADER. Los formularios del mismo origen no requieren CSRF_TRUSTED_ORIGINS; el proxy conserva Host, incluido el puerto externo. No añadir comodines de CSRF.

## 6. Migraciones y datos demo

Crear los directorios de archivos y ejecutar únicamente las migraciones existentes:

```bash
sudo install -d -o quantedge -g www-data -m 0750 media staticfiles deploy/backups
sudo -u quantedge .venv/bin/python manage.py check
sudo -u quantedge .venv/bin/python manage.py migrate --noinput
```

Antes del traslado, detener temporalmente las sincronizaciones y hacer un backup SQL completo nuevo fuera del repositorio. Los SQL antiguos no incluyen los históricos actuales. La base origen auditada era MariaDB 12.2.2; Ubuntu 24.04 usa MariaDB 10.11. Para evitar depender de la compatibilidad de un dump entre versiones, importar solo los datos de mercado mediante Django en una DB recién migrada.

Exportación en Windows, desde la raíz del proyecto (solo cuando se decida transferir):

```powershell
New-Item -ItemType Directory -Force deploy/backups
.\.venv\Scripts\python.exe manage.py dumpdata vistaprevia.Producto vistaprevia.CotizacionHistorica --indent 2 --output deploy/backups/quantedge_demo.json
```

Transferir el JSON a `/srv/quantedge/app/deploy/backups/quantedge_demo.json`. Luego en Linux:

```bash
sudo chown quantedge:quantedge deploy/backups/quantedge_demo.json
sudo chmod 600 deploy/backups/quantedge_demo.json
sudo -u quantedge .venv/bin/python manage.py loaddata deploy/backups/quantedge_demo.json
sudo -u quantedge .venv/bin/python manage.py createsuperuser
sudo -u quantedge .venv/bin/python manage.py shell -c 'from vistaprevia.models import Producto, CotizacionHistorica; print("Productos", Producto.objects.count()); print("Activos", Producto.objects.filter(activo=True).count()); print("Con score", Producto.objects.filter(fecha_ultimo_score_quant__isnull=False).count()); print("Historicos", CotizacionHistorica.objects.count())'
```

En la auditoría había 3 productos activos con score y 300 cotizaciones. Comparar con los conteos del momento de exportar. Esta exportación conserva scores y relaciones, pero no usuarios, inversiones ni consultas privadas: crear una cuenta demo y preparar operaciones desde la interfaz. No importar indiscriminadamente todos los modelos: los signals de usuarios no omiten raw=True y pueden producir efectos secundarios durante loaddata. Para conservar toda la DB, ensayar por separado una restauración SQL nueva sobre un servidor compatible.

Los backups quedan ignorados solo dentro de deploy/backups; no hay una exclusión global de SQL/JSON que oculte fixtures o migraciones.

## 7. Static y media

```bash
sudo -u quantedge .venv/bin/python manage.py collectstatic --noinput
sudo chown -R quantedge:www-data staticfiles media
sudo find staticfiles media -type d -exec chmod 2750 {} \;
sudo find staticfiles media -type f -exec chmod 0640 {} \;
```

Nginx necesita lectura y acceso a los directorios padres; Gunicorn escribe en media como quantedge:www-data. No usar chmod 777. No servir el directorio del proyecto. Static se recopila desde static_dev y aplicaciones instaladas, incluido admin. Las imágenes de media no se generan con collectstatic.

## 8. Probar Django y Gunicorn

```bash
sudo -u quantedge .venv/bin/python manage.py check --deploy
sudo -u quantedge .venv/bin/gunicorn QuantEdge.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 60 --access-logfile - --error-logfile -
```

En otra terminal: `curl -I http://127.0.0.1:8000/`. Las advertencias de HTTPS del check --deploy son esperables para esta VM HTTP; revisar cualquier otra advertencia. Detener Gunicorn manual con Ctrl+C antes de iniciar systemd. No ejecutar runserver como servicio de entrega.

## 9. systemd

```bash
sudo cp deploy/quantedge.service /etc/systemd/system/quantedge.service
sudo systemctl daemon-reload
sudo systemctl enable --now quantedge
sudo systemctl status quantedge --no-pager
```

El servicio depende de MariaDB, reinicia en fallos y envía logs al journal. ProtectSystem=full no impide escribir media en /srv. El proceso no escucha en interfaces externas. Tras cambiar .env o código: `sudo systemctl restart quantedge`.

## 10. Nginx

En una VM nueva, desactivar solo el enlace del sitio predeterminado; revisar cualquier configuración existente antes de sustituirla.

```bash
sudo cp deploy/nginx-quantedge.conf /etc/nginx/sites-available/quantedge
sudo ln -sfn /etc/nginx/sites-available/quantedge /etc/nginx/sites-enabled/quantedge
if [ -L /etc/nginx/sites-enabled/default ]; then sudo unlink /etc/nginx/sites-enabled/default; fi
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

Host se transmite con $http_host para conservar el puerto NAT 8080. No publicar 8000 ni 3306. Si UFW está habilitado, permitir SSH y HTTP antes de acceder remotamente. Nginx admite subidas de hasta 10 MB.

## 11. Pruebas finales y video

```bash
curl -I http://127.0.0.1/
curl -I http://127.0.0.1/static/css/app.css
curl -I http://127.0.0.1/static/admin/css/base.css
curl http://127.0.0.1/robots.txt
curl http://127.0.0.1/sitemap.xml
curl -s -H 'Host: 127.0.0.1:8080' http://127.0.0.1/ | grep -E 'canonical|og:url'
sudo systemctl is-active mariadb quantedge nginx
```

Desde Windows abrir http://127.0.0.1:8080/: home, ranking, comparador, detalle y gráfico histórico, login, dashboard, contacto/captcha y administrador. Verificar una imagen real subida bajo /media/. Canonical, OG y Sitemap deben conservar host/puerto externos. Probar un POST de login/contacto para comprobar CSRF. Confirmar CSS de admin y ausencia de errores 500/502.

Mostrar Ubuntu con `cat /etc/os-release`, servicios activos y navegador Windows. Reiniciar la VM y comprobar inicio automático. Bootstrap, GSAP y Chart.js usan CDN: asegurar Internet en el navegador de demostración. No es necesario sincronizar Twelve Data durante el video si se importaron los datos; la clave solo es necesaria para nuevas consultas al proveedor.

## 12. Diagnóstico

```bash
sudo systemctl status quantedge nginx mariadb --no-pager
sudo journalctl -u quantedge -n 100 --no-pager
sudo journalctl -u quantedge -f
sudo nginx -t
sudo tail -n 100 /var/log/nginx/quantedge_error.log
sudo ss -ltnp
curl -I http://127.0.0.1:8000/
curl -I http://127.0.0.1/
```

400: revisar ALLOWED_HOSTS. 403 en archivos: revisar permisos con `namei -l /srv/quantedge/app/staticfiles/css/app.css`. 502: revisar Gunicorn/journal y puerto 8000. Fallo DB: revisar servicio y variables sin imprimir contraseñas. CSS ausente: ejecutar collectstatic y revisar alias. No corregir problemas activando DEBUG en la VM de entrega.

## Checkout Mercado Pago de prueba (opcional)

Mantener `MERCADOPAGO_ENABLED=False` hasta completar las seis variables documentadas en
[la guia de pagos](../pagos/README.md). `MERCADOPAGO_ENVIRONMENT=test`; importe demo ARS explicito,
Access Token de prueba, secreto webhook y origen HTTPS publico. No exponer secretos ni reutilizar
credenciales reales. Revisar la discrepancia de credenciales documentada antes de habilitar.
La VM HTTP local no recibe webhooks desde Internet: la configuracion de HTTPS temporal y CSRF
se decide al elegir el tunel. No se requiere cambiar los servicios para mantener pagos deshabilitados.
Despues de aplicar la migracion de pagos y completar configuracion, ejecutar check y reiniciar Gunicorn.
