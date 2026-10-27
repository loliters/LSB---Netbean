'use strict';

/* Buscador en tiempo real y filtro de estado de la tabla de estudiantes. */
(() => {
  document.querySelectorAll('[data-tabla-filtrable]').forEach((bloque) => {
    const texto = bloque.querySelector('[data-filtro-texto]');
    const estado = bloque.querySelector('[data-filtro-estado]');
    const contador = bloque.querySelector('[data-contador]');
    const filas = [...bloque.querySelectorAll('[data-fila]')];
    const vacio = bloque.querySelector('[data-sin-resultados]');
    const normalizar = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();

    function filtrar() {
      const consulta = normalizar(texto.value);
      const filtroEstado = estado.value;
      let visibles = 0;
      filas.forEach((fila) => {
        const coincide = normalizar(fila.dataset.busqueda).includes(consulta) && (!filtroEstado || fila.dataset.estado === filtroEstado);
        fila.hidden = !coincide;
        visibles += coincide ? 1 : 0;
      });
      if (vacio) vacio.hidden = visibles > 0 || filas.length === 0;
      contador.textContent = `${visibles} de ${filas.length}`;
    }

    texto.addEventListener('input', filtrar);
    estado.addEventListener('change', filtrar);
    filtrar();
  });
})();
