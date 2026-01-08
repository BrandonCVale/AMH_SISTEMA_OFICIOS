document.addEventListener("DOMContentLoaded", function () {
  // Obtenemos referencias a los elementos del DOM
  const selectArea = document.getElementById("area_destino");
  const contenedorInfo = document.getElementById("datos_destinatario");

  // Inputs donde pondremos la info
  const inputNombre = document.getElementById("auto_nombre");
  const inputPuesto = document.getElementById("auto_puesto");
  const inputCorreo = document.getElementById("auto_correo");

  // Escuchamos el cambio en el select
  if (selectArea) {
    selectArea.addEventListener("change", function () {
      const idArea = this.value;

      // Si el usuario regresa a la opción por defecto ("-- Seleccione --")
      if (!idArea) {
        contenedorInfo.style.display = "none";
        return;
      }

      // Hacemos la petición a la API de Flask
      // Usamos comillas invertidas (backticks) para insertar la variable
      fetch(`/oficios/api/subdirector/${idArea}`)
        .then((response) => response.json())
        .then((data) => {
          if (data.encontrado) {
            // Llenamos los campos
            inputNombre.value = data.nombre;
            inputPuesto.value = data.puesto;
            inputCorreo.value = data.correo;

            // Mostramos la caja
            contenedorInfo.style.display = "block";
          } else {
            alert("AVISO: Esta área no tiene un Subdirector asignado activo.");
            contenedorInfo.style.display = "none";
            this.value = ""; // Reseteamos el select
          }
        })
        .catch((error) => {
          console.error("Error en la petición AJAX:", error);
          alert("Error al intentar obtener los datos del destinatario.");
        });
    });
  }
});
