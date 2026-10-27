'use strict';

/* Marcar o desmarcar todas las filas visibles de una tabla de asignación. */
(() => {
  document.querySelectorAll('[data-marcar-todos]').forEach((boton) => {
    boton.addEventListener('click', () => {
      const bloque = boton.closest('[data-tabla-filtrable]') || document;
      const casillas = [...bloque.querySelectorAll('[data-fila]:not([hidden]) input[type="checkbox"]')];
      const marcar = casillas.some((c) => !c.checked);
      casillas.forEach((c) => { c.checked = marcar; });
      boton.textContent = marcar ? 'Desmarcar visibles' : 'Marcar visibles';
    });
  });
})();

/* Confirmación antes de acciones destructivas en botones de un formulario. */
(() => {
  document.querySelectorAll('[data-confirmar-boton]').forEach((boton) => {
    boton.addEventListener('click', (evento) => {
      if (!window.confirm(boton.dataset.confirmarBoton)) evento.preventDefault();
    });
  });
})();
