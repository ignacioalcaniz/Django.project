from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import PerfilUsuario


class RegistroUsuarioForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=100, required=False, label="Nombre")
    last_name = forms.CharField(max_length=100, required=False, label="Apellido")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")


class PerfilUsuarioForm(forms.ModelForm):
    class Meta:
        model = PerfilUsuario
        fields = (
            "foto",
            "nombre_completo",
            "telefono",
            "pais",
            "perfil_inversor",
            "capital_demo",
            "biografia",
        )

        widgets = {
            "nombre_completo": forms.TextInput(attrs={"class": "profile-input"}),
            "telefono": forms.TextInput(attrs={"class": "profile-input"}),
            "pais": forms.TextInput(attrs={"class": "profile-input"}),
            "perfil_inversor": forms.Select(attrs={"class": "profile-input"}),
            "capital_demo": forms.NumberInput(attrs={"class": "profile-input"}),
            "biografia": forms.Textarea(attrs={"class": "profile-input profile-textarea", "rows": 5}),
        }