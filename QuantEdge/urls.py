from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core.sitemaps import ProductoSitemap, StaticViewSitemap
from core.views import robots


urlpatterns = [
    path("robots.txt", robots, name="robots"),
    path("sitemap.xml", sitemap, {
        "sitemaps": {"static": StaticViewSitemap, "productos": ProductoSitemap},
    }, name="sitemap"),
    path("", include("core.urls")),
    path("", include("vistaprevia.urls")),

    path("admin/", admin.site.urls),
    path("usuarios/", include("usuarios.urls")),
    path("pagos/", include("pagos.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("contacto/", include("contacto.urls")),
    path("captcha/", include("captcha.urls")),

    # QuantEdge REST API
    path("api/v1/", include("api.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
