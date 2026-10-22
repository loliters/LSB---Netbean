'use strict';

/* Práctica con IA (HU-04, HU-05, HU-06): cámara, predicción en vivo y cierre de la seña. */
(() => {
  const raiz = document.getElementById('practica');
  if (!raiz) return;

  const INTERVALO_MS = 450;     // ~2 fotogramas por segundo
  const FRAMES_ESTABLES = 2;     // coincidencias seguidas antes de registrar
  const ANCHO_ENVIO = 320;
  const CALIDAD_JPEG = 0.7;

  const config = {
    urlPrediccion: raiz.dataset.urlPrediccion,
    urlEvaluacion: raiz.dataset.urlEvaluacion,
    idSena: Number(raiz.dataset.idSena),
    idLeccion: Number(raiz.dataset.idLeccion),
    letraObjetivo: (raiz.dataset.letraObjetivo || '').trim().toUpperCase(),
    umbral: Number(raiz.dataset.umbral || 80) / 100,
  };

  const $ = (id) => document.getElementById(id);
  const el = {
    marco: raiz.querySelector('.camara__marco'),
    video: $('camara-video'),
    guia: $('camara-guia'),
    etiqueta: $('camara-etiqueta'),
    aviso: $('camara-aviso'),
    avisoTexto: $('camara-aviso-texto'),
    btnCamara: $('btn-camara'),
    btnEvaluar: $('btn-evaluar'),
    btnReintentar: $('btn-reintentar'),
    btnSiguiente: $('btn-siguiente'),
    btnVolverModulo: $('btn-volver-modulo'),
    mostrarGuia: $('mostrar-guia'),
    anillo: raiz.querySelector('.anillo'),
    estado: $('estado-texto'),
    letra: $('letra-detectada'),
    xp: $('valor-xp'),
    racha: $('valor-racha'),
    dominadas: $('valor-dominadas'),
    total: $('valor-total'),
    barraLeccion: $('barra-leccion'),
    xpFlotante: $('xp-flotante'),
    resultado: $('resultado'),
    resultadoIcono: $('resultado-icono'),
    resultadoTitulo: $('resultado-titulo'),
    resultadoDetalle: $('resultado-detalle'),
  };

  const lienzoEnvio = document.createElement('canvas');
  let flujo = null;
  let temporizador = null;
  let enVuelo = false;
  let pausado = false;
  let coincidenciasSeguidas = 0;

  const porcentaje = (valor) => Math.round(valor * 100);

  function capturarFrame() {
    const { videoWidth: ancho, videoHeight: alto } = el.video;
    if (!ancho) return null;
    lienzoEnvio.width = ANCHO_ENVIO;
    lienzoEnvio.height = Math.round(alto * (ANCHO_ENVIO / ancho));
    lienzoEnvio.getContext('2d').drawImage(el.video, 0, 0, lienzoEnvio.width, lienzoEnvio.height);
    return lienzoEnvio.toDataURL('image/jpeg', CALIDAD_JPEG);
  }

  function letraCoincide(datos) {
    return datos.mano_detectada && (datos.letra || '').toUpperCase() === config.letraObjetivo;
  }

  function aprueba(datos) {
    return letraCoincide(datos) && datos.confianza >= config.umbral;
  }

  function dibujarGuia(caja, tono) {
    const contexto = el.guia.getContext('2d');
    el.guia.width = el.guia.clientWidth;
    el.guia.height = el.guia.clientHeight;
    contexto.clearRect(0, 0, el.guia.width, el.guia.height);
    el.etiqueta.hidden = true;
    if (!caja || !el.mostrarGuia.checked) return;
    const [x, y, w, h] = caja;
    contexto.strokeStyle = tono === 'exito' ? '#10b981' : tono === 'aviso' ? '#f59e0b' : '#ffffff';
    contexto.lineWidth = 3;
    contexto.strokeRect(x * el.guia.width, y * el.guia.height, w * el.guia.width, h * el.guia.height);
    if (tono === 'exito') {
      el.etiqueta.textContent = 'Correcto';
      el.etiqueta.hidden = false;
    }
  }

  function mostrarPrediccion(datos) {
    if (!datos.mano_detectada) {
      NetBean.pintarAnillo(el.anillo, 0, 'neutro');
      el.letra.textContent = '—';
      el.estado.textContent = 'Muestra tu mano dentro del cuadro';
      dibujarGuia(null);
      return;
    }
    const tono = aprueba(datos) ? 'exito' : 'aviso';
    NetBean.pintarAnillo(el.anillo, porcentaje(datos.confianza), tono);
    el.letra.textContent = datos.letra || '—';
    if (tono === 'exito') {
      el.estado.textContent = '¡Así es! Mantén la seña';
    } else if (letraCoincide(datos)) {
      el.estado.textContent = `Casi: necesitas ${porcentaje(config.umbral)}% o más`;
    } else {
      el.estado.textContent = 'Ajusta la posición de tu mano';
    }
    dibujarGuia(datos.caja, tono);
  }

  function animarNumero(nodo, destino) {
    if (!nodo || destino === undefined) return;
    const inicio = Number(nodo.textContent) || 0;
    if (inicio === destino || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      nodo.textContent = destino;
      return;
    }
    const t0 = performance.now();
    const paso = (ahora) => {
      const avance = Math.min((ahora - t0) / 600, 1);
      nodo.textContent = Math.round(inicio + (destino - inicio) * avance);
      if (avance < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  }

  function panel(tono, icono, titulo, detalle) {
    el.resultado.hidden = false;
    el.resultado.dataset.tono = tono;
    el.resultadoIcono.className = `bi ${icono}`;
    el.resultadoTitulo.textContent = titulo;
    el.resultadoDetalle.textContent = detalle;
  }

  function actualizarMarcadores(datos) {
    animarNumero(el.xp, datos.xp_total);
    animarNumero(el.racha, datos.racha_dias);
    if (datos.total_senas !== undefined) {
      el.dominadas.textContent = datos.senas_dominadas;
      el.total.textContent = datos.total_senas;
      el.barraLeccion.max = datos.total_senas;
      el.barraLeccion.value = datos.senas_dominadas;
    }
    if (datos.xp_ganado) {
      el.xpFlotante.textContent = `+${datos.xp_ganado}`;
      el.xpFlotante.hidden = false;
      el.xpFlotante.classList.remove('marcador__flotante--activo');
      void el.xpFlotante.offsetWidth;
      el.xpFlotante.classList.add('marcador__flotante--activo');
    }
  }

  function completarSena(datos) {
    window.clearInterval(temporizador);
    el.marco.dataset.estado = 'completada';
    el.btnEvaluar.disabled = true;
    NetBean.pintarAnillo(el.anillo, datos.puntaje, 'exito');
    el.estado.textContent = 'Seña completada';
    const xpTexto = datos.xp_ganado ? ` Ganaste ${datos.xp_ganado} XP.` : '';
    if (datos.leccion_completada) {
      panel('leccion', 'bi-trophy-fill', '¡Lección completada!',
        `Dominaste las ${datos.total_senas} señas de esta lección.${xpTexto}`);
      el.btnVolverModulo.hidden = false;
    } else {
      panel('exito', 'bi-check-circle-fill', `¡Seña «${config.letraObjetivo}» completada!`,
        `Lograste ${Math.round(datos.puntaje)}% de coincidencia.${xpTexto}`);
    }
    if (el.btnSiguiente) el.btnSiguiente.className = 'btn-nb btn-nb--primario';
    el.btnReintentar.hidden = false;
    actualizarMarcadores(datos);
  }

  function mostrarFallo(datos) {
    const detalle = datos.letra_coincide
      ? `Lograste ${Math.round(datos.puntaje)}% y se necesita ${datos.puntos_minimos}%. Mantén la mano quieta y con buena luz.`
      : `Detectamos «${datos.letra}». Revisa la referencia e inténtalo otra vez.`;
    panel('aviso', 'bi-arrow-repeat', 'Todavía no', detalle);
    el.btnReintentar.hidden = false;
    actualizarMarcadores(datos);
  }

  async function evaluar() {
    const frame = capturarFrame();
    if (!frame) return;
    pausado = true;
    el.btnEvaluar.disabled = true;
    try {
      const datos = await NetBean.postJson(config.urlEvaluacion, {
        frame, id_sena: config.idSena, id_leccion: config.idLeccion,
      });
      console.info('Resultado de la evaluación:', datos);
      if (!datos.registrado) {
        panel('aviso', 'bi-hand-index', 'No vimos tu mano', 'Acércate a la cámara y vuelve a intentarlo.');
        el.btnReintentar.hidden = false;
      } else if (datos.es_correcta) {
        completarSena(datos);
      } else {
        mostrarFallo(datos);
      }
    } catch (error) {
      console.error('Fallo al registrar el intento:', error);
      panel('error', 'bi-exclamation-triangle-fill', 'No pudimos guardar el intento', error.message);
      el.btnReintentar.hidden = false;
    }
  }

  async function ciclo() {
    if (enVuelo || pausado) return;
    const frame = capturarFrame();
    if (!frame) return;
    enVuelo = true;
    try {
      const datos = await NetBean.postJson(config.urlPrediccion, { frame });
      if (pausado) return;
      mostrarPrediccion(datos);
      coincidenciasSeguidas = aprueba(datos) ? coincidenciasSeguidas + 1 : 0;
      if (coincidenciasSeguidas >= FRAMES_ESTABLES) {
        coincidenciasSeguidas = 0;
        await evaluar();
      }
    } catch (error) {
      console.error('Fallo al predecir:', error);
      el.estado.textContent = error.estado === 503
        ? 'El reconocimiento no está disponible ahora.'
        : 'Se perdió la conexión. Reintentando…';
    } finally {
      enVuelo = false;
    }
  }

  function reanudar() {
    pausado = false;
    coincidenciasSeguidas = 0;
    el.resultado.hidden = true;
    el.btnReintentar.hidden = true;
    el.btnVolverModulo.hidden = true;
    el.btnEvaluar.disabled = !flujo;
    if (el.marco.dataset.estado === 'completada' && flujo) {
      el.marco.dataset.estado = 'encendida';
      temporizador = window.setInterval(ciclo, INTERVALO_MS);
    }
    NetBean.pintarAnillo(el.anillo, 0, 'neutro');
    el.estado.textContent = 'Esperando tu seña';
  }

  async function encenderCamara() {
    if (!navigator.mediaDevices?.getUserMedia) {
      el.avisoTexto.textContent = 'Tu navegador no permite usar la cámara. Prueba con Chrome, Edge o Firefox.';
      return;
    }
    try {
      flujo = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      });
      el.video.srcObject = flujo;
      await el.video.play();
      el.aviso.hidden = true;
      el.marco.dataset.estado = 'encendida';
      el.btnEvaluar.disabled = false;
      temporizador = window.setInterval(ciclo, INTERVALO_MS);
    } catch (error) {
      el.avisoTexto.textContent = error.name === 'NotAllowedError'
        ? 'Bloqueaste la cámara. Habilítala desde el candado de la barra de direcciones y recarga la página.'
        : 'No encontramos una cámara disponible. Conecta una y vuelve a intentar.';
    }
  }

  function apagarCamara() {
    window.clearInterval(temporizador);
    if (flujo) flujo.getTracks().forEach((pista) => pista.stop());
    flujo = null;
  }

  el.btnCamara.addEventListener('click', encenderCamara);
  el.btnEvaluar.addEventListener('click', evaluar);
  el.btnReintentar.addEventListener('click', reanudar);
  el.mostrarGuia.addEventListener('change', () => dibujarGuia(null));
  document.addEventListener('visibilitychange', () => {
    pausado = document.hidden || !el.resultado.hidden;
  });
  window.addEventListener('pagehide', apagarCamara);
})();