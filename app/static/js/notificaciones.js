document.addEventListener("DOMContentLoaded", function () {
  // 1. Buscamos todas las alertas
  const alertas = document.querySelectorAll(".alerta");

  // 2. Si hay alertas, iniciamos el temporizador
  if (alertas.length > 0) {
    setTimeout(function () {
      alertas.forEach(function (alerta) {
        // A. Desvanecer
        alerta.style.transition = "opacity 0.5s ease";
        alerta.style.opacity = "0";

        // B. Eliminar del DOM
        setTimeout(function () {
          alerta.remove();
        }, 500);
      });
    }, 4000); // 4 segundos
  }
});
