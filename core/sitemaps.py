from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from vistaprevia.models import Producto


class StaticViewSitemap(Sitemap):
    def items(self):
        return ("home", "ranking_activos", "comparador_activos", "contacto")

    def location(self, item):
        return reverse(item)


class ProductoSitemap(Sitemap):
    def items(self):
        # No lastmod: sync services do not consistently update a content timestamp.
        return Producto.objects.filter(activo=True).order_by("pk")
