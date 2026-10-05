# Cierre tecnico QuantEdge ? 2026-10-05

Sin features nuevas, pagos reales, llamadas externas, instalaciones, commit ni push.
No se modificaron .env, proveedor Twelve Data, pesos del scoring, reglas de recomendacion,
modelos, migraciones, configuracion global MariaDB, Nginx ni Gunicorn.

## Hallazgos y cambios

| Punto | Antes | Ahora |
|---|---|---|
| Ranking REST | APIView ignoraba paginacion global | GenericAPIView: 20 por pagina, page, count/next/previous/results |
| Orden del ranking | Ya incluia desempate id | Conservado: -puntaje, -cobertura, nombre, id |
| Historico | Ultimas N en orden descendente | Ultimas N devueltas cronologicamente; empate por id |
| limite | Fallback silencioso/clamping | Entero ASCII 1..500, default 100, invalido fuera de rango 400 |
| Analytics/score limite pequeno | Forzaban al menos 20 | Respetan limite; insuficiencia de datos explicita |
| RSI plano | 100 | 50; solo subidas 100; solo bajadas 0, misma metodologia restante |
| sincronizado | Fecha presente y puntaje igual | Ademas recomendacion normalizada, cobertura, version, sin historicos creados despues ni sincronizacion de mercado posterior |
| 52 semanas | CREATE no consideraba defaults; negativos aceptados | Defaults cero, no negativos, minimo <= maximo |
| Activacion REST | PATCH podia publicar sin cotizacion | Requiere ticker, precio positivo, estado sincronizado y fecha de sincronizacion |
| Preparacion de inactivos | Servicios rechazaban siempre inactivos | Solo force=True explicitamente puede preparar datos, sin publicar |
| DELETE | Permission devolvia True | Permission rechaza; ViewSet bloquea siempre con 405, incluso ante futuro mixin |
| Admin | Score y recomendacion editables ordinariamente | Readonly; cobertura/fecha/version ya estaban protegidos; acciones existentes preservadas |
| Computo REST publico | Sin throttle | Scope compartido quantitative, 120/min |
| No finitos | Podian cruzar fronteras de calculo/sync | Rechazo antes de persistencia externa y normalizacion score; cierres corruptos excluidos de analytics |
| Favoritos | next arbitrario | Solo redirect al mismo host/esquema seguro o dashboard |
| Logout | GET mutaba sesion; link admin incompatible con POST | POST con CSRF en sitio/admin |
| MariaDB | Sin Strict Mode | STRICT_TRANS_TABLES por conexion, conservando modos existentes |

### Contratos y compatibilidad

- Ranking conserva count/results, agrega next/previous. Paginas inexistentes: comportamiento DRF 404.
  No se encontraron consumidores de estas rutas REST en templates/JS del repositorio.
- Historico conserva campos y ventana de ultimas N; cambia el orden de resultados a ascendente.
- Historico admite los intervalos del modelo; analytics/score solo 1day. Otros intervalos: 400.
- limite invalido (abc, negativo, cero, mayor que 500, fraccion): 400 sin fallback ni recorte silencioso.
- 52-week: cero significa dato desconocido. 0/0 y minimo 0/maximo conocido siguen validos.
  Un minimo positivo exige maximo conocido no menor: CREATE con solo minimo positivo devuelve 400.
  No hay limpieza destructiva de registros ni migracion.
- Para publicar no se exigen 20 historicos ni un score: una cotizacion sincronizada valida es el minimo.
  Las respuestas por historico insuficiente son parte del contrato. Crear sigue forzando activo=False.
  La accion admin existente de sincronizar mercado usa force=True y ahora puede preparar ese borrador.
  historical_sync admite force=True para preparacion explicita interna; nunca cambia activo a True.
- sincronizado expresa equivalencia del resultado actual y snapshot relevante, no un TTL arbitrario.
  No hay fecha de modificacion por barra: si una correccion historica produce exactamente el mismo
  resultado relevante, la igualdad no permite reconstruir su procedencia; no se invento un timestamp.
