from html.parser import HTMLParser
from unittest.mock import patch
from xml.etree import ElementTree

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from vistaprevia.models import Producto


class HeadParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.metadata = {}
        self.title = ""
        self.in_title = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            self.metadata[attrs.get("name", attrs.get("property"))] = attrs.get("content")
        elif tag == "link" and attrs.get("rel") == "canonical":
            self.metadata["canonical"] = attrs["href"]
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


@override_settings(ALLOWED_HOSTS=["testserver", "seo.example"])
class SEOTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.producto = Producto.objects.create(
            nombre="Apple Inc.", simbolo="AAPL", activo=True,
            descripcion='<p>Empresa tecnologica</p>\n  con "innovacion" &amp; datos.',
        )
        cls.inactivo = Producto.objects.create(nombre="Inactivo", simbolo="OFF", activo=False)
        cls.user = get_user_model().objects.create_user(username="seo-user")

    def setUp(self):
        # Analytics and scoring use only local data; fail if any HTTP request is attempted.
        network = patch("requests.sessions.Session.request", side_effect=AssertionError("Unexpected HTTP request"))
        network.start()
        self.addCleanup(network.stop)

    def head(self, path, **kwargs):
        response = self.client.get(path, **kwargs)
        self.assertEqual(response.status_code, 200)
        return HeadParser(response.content.decode())

    def test_robots_plain_text_and_dynamic_sitemap(self):
        response = self.client.get("/robots.txt", secure=True, HTTP_HOST="seo.example")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        for line in ("User-agent: *", "Disallow: /admin/", "Disallow: /api/",
                     "Disallow: /captcha/", "Disallow: /usuarios/ajax/",
                     "Sitemap: https://seo.example/sitemap.xml"):
            self.assertContains(response, line)

    def test_sitemap_exact_public_urls_and_active_products(self):
        response = self.client.get("/sitemap.xml", secure=True, HTTP_HOST="seo.example")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        xml = ElementTree.fromstring(response.content)
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = {element.text for element in xml.findall("s:url/s:loc", ns)}
        self.assertEqual(locations, {
            "https://seo.example" + path for path in (
                "/", "/ranking/", "/comparador/", "/contacto/", self.producto.get_absolute_url(),
            )
        })
        self.assertNotIn("https://seo.example" + self.inactivo.get_absolute_url(), locations)
        self.assertFalse(xml.findall("s:url/s:lastmod", ns))
        for prefix in ("/usuarios/", "/accounts/", "/api/", "/admin/", "/captcha/"):
            self.assertFalse(any(prefix in location for location in locations))

    def test_public_pages_render_consistent_metadata(self):
        descriptions = set()
        for path in ("/", "/ranking/", "/comparador/", "/contacto/"):
            with self.subTest(path=path):
                head = self.head(path + "?utm_source=test", secure=True, HTTP_HOST="seo.example")
                self.assertIn("QuantEdge", head.title)
                self.assertTrue(head.metadata["description"])
                descriptions.add(head.metadata["description"])
                self.assertEqual(head.metadata["canonical"], "https://seo.example" + path)
                self.assertEqual(head.metadata["og:url"], head.metadata["canonical"])
                self.assertEqual(head.metadata["og:title"], head.title.strip())
                self.assertEqual(head.metadata["og:description"], head.metadata["description"])
                self.assertEqual(head.metadata["og:type"], "website")
                self.assertEqual(head.metadata["robots"], "index, follow")
                self.assertNotIn("og:image", head.metadata)
        self.assertEqual(len(descriptions), 4)

    def test_detail_metadata_and_escaped_description(self):
        path = self.producto.get_absolute_url()
        head = self.head(path + "?utm_source=test", secure=True, HTTP_HOST="seo.example")
        self.assertEqual(head.title.strip(), "Apple Inc. (AAPL) | QuantEdge")
        self.assertEqual(head.metadata["og:title"], head.title.strip())
        self.assertEqual(head.metadata["description"], 'Empresa tecnologica con "innovacion" & datos.')
        self.assertEqual(head.metadata["og:description"], head.metadata["description"])
        self.assertEqual(head.metadata["canonical"], "https://seo.example" + path)
        self.assertEqual(head.metadata["og:url"], head.metadata["canonical"])
        self.assertEqual(head.metadata["robots"], "index, follow")
        self.assertNotIn("og:image", head.metadata)

    def test_detail_fallback_description_and_image(self):
        self.producto.descripcion = "<p> </p>"
        # Store only a file name: tests do not write media files.
        self.producto.imagen = "activos/apple.png"
        self.producto.save()
        head = self.head(self.producto.get_absolute_url(), secure=True, HTTP_HOST="seo.example")
        for value in ("Apple Inc.", "AAPL", self.producto.get_tipo_activo_display()):
            self.assertIn(value, head.metadata["description"])
        self.assertEqual(head.metadata["og:image"], "https://seo.example/media/activos/apple.png")

    def test_inactive_detail_is_not_public(self):
        self.assertEqual(self.client.get(self.inactivo.get_absolute_url()).status_code, 404)

    def test_auth_pages_noindex(self):
        for path in ("/accounts/login/", "/usuarios/registro/"):
            with self.subTest(path=path):
                self.assertEqual(self.head(path).metadata["robots"], "noindex, follow")

    def test_private_pages_noindex(self):
        self.client.force_login(self.user)
        for path in ("/usuarios/dashboard/", "/usuarios/perfil/", "/usuarios/mis-analisis/", "/usuarios/notificaciones/"):
            with self.subTest(path=path):
                self.assertEqual(self.head(path).metadata["robots"], "noindex, follow")

    def test_private_page_redirects_anonymous_to_noindex_login(self):
        response = self.client.get("/usuarios/dashboard/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(HeadParser(response.content.decode()).metadata["robots"], "noindex, follow")

    def test_parameterized_comparator_noindex(self):
        for query in ("activo_1=", "activo_2=", f"activo_1={self.producto.pk}", f"activo_2={self.producto.pk}"):
            with self.subTest(query=query):
                head = self.head("/comparador/?" + query)
                self.assertEqual(head.metadata["robots"], "noindex, follow")
                self.assertEqual(head.metadata["canonical"], "http://testserver/comparador/")
