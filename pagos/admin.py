from django.contrib import admin
from .models import OrdenPago, PagoProveedor, EventoPago


class AuditAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)


@admin.register(OrdenPago)
class OrdenPagoAdmin(AuditAdmin):
    list_display = ("id", "usuario", "simbolo_snapshot", "importe_demo", "estado", "creada")
    list_filter = ("estado", "environment")
    search_fields = ("mp_order_id", "usuario__username", "simbolo_snapshot")


@admin.register(PagoProveedor)
class PagoProveedorAdmin(AuditAdmin):
    list_display = ("external_id", "orden", "estado", "importe", "moneda")


@admin.register(EventoPago)
class EventoPagoAdmin(AuditAdmin):
    list_display = ("orden", "origen", "resultado", "estado_nuevo", "creado")