- Throttle DRF usa cache local existente, sin Redis: contadores por proceso/worker, no limite global
  distribuido ni defensa DDoS. 120 solicitudes/min combinadas entre historico, analytics y score,
  por usuario autenticado o IP directa. NUM_PROXIES=0 impide evasion mediante X-Forwarded-For.
  Detras de Nginx los visitantes anonimos comparten la IP del proxy y su presupuesto por worker.
  Los tests limpian cache y prueban 429/Retry-After con un limite reducido temporalmente.
- DB_STRICT_MODE=True por defecto (documentado en .env.example). init_command agrega
  STRICT_TRANS_TABLES al sql_mode de la sesion, sin reemplazar los otros modos ni modificar GLOBAL.
  DB_STRICT_MODE=False permite deshabilitarlo explicitamente; reapareceria mysql.W002.

## Ya resuelto; preservado

- Dashboard y sus metricas/graficos reciben solo activa=True; regresion nueva comprueba el total.
- Perfil conserva conteo historico y admin/exportacion conservan registros inactivos deliberadamente.
- PortfolioService, reintegros, exactly-once y arquitectura de pagos sin cambios.
- REST ya protege escrituras con staff + permisos Django; campos de mercado/scoring readonly.
- DecimalField de DRF ya rechaza NaN/Infinity en entradas; se agregaron tests sin duplicar validacion.
- Webhook de pagos es la unica excepcion CSRF; redireccion MP validada al crear, admin pagos readonly,
  sin Access Token en UI ni payloads de tarjetas. Sin cambios en estos controles.
- SECRET_KEY de desarrollo y defaults locales permanecen por compatibilidad. Produccion exige variables.
- Dependencias importadas/configuradas declaradas: Django, DRF, dotenv, requests, captcha,
  mysqlclient (backend), Pillow (ImageField), pytest/pytest-django y utilidades de tests.
  pip check: No broken requirements found. Gunicorn conserva marker Linux. requirements no se modifico.

## Archivos de esta tarea

Modificados: QuantEdge/settings.py, .env.example, api/views.py, api/serializers.py,
api/permissions.py, vistaprevia/admin.py, vistaprevia/services/analytics.py,
vistaprevia/services/market_sync.py, vistaprevia/services/historical_sync.py,
vistaprevia/services/score_sync.py, usuarios/views.py, templates/base.html,
templates/admin/base_site.html. Cambios de templates limitados al logout seguro.

Creados: api/test_quantitative.py (26 tests nuevos), docs/CIERRE_TECNICO.md.

## Verificacion final

Todos los comandos usan .venv Windows actual. Sin HTTP externo: mocks y guard de requests.

| Comando | Resultado |
|---|---|
| python manage.py check | System check identified no issues (0 silenced) |
| python manage.py makemigrations --check --dry-run | No changes detected |
| python manage.py test api --noinput | 40 tests OK, 31.259 s |
| python manage.py test pagos --noinput | 44 tests OK, 2.150 s |
| python -m pytest -q -p no:cacheprovider | 100 passed, 89 subtests passed, 34.72 s |
| git diff --check | Sin errores; avisos LF/CRLF de Git Windows |
| python -m pip check | No broken requirements found |
| python manage.py check --deploy | 7 warnings del entorno local, detallados debajo |

Los tests nuevos cubren ranking/paginacion/empates, errores de parametros, 404 publico,
analytics y score con/sin datos, snapshot obsoleto, RSI extremos, 52-week y no finitos,
activacion y preparacion inactiva sin APIs, readonly, DELETE, throttle/evasion,
Strict Mode, portfolio e historial, redirect y CSRF/logout. Los tests de pagos conservan concurrencia MariaDB.

## Warnings y condiciones de deployment

check --deploy con .env local: security.W004 (HSTS), W008 (SSL redirect), W012 (session Secure),
W016 (CSRF Secure), W009 (clave de desarrollo), W018 (DEBUG), W020 (hosts vacios).
No se silenciaron. mysql.W002 desaparecio y el test verifica @@SESSION.sql_mode.

