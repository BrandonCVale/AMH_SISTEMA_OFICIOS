function abrirPestana(evento, idTab) {
  // 1. Ocultar todos los contenidos
  // Seleccionamos todos los elementos con clase 'contenido-tab'
  var contenidos = document.getElementsByClassName("contenido-tab");
  for (var i = 0; i < contenidos.length; i++) {
    contenidos[i].classList.remove("activo"); // Quitamos la clase que los hace visibles
  }

  // 2. Desactivar todos los botones
  // Seleccionamos todos los botones con clase 'tab-btn'
  var botones = document.getElementsByClassName("tab-btn");
  for (var i = 0; i < botones.length; i++) {
    botones[i].classList.remove("activo"); // Quitamos el color azul/negrita
  }

  // 3. Mostrar el contenido actual y activar el botón clickeado
  document.getElementById(idTab).classList.add("activo");
  evento.currentTarget.classList.add("activo");
}
