'use strict';

/* Utilidades globales de Net Bean: anillos, ver contraseña y recuperación (HU-12). */
const NetBean = (() => {
  const CIRCUNFERENCIA = 2 * Math.PI * 52;

  function obtenerTokenCsrf() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  async function postJson(url, cuerpo) {
    const respuesta = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': obtenerTokenCsrf() },
      body: JSON.stringify(cuerpo),
      credentials: 'same-origin',
    });
    const datos = await respuesta.json().catch(() => ({}));
    if (!respuesta.ok) {
      const error = new Error(datos.error || `HTTP ${respuesta.status}`);
      error.estado = respuesta.status;
      throw error;
    }
    return datos;
  }

  function pintarAnillo(anillo, porcentaje, tono) {
    const valor = anillo.querySelector('[data-anillo-valor]');
    const texto = anillo.querySelector('[data-anillo-texto]');
    const acotado = Math.max(0, Math.min(100, Math.round(porcentaje)));
    valor.style.strokeDasharray = `${CIRCUNFERENCIA}`;
    valor.style.strokeDashoffset = `${CIRCUNFERENCIA * (1 - acotado / 100)}`;
    if (texto) texto.textContent = `${acotado}%`;
    if (tono) anillo.dataset.tono = tono;
  }

  function iniciarAnillos() {
    document.querySelectorAll('.anillo').forEach((anillo) => {
      const valor = anillo.querySelector('[data-anillo-valor]');
      pintarAnillo(anillo, Number(valor.dataset.porcentaje || 0));
    });
  }

  function iniciarVerContrasena() {
    document.querySelectorAll('[data-ver-contrasena]').forEach((boton) => {
      boton.addEventListener('click', () => {
        const entrada = boton.parentElement.querySelector('input');
        const mostrar = entrada.type === 'password';
        entrada.type = mostrar ? 'text' : 'password';
        boton.setAttribute('aria-label', mostrar ? 'Ocultar contraseña' : 'Mostrar contraseña');
        boton.querySelector('i').className = mostrar ? 'bi bi-eye-slash' : 'bi bi-eye';
      });
    });
  }

  function iniciarRecuperacion() {
    const formulario = document.getElementById('form-recuperar');
    if (!formulario) return;
    const error = document.getElementById('recuperar-error');
    formulario.addEventListener('submit', async (evento) => {
      evento.preventDefault();
      const boton = formulario.querySelector('button[type="submit"]');
      boton.disabled = true;
      error.hidden = true;
      try {
        const correo = formulario.querySelector('input[type="email"]').value;
        const datos = await postJson(formulario.dataset.urlApi, { correo });
        document.getElementById('recuperar-mensaje').textContent = datos.mensaje;
        formulario.hidden = true;
        document.getElementById('recuperar-ok').hidden = false;
      } catch (fallo) {
        error.textContent = fallo.message || 'No se pudo enviar el enlace. Intenta de nuevo.';
        error.hidden = false;
      } finally {
        boton.disabled = false;
      }
    });
  }

  function iniciarConfirmaciones() {
    document.querySelectorAll('form[data-confirmar]').forEach((formulario) => {
      formulario.addEventListener('submit', (evento) => {
        if (!window.confirm(formulario.dataset.confirmar)) evento.preventDefault();
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    iniciarAnillos();
    iniciarConfirmaciones();
    iniciarVerContrasena();
    iniciarRecuperacion();
  });

  return { postJson, pintarAnillo };
})();