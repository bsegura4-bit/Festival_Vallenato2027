document.addEventListener("DOMContentLoaded", () => {
  // Mostrar u ocultar contraseña
  document.querySelectorAll("[data-ver-clave]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const campo = document.getElementById(boton.dataset.verClave);
      if (!campo) return;
      const mostrar = campo.type === "password";
      campo.type = mostrar ? "text" : "password";
      boton.textContent = mostrar ? "Ocultar" : "Mostrar";
      boton.setAttribute("aria-pressed", String(mostrar));
    });
  });
  // Filtros que se envían al cambiar de valor
  document.querySelectorAll("select[data-autoenvio]").forEach((sel) => {
    sel.addEventListener("change", () => sel.form.submit());
  });
});
