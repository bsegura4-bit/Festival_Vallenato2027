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
  // Los mensajes flotantes se cierran solos después de unos segundos
  document.querySelectorAll(".mensajes .alert").forEach((alerta, i) => {
    setTimeout(() => {
      if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(alerta).close();
      else alerta.remove();
    }, 6000 + i * 800);
  });
  // Animación de las secciones al aparecer en pantalla
  const secciones = document.querySelectorAll(".revelar");
  if ("IntersectionObserver" in window) {
    const obs = new IntersectionObserver((entradas) => {
      entradas.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add("visible"); obs.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    secciones.forEach((s) => obs.observe(s));
  } else {
    secciones.forEach((s) => s.classList.add("visible"));
  }
  // Cifras del inicio: cuentan desde 0
  const reducir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.querySelectorAll("[data-contar]").forEach((el) => {
    const fin = parseInt(el.dataset.contar, 10);
    if (reducir || !fin) return;
    let n = 0;
    const paso = Math.max(1, Math.ceil(fin / 30));
    el.textContent = "0";
    const t = setInterval(() => { n = Math.min(fin, n + paso); el.textContent = n; if (n >= fin) clearInterval(t); }, 35);
  });
});