Comprobacion adicional con override_settings temporal, sin escribir secretos ni .env:
DEBUG=False, clave aleatoria fuerte y hosts explicitos deja solo W004/W008/W012/W016.
Estos cuatro son aceptables exclusivamente para la demostracion HTTP local/LAN prevista.
Antes de deployment configurar realmente DJANGO_DEBUG=False, DJANGO_SECRET_KEY fuerte y
DJANGO_ALLOWED_HOSTS explicito. No reutilizar .env Windows ni publicar DEBUG.

No se genero ninguna migracion nueva. La migracion inicial de pagos de la tarea anterior
continua pendiente de aplicar a la base real antes de usar esas pantallas. No se ejecutaron migrate/loaddata.
La activacion externa Mercado Pago sigue condicionada a credenciales de prueba y HTTPS/webhooks,
con la discrepancia oficial ya documentada en pagos/README.md; puede desplegarse deshabilitado.
No se verifico la ejecucion real en Ubuntu/Nginx/Gunicorn en esta tarea Windows.

## Git (incluye cambios de tareas anteriores)

El diff contra HEAD no representa exclusivamente este cierre. Archivos nuevos sin seguimiento
no aparecen en git diff --stat. No se hizo staging, commit ni push.

### git status --short

```text
 M .gitignore
 M QuantEdge/settings.py
 M QuantEdge/urls.py
 M api/permissions.py
 M api/serializers.py
 M api/views.py
 M core/context_processors.py
 M core/views.py
 M requirements.txt
 M templates/admin/base_site.html
 M templates/base.html
 M templates/contacto/contacto.html
 M templates/core/home.html
 M templates/usuarios/partials/_asset_cards.html
 M templates/vistaprevia/activo_detalle.html
 M templates/vistaprevia/comparador.html
 M templates/vistaprevia/ranking.html
 M usuarios/admin.py
 M usuarios/views.py
 M vistaprevia/admin.py
 M vistaprevia/models.py
 M vistaprevia/services/analytics.py
 M vistaprevia/services/historical_sync.py
 M vistaprevia/services/market_sync.py
 M vistaprevia/services/score_sync.py
 M vistaprevia/views.py
?? .env.example
?? api/test_quantitative.py
?? conftest.py
?? core/sitemaps.py
?? deploy/
?? docs/
?? pagos/
?? static_dev/js/pagos.js
?? templates/pagos/
?? templates/robots.txt
?? tests/test_seo.py
?? usuarios/services/
```

### git diff --stat

```text
 .gitignore                                    |   5 +-
 QuantEdge/settings.py                         |  36 ++++-
 QuantEdge/urls.py                             |   9 ++
 api/permissions.py                            |  10 +-
 api/serializers.py                            |  13 +-
 api/views.py                                  | 202 ++++++++++++++++----------
 core/context_processors.py                    |  48 +++++-
 core/views.py                                 |  11 +-
 requirements.txt                              | Bin 874 -> 483 bytes
 templates/admin/base_site.html                |   2 +-
 templates/base.html                           |  27 ++--
 templates/contacto/contacto.html              |   4 +-
 templates/core/home.html                      |   4 +-
 templates/usuarios/partials/_asset_cards.html |   6 +-
 templates/vistaprevia/activo_detalle.html     |   7 +-
 templates/vistaprevia/comparador.html         |   4 +-
 templates/vistaprevia/ranking.html            |   4 +-
 usuarios/admin.py                             |  10 ++
 usuarios/views.py                             |  12 +-
 vistaprevia/admin.py                          |   2 +
 vistaprevia/models.py                         |   9 +-
 vistaprevia/services/analytics.py             |  11 +-
 vistaprevia/services/historical_sync.py       |   9 +-
 vistaprevia/services/market_sync.py           |   6 +-
 vistaprevia/services/score_sync.py            |   3 +
 vistaprevia/views.py                          |  23 ++-
 26 files changed, 350 insertions(+), 127 deletions(-)
```
