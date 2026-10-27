'use strict';

/* Gráficos de actividad del dashboard del estudiante y del panel del administrador. */
(() => {
  if (typeof Chart === 'undefined') return;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.color = '#42536B';

  function graficoActividad(idDatos, idLienzo) {
    const nodo = document.getElementById(idDatos);
    const lienzo = document.getElementById(idLienzo);
    if (!nodo || !lienzo) return;
    const datos = JSON.parse(nodo.textContent);
    new Chart(lienzo, {
      type: 'bar',
      data: {
        labels: datos.dias,
        datasets: [
          { label: 'Intentos', data: datos.intentos, backgroundColor: 'rgba(30,91,184,.25)', borderColor: '#1E5BB8', borderWidth: 1.5, borderRadius: 6 },
          { label: 'Aciertos', data: datos.aciertos, backgroundColor: '#10B981', borderRadius: 6 },
        ],
      },
      options: {
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { grid: { display: false } } },
      },
    });
  }

  graficoActividad('datos-semana', 'grafico-semana');
  graficoActividad('datos-sistema', 'grafico-sistema');
})();
