'use strict';

/* Gráficos del dashboard de reportes (HU-10).
   Dibujados con SVG propio: no dependen de Chart.js ni de ningún CDN, así que siempre se ven.
   Si algo falla, cada tarjeta muestra un aviso en vez de quedar vacía. */
(() => {
  const nodo = document.getElementById('datos-graficos');
  if (!nodo) return;

  let datos;
  try {
    datos = JSON.parse(nodo.textContent);
  } catch (error) {
    console.error('Reportes: datos de gráficos inválidos', error);
    return;
  }

  const C = { azul: '#1E5BB8', verde: '#10B981', ambar: '#F59E0B', rojo: '#DC2626', gris: '#CBD5E1', texto: '#42536B', rejilla: '#E2E8F0' };
  const FUENTE = getComputedStyle(document.body).fontFamily.replace(/"/g, "'");

  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const suma = (lista) => lista.reduce((a, b) => a + b, 0);

  function maximoBonito(valor) {
    if (valor <= 5) return 5;
    const base = 10 ** Math.floor(Math.log10(valor));
    const f = valor / base;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * base;
  }

  const lienzo = (ancho, alto, contenido) =>
    `<svg width="100%" height="${alto}" viewBox="0 0 ${ancho} ${alto}" font-family="${FUENTE}" font-size="12" role="presentation">${contenido}</svg>`;

  const leyenda = (x, y, items) => items.map(([color, texto], i) => {
    const px = x + i * 120;
    return `<rect x="${px}" y="${y - 9}" width="11" height="11" rx="2" fill="${color}"/><text x="${px + 16}" y="${y}" fill="${C.texto}">${esc(texto)}</text>`;
  }).join('');

  // ---- Prácticas por día (líneas) ----
  function graficoDias(cont) {
    const W = Math.max(cont.clientWidth, 280), H = cont.clientHeight || 260;
    const m = { l: 36, r: 14, t: 34, b: 28 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b, n = datos.dias.length;
    const max = maximoBonito(Math.max(1, ...datos.intentos));
    const x = (i) => m.l + (n <= 1 ? iw / 2 : (iw * i) / (n - 1));
    const y = (v) => m.t + ih - (ih * v) / max;
    let s = leyenda(m.l, 14, [[C.azul, 'Intentos'], [C.verde, 'Aciertos']]);
    for (let k = 0; k <= 4; k += 1) {
      const v = (max * k) / 4, py = y(v);
      s += `<line x1="${m.l}" x2="${W - m.r}" y1="${py}" y2="${py}" stroke="${C.rejilla}"/><text x="${m.l - 6}" y="${py + 4}" text-anchor="end" fill="${C.texto}">${Math.round(v)}</text>`;
    }
    const salto = Math.ceil(n / 8);
    datos.dias.forEach((dia, i) => {
      if (i % salto === 0 || i === n - 1) s += `<text x="${x(i)}" y="${H - 8}" text-anchor="middle" fill="${C.texto}">${esc(dia)}</text>`;
    });
    const trazo = (serie, color, relleno) => {
      if (!n) return '';
      const puntos = serie.map((v, i) => `${x(i)},${y(v)}`).join(' ');
      const area = relleno ? `<polygon points="${x(0)},${y(0)} ${puntos} ${x(n - 1)},${y(0)}" fill="${color}" opacity=".12"/>` : '';
      const circulos = serie.map((v, i) => `<circle cx="${x(i)}" cy="${y(v)}" r="3.5" fill="${color}"><title>${esc(datos.dias[i])}: ${v}</title></circle>`).join('');
      return `${area}<polyline points="${puntos}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round"/>${circulos}`;
    };
    cont.innerHTML = lienzo(W, H, s + trazo(datos.intentos, C.azul, true) + trazo(datos.aciertos, C.verde, false));
  }

  // ---- Resultado de los intentos (dona) ----
  function graficoResultado(cont) {
    const W = Math.max(cont.clientWidth, 200), H = cont.clientHeight || 240;
    const [aciertos, fallidos] = datos.resultado;
    const total = aciertos + fallidos;
    const r = Math.min(W, H - 34) * 0.34, cx = W / 2, cy = (H - 34) / 2 + 4, grosor = r * 0.42;
    const largo = 2 * Math.PI * r;
    const arco = (valor, desfase, color, nombre) => (valor ? `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="${grosor}"
      stroke-dasharray="${(largo * valor) / total} ${largo}" stroke-dashoffset="${-(largo * desfase) / total}" transform="rotate(-90 ${cx} ${cy})"><title>${nombre}: ${valor}</title></circle>` : '');
    const tasa = total ? Math.round((aciertos / total) * 100) : 0;
    const centro = `<text x="${cx}" y="${cy + 2}" text-anchor="middle" font-size="22" font-weight="700" fill="#1A365D">${tasa} %</text>
      <text x="${cx}" y="${cy + 20}" text-anchor="middle" fill="${C.texto}">de acierto</text>`;
    const base = `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${C.gris}" stroke-width="${grosor}"/>`;
    const lx = Math.max(8, cx - 105);
    cont.innerHTML = lienzo(W, H, base + arco(aciertos, 0, C.verde, 'Aciertos') + arco(fallidos, aciertos, C.gris, 'Intentos fallidos') + centro
      + leyenda(lx, H - 8, [[C.verde, `Aciertos (${aciertos})`], [C.gris, `Fallidos (${fallidos})`]]));
  }

  // ---- Señas que necesitan refuerzo (barras horizontales) ----
  function graficoSenas(cont) {
    const W = Math.max(cont.clientWidth, 280), fila = 30, n = datos.senas.length;
    const H = Math.max(n * fila + 30, 60), ml = 64, mr = 52, iw = W - ml - mr;
    let s = '';
    [0, 50, 100].forEach((v) => {
      const px = ml + (iw * v) / 100;
      s += `<line x1="${px}" x2="${px}" y1="4" y2="${H - 22}" stroke="${C.rejilla}"/><text x="${px}" y="${H - 6}" text-anchor="middle" fill="${C.texto}">${v} %</text>`;
    });
    datos.senas.forEach((nombre, i) => {
      const tasa = datos.tasas[i], py = 8 + i * fila, color = tasa < 50 ? C.rojo : tasa < 80 ? C.ambar : C.verde;
      s += `<text x="${ml - 8}" y="${py + 15}" text-anchor="end" font-weight="600" fill="#1A365D">${esc(nombre)}</text>
        <rect x="${ml}" y="${py + 3}" width="${Math.max((iw * tasa) / 100, 2)}" height="18" rx="5" fill="${color}"><title>${esc(nombre)}: ${tasa} % de acierto</title></rect>
        <text x="${ml + (iw * tasa) / 100 + 6}" y="${py + 16}" fill="${C.texto}">${tasa} %</text>`;
    });
    cont.style.height = `${H}px`;
    cont.innerHTML = lienzo(W, H, s);
  }

  const GRAFICOS = [['grafico-dias', graficoDias], ['grafico-resultado', graficoResultado], ['grafico-senas', graficoSenas]];

  function pintar() {
    GRAFICOS.forEach(([id, dibujar]) => {
      const cont = document.getElementById(id);
      if (!cont) return;
      try {
        dibujar(cont);
      } catch (error) {
        console.error(`Reportes: no se pudo dibujar ${id}`, error);
        cont.innerHTML = '<p class="texto-suave">No se pudo dibujar este gráfico. Los datos están en la tabla de abajo.</p>';
      }
    });
  }

  pintar();
  let anchoPrevio = window.innerWidth, pendiente = null;
  window.addEventListener('resize', () => {
    if (window.innerWidth === anchoPrevio) return;
    anchoPrevio = window.innerWidth;
    window.cancelAnimationFrame(pendiente);
    pendiente = window.requestAnimationFrame(pintar);
  });
})();
