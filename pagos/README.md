# Checkout Pro demo con Orders API

Implementacion academica: no se compran instrumentos financieros. La simulacion gratuita sigue disponible.
El snapshot financiero (cantidad, cotizacion y moneda original) no es el importe cobrado: el cobro demo
es un importe fijo ARS configurado por el operador, independiente de cantidad y sin conversion USD/ARS.
La aprobacion registra una inversion simulada usando exclusivamente ese snapshot.

## Estado de habilitacion y conflicto documental

Deshabilitado por defecto. Produccion esta bloqueada tanto por configuracion como por constraint DB.
No se realizaron llamadas reales a Mercado Pago. La migracion se genero; no se aplico a la base real.

La guia oficial de creacion y la guia de pruebas indican **Access Token de prueba**, mientras que el
error `invalid_credentials` en la referencia GET dice que no admite credenciales de prueba y pide
credenciales de produccion de un usuario de prueba. No se resuelve esta contradiccion por inferencia.
Esta entrega admite conservadoramente solo `TEST-...`, y rechaza `APP_USR-...` incluso si pertenece a
un usuario de prueba. El prefijo es una restriccion local, no una prueba universal del entorno remoto.
Si la aplicacion concreta requiere APP_USR de un usuario de prueba, detener la habilitacion y confirmar
con Mercado Pago el mecanismo verificable de contexto test antes de ampliar el cliente. No cambiar
el token por credenciales reales para sortear el bloqueo. No se utiliza el prefijo ORDTST como contrato:
la referencia tambien contiene ejemplos ORD; se comprueban contexto, vendedor y aplicacion.

## Configuracion manual

Copiar las seis variables de `.env.example` a `.env` manualmente, nunca versionar secretos:

- `MERCADOPAGO_ENABLED=False`: mantener asi hasta verificar credenciales y HTTPS.
- `MERCADOPAGO_ENVIRONMENT=test`: unico entorno permitido.
- `MERCADOPAGO_ACCESS_TOKEN`: exclusivamente token de prueba compatible con la restriccion anterior.
- `MERCADOPAGO_WEBHOOK_SECRET`: secreto de firma del panel de la aplicacion.
- `MERCADOPAGO_PUBLIC_BASE_URL`: origen HTTPS publico real, sin path ni barra final.
- `MERCADOPAGO_DEMO_AMOUNT_ARS`: importe positivo explicito, hasta dos decimales; sin default monetario.

Con pagos deshabilitados no se exige completar las otras variables y Django arranca normalmente.
Con pagos habilitados `manage.py check` verifica la configuracion y los servicios vuelven a validarla.
No se necesita Public Key, SDK frontend ni una URL API configurable.

1. Respaldar DB y ejecutar `python manage.py migrate` para aplicar `pagos/0001_initial.py`.
2. Crear/configurar la aplicacion Checkout Pro (Orders) argentina en Tus integraciones.
3. Verificar el tipo de credencial de prueba segun la discrepancia documentada.
4. Preparar HTTPS publico temporal; no se configuro ningun tunel automaticamente.
5. En el panel configurar evento **Order (Mercado Pago)** y URL:
   `<origen-HTTPS>/pagos/webhooks/mercadopago/`.
6. Completar variables; ejecutar `python manage.py check`; reiniciar Gunicorn si corresponde.
7. Iniciar sesion en QuantEdge, abrir checkout desde una tarjeta o detalle, seleccionar cantidad,
   revisar por separado el snapshot y ARS demo; enviar a Mercado Pago.
8. Usar solo comprador y tarjetas oficiales de prueba. Nunca tarjeta ni pago real.
9. Confirmar la acreditacion local y comprobar que un reenvio de webhook no duplica la inversion.
10. Ejecutar `python manage.py reconciliar_pagos --limit 100` si se pierde una notificacion.

## Windows, VM y HTTPS temporal

`http://127.0.0.1:8080` sirve para la demostracion local, pero no es accesible desde Mercado Pago.
El operador debe seleccionar y configurar un tunel HTTPS temporal hacia la VM o desarrollo,
con host real autorizado en `DJANGO_ALLOWED_HOSTS`. Mantener el panel admin fuera de la exposicion
publica. No se modifico Nginx ni la politica HTTPS de la VM en esta tarea.

Las URLs de retorno se capturan desde PUBLIC_BASE_URL al crear la orden; no dependen del Host del
navegador ni cambian durante un reintento. Iniciar el flujo autenticado desde ese mismo host publico
permite conservar la sesion al regresar. La terminacion TLS del tunel y los POST CSRF requieren una
configuracion explicita de proxy confiable/origen CSRF en ese entorno; no activar confianza global
en X-Forwarded-Proto ni deshabilitar CSRF. Esta configuracion depende del tunel y queda pendiente.

## Cliente y SDK

Se inspecciono el wheel oficial **mercadopago 3.6.0** sin instalarlo: requiere Python >=3.10,
compatible por metadata con Python 3.13; incluye ejemplo `create_order_checkout_pro.py` y soporte Orders.
El cliente usa `requests` ya existente para dos operaciones HTTP; no se agrega una dependencia
que no se usa. No se afirma que el SDK carezca de soporte.

