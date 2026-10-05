from rest_framework.permissions import SAFE_METHODS, BasePermission


class ProductoPermission(BasePermission):
    """
    Lectura pública.

    Las operaciones de escritura soportadas requieren
    autenticación, condición de staff y el permiso
    Django correspondiente.

    DELETE nunca recibe permiso. El ViewSet lo rechaza con 405
    antes de evaluar permisos, incluso si se agrega un mixin.
    """

    message = (
        "No tenés permisos suficientes para modificar "
        "los activos de QuantEdge."
    )

    permission_map = {
        "POST": "vistaprevia.add_producto",
        "PUT": "vistaprevia.change_producto",
        "PATCH": "vistaprevia.change_producto",
    }

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        required_permission = self.permission_map.get(
            request.method
        )

        if required_permission is None:
            return False

        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
            and request.user.has_perm(required_permission)
        )