from django import forms
from captcha.fields import CaptchaField
from .models import ConsultaContacto


class ConsultaContactoForm(forms.ModelForm):
    captcha = CaptchaField(label="Verificación")

    class Meta:
        model = ConsultaContacto
        fields = ["nombre", "email", "categoria", "asunto", "mensaje", "captcha"]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "placeholder": "Tu nombre",
                "class": "qe-input"
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "tuemail@ejemplo.com",
                "class": "qe-input"
            }),
            "categoria": forms.Select(attrs={
                "class": "qe-input"
            }),
            "asunto": forms.TextInput(attrs={
                "placeholder": "Motivo de la consulta",
                "class": "qe-input"
            }),
            "mensaje": forms.Textarea(attrs={
                "placeholder": "Contanos cómo podemos ayudarte...",
                "class": "qe-input qe-textarea",
                "rows": 6
            }),
        }