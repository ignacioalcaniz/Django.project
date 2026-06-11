from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import ConsultaContactoForm


def contacto(request):
    if request.method == "POST":
        form = ConsultaContactoForm(request.POST)

        if form.is_valid():
            consulta = form.save(commit=False)

            if request.user.is_authenticated:
                consulta.usuario = request.user

            consulta.save()

            messages.success(
                request,
                "Tu consulta fue enviada correctamente. El equipo de QuantEdge la revisará pronto."
            )
            return redirect("contacto")
    else:
        initial_data = {}

        if request.user.is_authenticated:
            initial_data["nombre"] = request.user.username
            initial_data["email"] = request.user.email

        form = ConsultaContactoForm(initial=initial_data)

    return render(request, "contacto/contacto.html", {"form": form})
