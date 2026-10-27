'use strict';

/* Práctica con IA (HU-04 a HU-07): cámara, guía de puntos y retroalimentación guiada.
   Modo repaso: si la seña ya está dominada se puede practicar, pero no suma XP. */
(() => {
  const raiz = document.getElementById('practica');
  if (!raiz) return;

  const INTERVALO_MS = 450;        // ~2 fotogramas por segundo al servidor
  const ANCHO_ENVIO = 320;
  const SUAVIZADO = 0.35;          // interpolación de puntos por cuadro (anti parpadeo)
  const CONEXIONES = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 5], [5, 6], [6, 7], [7, 8], [5, 9], [9, 10], [10, 11],
    [11, 12], [9, 13], [13, 14], [14, 15], [15, 16], [13, 17], [17, 18], [18, 19], [19, 20], [0, 17]];
  const DEDO_DE_PUNTO = (i) => (i === 0 ? 'palma' : ['pulgar', 'indice', 'medio', 'anular', 'menique'][Math.floor((i - 1) / 4)]);
  const COLOR_DEDO = { palma: '#E2E8F0', pulgar: '#F59E0B', indice: '#38BDF8', medio: '#A78BFA', anular: '#F472B6', menique: '#34D399' };
  const NOMBRE_DEDO = { pulgar: 'pulgar', indice: 'índice', medio: 'medio', anular: 'anular', menique: 'meñique' };

  const config = {
    urlPrediccion: raiz.dataset.urlPrediccion,
    urlEvaluacion: raiz.dataset.urlEvaluacion,
    idSena: Number(raiz.dataset.idSena),
    idLeccion: Number(raiz.dataset.idLeccion),
    objetivo: (raiz.dataset.letraObjetivo || '').trim().toUpperCase(),
    umbral: Number(raiz.dataset.umbral || 70) / 100,
    segundosAuto: Number(raiz.dataset.segundosAuto || 2),
    modo: raiz.dataset.modo || 'letra',
    yaDominada: raiz.dataset.yaDominada === 'true',
  };

  // Forma esperada de los dedos (solo donde es confiable; null = no se revisa)
  const N = Number(config.objetivo);
  const FORMAS = {
    A: { consejo: 'Puño cerrado con el pulgar al costado del índice.', dedos: { indice: false, medio: false, anular: false, menique: false } },
    E: { consejo: 'Dobla las puntas de los dedos hacia la palma, con el pulgar debajo.', dedos: { indice: false, medio: false, anular: false, menique: false } },
    I: { consejo: 'Puño cerrado y solo el meñique extendido hacia arriba.', dedos: { indice: false, medio: false, anular: false, menique: true } },
    O: { consejo: 'Junta las puntas de todos los dedos formando un círculo.', dedos: null },
    U: { consejo: 'Índice y medio extendidos y juntos; anular y meñique doblados.', dedos: { indice: true, medio: true, anular: false, menique: false } },
  };
  const forma = config.modo === 'numero'
    ? { consejo: `Extiende ${N} ${N === 1 ? 'dedo' : 'dedos'} con la palma hacia la cámara.`, dedos: null, cantidad: N }
    : (FORMAS[config.objetivo] || { consejo: 'Imita la imagen de referencia con la mano completa a la vista.', dedos: null });

  const $ = (id) => document.getElementById(id);
  const el = {
    marco: raiz.querySelector('.camara__marco'), video: $('camara-video'), guia: $('camara-guia'),
    etiqueta: $('camara-etiqueta'), aviso: $('camara-aviso'), avisoTexto: $('camara-aviso-texto'),
    btnCamara: $('btn-camara'), btnEvaluar: $('btn-evaluar'), btnReintentar: $('btn-reintentar'),
    btnSiguiente: $('btn-siguiente'), btnVolverModulo: $('btn-volver-modulo'), mostrarGuia: $('mostrar-guia'),
    anillo: raiz.querySelector('.anillo'), estado: $('estado-texto'), detalle: $('feedback-detalle'),
    letra: $('letra-detectada'), consejo: $('consejo-sena'), xp: $('valor-xp'), racha: $('valor-racha'),
    dominadas: $('valor-dominadas'), total: $('valor-total'), barraLeccion: $('barra-leccion'),
    xpFlotante: $('xp-flotante'), resultado: $('resultado'), resultadoIcono: $('resultado-icono'),
    resultadoTitulo: $('resultado-titulo'), resultadoDetalle: $('resultado-detalle'),
    avisoRepaso: $('aviso-repaso'), btnApagar: $('btn-apagar'), btnApagarTexto: $('btn-apagar-texto'),
    mantener: $('mantener'), mantenerBarra: $('mantener-barra'), mantenerTexto: $('mantener-texto'),
  };
  el.consejo.textContent = forma.consejo;

  const lienzoEnvio = document.createElement('canvas');
  const contexto = el.guia.getContext('2d');

  let flujo = null, temporizador = null, enVuelo = false, pausado = false, evaluando = false;
  let inicioAcierto = null;         // performance.now() desde que la seña supera el umbral sin interrupción
  let ultimo = null;                 // última respuesta del servidor
  let puntosActuales = null;         // puntos interpolados que se dibujan
  let cajaActual = null;
  let centroAnterior = null;
  let confianzaMostrada = 0;
  let candidato = { clave: '', veces: 0 }, claveMostrada = '';

  // ---------- Captura ----------
  function capturarFrame() {
    const { videoWidth: ancho, videoHeight: alto } = el.video;
    if (!ancho) return null;
    lienzoEnvio.width = ANCHO_ENVIO;
    lienzoEnvio.height = Math.round(alto * (ANCHO_ENVIO / ancho));
    lienzoEnvio.getContext('2d').drawImage(el.video, 0, 0, lienzoEnvio.width, lienzoEnvio.height);
    return lienzoEnvio.toDataURL('image/jpeg', 0.7);
  }

  // ---------- Dibujo (requestAnimationFrame, sin parpadeos) ----------
  function ajustarLienzo() {
    const escala = window.devicePixelRatio || 1;
    const ancho = Math.round(el.guia.clientWidth * escala);
    const alto = Math.round(el.guia.clientHeight * escala);
    if (el.guia.width !== ancho || el.guia.height !== alto) {   // solo si cambió: redimensionar borra el lienzo
      el.guia.width = ancho;
      el.guia.height = alto;
    }
  }

  const mezclar = (a, b, t) => a + (b - a) * t;

  function dibujar() {
    ajustarLienzo();
    const { width: W, height: H } = el.guia;
    contexto.clearRect(0, 0, W, H);
    const objetivoPuntos = ultimo && ultimo.mano_detectada ? ultimo.puntos : null;
    if (objetivoPuntos && objetivoPuntos.length === 21) {
      puntosActuales = puntosActuales
        ? puntosActuales.map((p, i) => [mezclar(p[0], objetivoPuntos[i][0], SUAVIZADO), mezclar(p[1], objetivoPuntos[i][1], SUAVIZADO)])
        : objetivoPuntos.map((p) => [...p]);
      const caja = ultimo.caja;
      cajaActual = cajaActual ? cajaActual.map((v, i) => mezclar(v, caja[i], SUAVIZADO)) : [...caja];
    } else {
      puntosActuales = null;
      cajaActual = null;
    }
    if (cajaActual) {
      const aprobado = ultimo && aprueba(ultimo);
      contexto.strokeStyle = aprobado ? '#10B981' : 'rgba(255,255,255,.75)';
      contexto.lineWidth = 3 * (window.devicePixelRatio || 1);
      contexto.setLineDash(aprobado ? [] : [10, 8]);
      contexto.strokeRect(cajaActual[0] * W, cajaActual[1] * H, cajaActual[2] * W, cajaActual[3] * H);
      contexto.setLineDash([]);
    }
    if (puntosActuales) {
      const escala = window.devicePixelRatio || 1;
      const errores = dedosConError(ultimo);
      contexto.lineWidth = 3 * escala;
      CONEXIONES.forEach(([a, b]) => {
        contexto.strokeStyle = COLOR_DEDO[DEDO_DE_PUNTO(b)];
        contexto.beginPath();
        contexto.moveTo(puntosActuales[a][0] * W, puntosActuales[a][1] * H);
        contexto.lineTo(puntosActuales[b][0] * W, puntosActuales[b][1] * H);
        contexto.stroke();
      });
      puntosActuales.forEach(([x, y], i) => {
        const punta = [4, 8, 12, 16, 20].includes(i);
        const dedo = DEDO_DE_PUNTO(i);
        contexto.beginPath();
        contexto.arc(x * W, y * H, (punta ? 7 : 4.5) * escala, 0, Math.PI * 2);
        contexto.fillStyle = errores.includes(dedo) && punta ? '#EF4444' : '#FFFFFF';
        contexto.fill();
        contexto.lineWidth = 2 * escala;
        contexto.strokeStyle = COLOR_DEDO[dedo];
        contexto.stroke();
      });
    }
    requestAnimationFrame(dibujar);
  }

  // ---------- Análisis pedagógico ----------
  function letraCoincide(d) { return d && d.mano_detectada && (d.letra || '').toUpperCase() === config.objetivo; }
  function aprueba(d) { return letraCoincide(d) && d.confianza >= config.umbral; }

  function dedosConError(d) {
    if (!d || !d.mano_detectada || !forma.dedos || !d.dedos) return [];
    return Object.entries(forma.dedos).filter(([dedo, esperado]) => d.dedos[dedo] !== esperado).map(([dedo]) => dedo);
  }

  function evaluarPostura(d) {
    if (!d || !d.mano_detectada) return { mano: false };
    const [x, y, w, h] = d.caja;
    const tamano = Math.max(w, h);
    const centro = [x + w / 2, y + h / 2];
    const movimiento = centroAnterior ? Math.hypot(centro[0] - centroAnterior[0], centro[1] - centroAnterior[1]) : 0;
    centroAnterior = centro;
    const extendidos = Object.values(d.dedos || {}).filter(Boolean).length;
    return {
      mano: true,
      puntos: (d.puntos || []).length,
      distancia: tamano < 0.2 ? 'lejos' : tamano > 0.8 ? 'cerca' : 'ok',
      centro: Math.abs(centro[0] - 0.5) < 0.25 && Math.abs(centro[1] - 0.5) < 0.3,
      estable: movimiento < 0.06,
      errores: dedosConError(d),
      extendidos,
      formaOk: forma.cantidad ? extendidos === forma.cantidad : dedosConError(d).length === 0,
    };
  }

  function mensajeGuiado(d, p) {
    if (!p.mano) return { clave: 'sin_mano', titulo: 'No veo tu mano', detalle: 'Muestra la mano completa, con la palma hacia la cámara.' };
    if (p.distancia === 'lejos') return { clave: 'acercate', titulo: 'Acerca la mano', detalle: 'Ocupa muy poco del cuadro; acércate unos 20 cm.' };
    if (p.distancia === 'cerca') return { clave: 'alejate', titulo: 'Aleja un poco la mano', detalle: 'Los dedos salen del cuadro; aléjala unos 15 cm.' };
    if (!p.centro) return { clave: 'centra', titulo: 'Centra la mano', detalle: 'Llévala al rectángulo central para que se vean todos los dedos.' };
    if (!p.estable) return { clave: 'quieto', titulo: 'Mantén la mano quieta', detalle: 'Un segundo sin moverte ayuda a reconocer la forma.' };
    if (forma.cantidad && p.extendidos !== forma.cantidad) {
      return { clave: 'dedos', titulo: `Veo ${p.extendidos} ${p.extendidos === 1 ? 'dedo' : 'dedos'}`, detalle: `Para el ${forma.cantidad} extiende ${forma.cantidad} y dobla el resto.`, consejo: forma.consejo };
    }
    if (p.errores.length) {
      const dedo = p.errores[0];
      const extender = forma.dedos[dedo];
      return { clave: 'dedos', titulo: `${extender ? 'Extiende' : 'Dobla'} el ${NOMBRE_DEDO[dedo]}`, detalle: forma.consejo, consejo: `${extender ? 'Estirar' : 'Doblar'} dedo ${NOMBRE_DEDO[dedo]}.` };
    }
    if (!letraCoincide(d)) {
      return { clave: 'otra_letra', titulo: `Detecto «${d.letra || '?'}»`, detalle: `Buscamos «${config.objetivo}». ${forma.consejo}`, detectada: d.letra || '?' };
    }
    if (!aprueba(d)) {
      const porcentaje = Math.round(d.confianza * 100);
      return { clave: 'casi', titulo: `Casi: ${porcentaje} %`, detalle: `Necesitas ${Math.round(config.umbral * 100)} %. Marca la forma con firmeza.`, porcentaje };
    }
    return { clave: 'correcto', titulo: '¡Así es! Mantén la seña', detalle: 'Un instante más y se registra tu acierto.' };
  }

  function mostrarMensaje(m) {
    // Histéresis: un mensaje nuevo debe repetirse 2 veces antes de mostrarse (salvo el acierto)
    candidato = candidato.clave === m.clave ? { clave: m.clave, veces: candidato.veces + 1 } : { clave: m.clave, veces: 1 };
    if (m.clave !== claveMostrada && (candidato.veces >= 2 || m.clave === 'correcto')) {
      claveMostrada = m.clave;
      el.estado.textContent = m.titulo;
      el.detalle.textContent = m.detalle;
      raiz.querySelector('.feedback').dataset.tono = m.clave === 'correcto' ? 'exito' : m.clave === 'casi' ? 'aviso' : 'guia';
    } else if (m.clave === claveMostrada && m.clave === 'casi') {
      el.estado.textContent = m.titulo;  // actualiza el porcentaje sin cambiar de estado
    }
  }

  function procesar(d) {
    ultimo = d;
    const p = evaluarPostura(d);
    const objetivo = d.mano_detectada && letraCoincide(d) ? d.confianza : d.mano_detectada ? d.confianza * 0.5 : 0;
    confianzaMostrada = mezclar(confianzaMostrada, objetivo, 0.5);
    const tono = !d.mano_detectada ? 'neutro' : aprueba(d) ? 'exito' : 'aviso';
    NetBean.pintarAnillo(el.anillo, confianzaMostrada * 100, tono);
    el.letra.textContent = d.mano_detectada ? (d.letra || '—') : '—';
    el.marco.dataset.aprobado = String(aprueba(d));
    mostrarMensaje(mensajeGuiado(d, p));
    return p;
  }

  // ---------- «Mantén la seña» (aceptación automática por tiempo) ----------
  function reiniciarMantener() {
    inicioAcierto = null;
    el.mantener.hidden = true;
    el.mantenerBarra.value = 0;
  }

  function actualizarMantener(aprobada) {
    if (!aprobada) { reiniciarMantener(); return 0; }
    const ahora = performance.now();
    if (inicioAcierto === null) inicioAcierto = ahora;
    const transcurrido = (ahora - inicioAcierto) / 1000;
    const restante = Math.max(0, config.segundosAuto - transcurrido);
    el.mantener.hidden = false;
    el.mantenerBarra.value = Math.min(100, (transcurrido / config.segundosAuto) * 100);
    el.mantenerTexto.textContent = restante > 0 ? `Mantén la seña… ${restante.toFixed(1)} s` : '¡Registrando!';
    return transcurrido;
  }

  // ---------- Resultado ----------
  function animarNumero(nodo, destino) {
    if (!nodo || destino === undefined) return;
    const inicio = Number(nodo.textContent) || 0;
    if (inicio === destino || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { nodo.textContent = destino; return; }
    const t0 = performance.now();
    const paso = (ahora) => {
      const avance = Math.min((ahora - t0) / 600, 1);
      nodo.textContent = Math.round(inicio + (destino - inicio) * avance);
      if (avance < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  }

  function panel(tono, icono, titulo, detalle) {
    el.resultado.dataset.visible = 'true';
    el.resultado.dataset.tono = tono;
    el.resultadoIcono.className = `bi ${icono}`;
    el.resultadoTitulo.textContent = titulo;
    el.resultadoDetalle.textContent = detalle;
  }

  function actualizarMarcadores(d) {
    animarNumero(el.xp, d.xp_total);
    animarNumero(el.racha, d.racha_dias);
    if (d.total_senas !== undefined) {
      el.dominadas.textContent = d.senas_dominadas;
      el.total.textContent = d.total_senas;
      el.barraLeccion.max = d.total_senas;
      el.barraLeccion.value = d.senas_dominadas;
    }
    if (d.xp_ganado) {
      el.xpFlotante.textContent = `+${d.xp_ganado}`;
      el.xpFlotante.classList.remove('marcador__flotante--activo');
      void el.xpFlotante.offsetWidth;
      el.xpFlotante.classList.add('marcador__flotante--activo');
    }
    const logros = d.logros_nuevos || [];
    if (logros.length) {
      const texto = logros.map((l) => `${l.nombre} (+${l.xp_bonus} XP)`).join(', ');
      el.resultadoDetalle.textContent += ` Nueva insignia: ${texto}.`;
    }
  }

  function completarSena(d) {
    window.clearInterval(temporizador);
    el.marco.dataset.estado = 'completada';
    el.btnEvaluar.disabled = true;
    NetBean.pintarAnillo(el.anillo, d.puntaje, 'exito');
    const repaso = d.repaso === true;
    const xpTexto = d.xp_ganado ? ` Ganaste ${d.xp_ganado} XP.` : '';
    if (repaso) {
      panel('repaso', 'bi-arrow-repeat', `¡Repaso de «${config.objetivo}» superado!`,
        `Lograste ${Math.round(d.puntaje)} % de coincidencia. Esta seña ya estaba dominada, así que no suma XP.`);
    } else if (d.leccion_completada) {
      panel('leccion', 'bi-trophy-fill', '¡Lección completada!', `Dominaste las ${d.total_senas} señas de esta lección.${xpTexto}`);
      el.btnVolverModulo.hidden = false;
    } else {
      panel('exito', 'bi-check-circle-fill', `¡Seña «${config.objetivo}» completada!`, `Lograste ${Math.round(d.puntaje)} % de coincidencia.${xpTexto}`);
    }
    if (!repaso) {
      // A partir de ahora esta seña cuenta como dominada: nuevos intentos no suman XP
      config.yaDominada = true;
      if (el.avisoRepaso) el.avisoRepaso.hidden = false;
    }
    if (el.btnSiguiente) el.btnSiguiente.className = 'btn-nb btn-nb--primario';
    el.btnReintentar.hidden = false;
    actualizarMarcadores(d);
  }

  function mostrarFallo(d) {
    const detalle = d.letra_coincide
      ? `Lograste ${Math.round(d.puntaje)} % y se necesita ${d.puntos_minimos} %. ${forma.consejo}`
      : `Detectamos «${d.letra}». ${forma.consejo}`;
    panel('aviso', 'bi-arrow-repeat', 'Todavía no', detalle);
    el.btnReintentar.hidden = false;
    actualizarMarcadores(d);
  }

  // ---------- Comunicación ----------
  async function evaluar() {
    if (evaluando) return;
    if (!flujo) { panel('aviso', 'bi-camera-video-off', 'La cámara está apagada', 'Enciéndela para poder evaluar tu seña.'); return; }
    const frame = capturarFrame();
    if (!frame) {
      panel('aviso', 'bi-hourglass-split', 'La cámara aún no está lista', 'Espera un segundo a que se vea la imagen y vuelve a intentarlo.');
      return;
    }
    evaluando = true;
    pausado = true;
    reiniciarMantener();
    el.btnEvaluar.disabled = true;
    panel('neutro', 'bi-hourglass-split', 'Evaluando…', 'Estamos comparando tu seña con la referencia.');
    try {
      const d = await NetBean.postJson(config.urlEvaluacion, { frame, id_sena: config.idSena, id_leccion: config.idLeccion });
      if (!d.registrado) {
        panel('aviso', 'bi-hand-index', 'No vimos tu mano', 'Acércate a la cámara y vuelve a intentarlo.');
        el.btnReintentar.hidden = false;
      } else if (d.es_correcta) {
        completarSena(d);
      } else {
        mostrarFallo(d);
      }
    } catch (error) {
      console.error('Fallo al registrar el intento:', error);
      const sinConexion = error.estado === undefined;
      panel('error', 'bi-exclamation-triangle-fill', 'No pudimos evaluar tu seña',
        sinConexion ? 'Se perdió la conexión con el servidor. Revisa tu internet e inténtalo otra vez.' : error.message);
      el.btnReintentar.hidden = false;
    } finally {
      evaluando = false;
      if (el.marco.dataset.estado !== 'completada') el.btnEvaluar.disabled = !flujo;
    }
  }

  async function ciclo() {
    if (enVuelo || pausado || evaluando || !flujo) return;
    const frame = capturarFrame();
    if (!frame) return;
    enVuelo = true;
    try {
      const d = await NetBean.postJson(config.urlPrediccion, { frame, modo: config.modo });
      if (pausado || evaluando || !flujo) return;
      procesar(d);
      // Tiempo continuo por encima del umbral (se reinicia si baja, cambia la letra o se pierde la mano)
      const transcurrido = actualizarMantener(aprueba(d));
      if (transcurrido >= config.segundosAuto) {
        reiniciarMantener();
        await evaluar();
      }
    } catch (error) {
      console.error('Fallo al predecir:', error);
      reiniciarMantener();
      el.estado.textContent = error.estado === 503 ? 'El reconocimiento no está disponible' : 'Se perdió la conexión';
      el.detalle.textContent = 'Reintentando…';
    } finally {
      enVuelo = false;
    }
  }

  function reanudar() {
    pausado = false;
    reiniciarMantener();
    el.resultado.dataset.visible = 'false';
    el.btnReintentar.hidden = true;
    el.btnVolverModulo.hidden = true;
    el.btnEvaluar.disabled = !flujo;
    if (el.marco.dataset.estado === 'completada' && flujo) {
      el.marco.dataset.estado = 'encendida';
      temporizador = window.setInterval(ciclo, INTERVALO_MS);
    }
    claveMostrada = '';
    NetBean.pintarAnillo(el.anillo, 0, 'neutro');
  }

  function pintarBotonCamara(encendida) {
    el.btnApagar.disabled = !encendida && !el.btnApagar.dataset.usada;
    el.btnApagar.setAttribute('aria-pressed', String(!encendida));
    el.btnApagarTexto.textContent = encendida ? 'Apagar cámara' : 'Encender cámara';
    el.btnApagar.querySelector('i').className = `bi ${encendida ? 'bi-camera-video-off' : 'bi-camera-video'}`;
  }

  async function encenderCamara() {
    if (flujo) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      el.avisoTexto.textContent = 'Tu navegador no permite usar la cámara. Prueba con Chrome, Edge o Firefox.';
      return;
    }
    try {
      flujo = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }, audio: false });
      el.video.srcObject = flujo;
      await el.video.play();
      el.aviso.hidden = true;
      el.marco.dataset.estado = 'encendida';
      el.btnApagar.dataset.usada = 'true';
      pintarBotonCamara(true);
      pausado = el.resultado.dataset.visible === 'true';   // si había un resultado en pantalla, espera «Practicar otra vez»
      el.btnEvaluar.disabled = pausado;
      window.clearInterval(temporizador);
      temporizador = window.setInterval(ciclo, INTERVALO_MS);
    } catch (error) {
      flujo = null;
      el.avisoTexto.textContent = error.name === 'NotAllowedError'
        ? 'Bloqueaste la cámara. Habilítala desde el candado de la barra de direcciones y recarga la página.'
        : 'No encontramos una cámara disponible. Conecta una y vuelve a intentar.';
    }
  }

  function apagarCamara() {
    window.clearInterval(temporizador);
    temporizador = null;
    if (flujo) flujo.getTracks().forEach((pista) => pista.stop());
    flujo = null;
    el.video.srcObject = null;
  }

  // Botón «Apagar cámara»: p. ej. si te llaman en plena lección. No se pierde el progreso ni se registran intentos.
  function apagarPorUsuario() {
    apagarCamara();
    reiniciarMantener();
    ultimo = null;
    el.marco.dataset.estado = 'apagada';
    el.btnEvaluar.disabled = true;
    el.estado.textContent = 'Cámara apagada';
    el.detalle.textContent = 'Tu progreso se conserva. Enciéndela cuando quieras seguir.';
    el.letra.textContent = '—';
    NetBean.pintarAnillo(el.anillo, 0, 'neutro');
    el.avisoTexto.textContent = 'Cámara apagada. No se registran intentos mientras está apagada.';
    el.btnCamara.textContent = 'Encender cámara';
    el.aviso.hidden = false;
    pintarBotonCamara(false);
  }

  function alternarCamara() { if (flujo) apagarPorUsuario(); else encenderCamara(); }

  // «Mostrar guía»: solo cambia la opacidad del lienzo; no oculta ni mueve nada del layout
  function aplicarGuia() {
    el.guia.classList.toggle('camara__guia--oculta', !el.mostrarGuia.checked);
    el.marco.classList.toggle('camara__marco--sin-guia', !el.mostrarGuia.checked);
  }

  el.btnCamara.addEventListener('click', encenderCamara);
  el.btnEvaluar.addEventListener('click', evaluar);
  el.btnApagar.addEventListener('click', alternarCamara);
  el.btnReintentar.addEventListener('click', reanudar);
  el.mostrarGuia.addEventListener('change', aplicarGuia);
  document.addEventListener('visibilitychange', () => {
    reiniciarMantener();
    if (evaluando) return;   // no interrumpir una evaluación en curso
    pausado = document.hidden || el.resultado.dataset.visible === 'true';
  });
  window.addEventListener('pagehide', apagarCamara);
  aplicarGuia();
  requestAnimationFrame(dibujar);
})();
