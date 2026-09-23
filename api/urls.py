from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProductoViewSet, RankingView


app_name = "api"


router = DefaultRouter()

router.register(
    "activos",
    ProductoViewSet,
    basename="activo",
)


urlpatterns = [
    path(
        "ranking/",
        RankingView.as_view(),
        name="ranking",
    ),
    path(
        "",
        include(router.urls),
    ),
]