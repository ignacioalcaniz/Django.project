"use strict";
document.querySelectorAll("[data-prevent-double-submit]").forEach((form) => {
    form.addEventListener("submit", (event) => {
        if (form.dataset.submitting) { event.preventDefault(); return; }
        form.dataset.submitting = "true";
        form.querySelectorAll("button[type=submit]").forEach((button) => { button.disabled = true; });
    });
});
window.addEventListener("pageshow", () => {
    document.querySelectorAll("[data-prevent-double-submit]").forEach((form) => {
        delete form.dataset.submitting;
        form.querySelectorAll("button[type=submit]").forEach((button) => { button.disabled = false; });
    });
});
const label = document.querySelector("[data-payment-status]");
if (label) {
    let attempts = 0;
    const poll = async () => {
        if (++attempts > 12) return;
        try {
            const response = await fetch(label.dataset.statusUrl, {
                credentials: "same-origin", cache: "no-store", redirect: "error",
                signal: AbortSignal.timeout(5000)
            });
            if (!response.ok) return;
            const data = await response.json();
            label.textContent = data.etiqueta;
            if (data.continuar) window.setTimeout(poll, 5000);
        } catch (_) { /* State stays server-owned; user can revisit the order. */ }
    };
    window.setTimeout(poll, 5000);
}
