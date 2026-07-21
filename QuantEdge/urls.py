from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("", include("core.urls")),
    path("", include("vistaprevia.urls")),

    path("admin/", admin.site.urls),
    path("usuarios/", include("usuarios.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("contacto/", include("contacto.urls")),
    path("captcha/", include("captcha.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