POST `/v1/orders`: type online, processing_mode manual, capture_mode automatic, clave estable,
external_reference UUID y config.online con success_url/pending_url/failure_url/auto_return.
El item representa la demo, cantidad 1, precio ARS fijo. No se envia el activo financiero como venta.
GET `/v1/orders/{id}` verifica el estado. Timeout connect/read 3/7 segundos, sin retries ni redirects.
La URL de checkout se valida contra HTTPS y la ruta de Mercado Pago Argentina con el ID esperado.
No se almacenan tarjetas, payer, client_token, tokens ni cuerpos remotos completos.

## Estados y efectos

| Remoto | Interno | Efecto |
|---|---|---|
| created / created; processing / in_process o pending_review_manual | PENDING | Ninguno |
| action_required / waiting_capture | ACTION_REQUIRED | Ninguno; no captura automatica local |
| processed / accredited | APPROVED | Una inversion usando snapshot |
| failed / detalle de rechazo documentado | REJECTED | Ninguno |
| canceled / canceled | CANCELLED | Ninguno |
| processed / refunded o refunded / refunded | REFUNDED | Inversion historica inactiva |
| partially_refunded o transactions.chargebacks | REVIEW_REQUIRED | No reducir unidades |
| Desconocido, contradiccion, ID/importes/moneda/contexto incorrectos | REVIEW_REQUIRED | No acreditar |

CREATED existe antes del request; ERROR es un fallo recuperable de transporte/creacion.
PARTIALLY_REFUNDED esta declarado para evolucion del dominio; en esta entrega el parcial exige REVIEW_REQUIRED.
APPROVED requiere ademas importe total pagado correcto y transacciones acreditadas que sumen el importe demo.
Se valida ID, referencia, importe ARS, type/mode, pais argentino, vendedor y aplicacion; live_mode true se rechaza.
Las actualizaciones anteriores se ignoran. Una aprobacion no retrocede a pendiente/rechazada/cancelada.
REFUNDED no se reactiva; REVIEW_REQUIRED no se libera automaticamente salvo reembolso total verificado.
El admin es de consulta, incluida la inversion vinculada. Resolver una revision requiere investigar y
una intervencion tecnica auditada; no se proporciona una accion manual para acreditar.

## Idempotencia y transacciones

1. Formulario firmado (usuario/activo/UUID, 24 h), submission_key unica. Cantidad y precio se validan
   server-side; bloqueo de Producto serializa el doble POST y obtiene el precio vigente.
2. Orden, clave UUID y payload minimo se guardan antes de HTTP. Lease de 30 s evita iniciar dos requests
   simultaneas. Reintentar una intencion conserva key y payload incluso si cambia la configuracion.
   Un timeout no crea otra intencion. No reutilizar una orden para cambiar importe/cantidad.
3. PaymentService usa atomic + select_for_update sobre OrdenPago y OneToOne inversion.
   Un ID externo de transaccion es unico y nunca se reasigna a otra orden. Acreditacion, notificacion
   interna, transacciones y auditoria se confirman juntos; cualquier fallo revierte todo.

Webhook adelantado a la respuesta de creacion: consulta remota y asociacion por external_reference
solo a una intencion ya iniciada, seguida de las mismas validaciones. No hay llamadas HTTP dentro
 del bloqueo transaccional. El comando comparte PaymentService y consulta solo PENDING/ACTION_REQUIRED/ERROR;
si falta el ID, recupera la misma creacion con su key/payload antes de consultar. No busca estados terminales.
Por eso los reembolsos de aprobadas dependen de los webhooks: vigilar entregas y reintentar desde el panel.

## Firma y respuestas

Solo el webhook esta exento de CSRF: el emisor es externo y se autentica mediante HMAC-SHA256.
Se exigen x-signature (ts y v1), x-request-id y un unico data.id en query; ID y type deben coincidir
con el JSON. Se firma `id:{data.id};request-id:{x-request-id};ts:{ts};` con compare_digest,
conservando el ID como en SDK 3.6.0. El cuerpo no decide el estado; se consulta el recurso autenticado.

No se usa tolerancia temporal: el validator 3.6.0 documenta ms pero calcula int(ts)*1000.
No se inventa otra unidad. El replay no duplica efectos por la verificacion server-to-server y DB.
401 firma ausente/invalida; 400 estructura/IDs inconsistentes; 200 procesado, duplicado o revision
persistida; 503 fallo transitorio. Procesamiento sin Celery/Redis, con timeout corto.
Los errores guardados son codigos constantes, no mensajes del proveedor.

## Tests

`python manage.py test pagos --noinput`: suite unittest offline, incluido TransactionTestCase con
conexiones independientes a MariaDB para concurrencia. Con SQLite se omiten los tests de locks.
`pytest -q -p no:cacheprovider`: conftest bloquea HTTP real para todas las suites.
Los tests Django de pagos bloquean requests por separado y mockean cliente/transporte.
Las migraciones se aplican solo en las DB temporales de tests durante la verificacion.

## Fuentes oficiales verificadas

- https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-orders/create-order
- https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-pro/get-order/get
- https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-orders/payment-management/status/order-status
- https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-orders/notifications
- https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-orders/integration-test/test-purchase-with-card
- https://pypi.org/project/mercadopago/3.6.0/
- https://github.com/mercadopago/sdk-python
