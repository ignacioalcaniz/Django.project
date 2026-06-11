from django import template

register = template.Library()


@register.filter
def money(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "Sin dato"

    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f} T"
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f} M"

    return f"{value:,.2f}"


@register.filter
def percentage(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "0.00%"

    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


@register.filter
def score_label(score):
    try:
        score = int(score)
    except (TypeError, ValueError):
        return "Sin score"

    if score >= 85:
        return "Excelente"
    if score >= 70:
        return "Favorable"
    if score >= 50:
        return "Neutral"
    return "Débil"


@register.filter
def risk_label(risk):
    labels = {
        "bajo": "🟢 Bajo",
        "medio": "🟡 Medio",
        "alto": "🔴 Alto",
    }
    return labels.get(risk, "Sin riesgo")


@register.filter
def recommendation_label(value):
    labels = {
        "comprar": "🟢 Comprar",
        "mantener": "🔵 Mantener",
        "observar": "🟣 Observar",
        "vender": "🔴 Vender",
    }
    return labels.get(value, "Sin recomendación")