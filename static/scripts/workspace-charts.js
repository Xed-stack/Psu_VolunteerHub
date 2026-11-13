(() => {
  if (!window.Plotly) return;
  const layout = { font: { family: 'Inter, sans-serif', color: '#111c2c', size: 13 },
    margin: { t: 24, r: 16, b: 42, l: 90 }, paper_bgcolor: '#fff', plot_bgcolor: '#fff',
    height: 300, showlegend: false, xaxis: { rangemode: 'tozero', fixedrange: true },
    yaxis: { fixedrange: true, automargin: true } };
  const config = { responsive: true, displayModeBar: false, staticPlot: false };
  document.querySelectorAll('[data-campus-chart]').forEach(el => {
    const rows = JSON.parse(el.dataset.chartValues);
    Plotly.newPlot(el, [{ type: 'bar', orientation: 'h', x: rows.map(r => r.count),
      y: rows.map(r => r.name), marker: { color: '#00408b' }, customdata: rows.map(r => r.id),
      hovertemplate: '%{y}: %{x} conducted activities<extra></extra>' }], layout, config);
    el.on('plotly_click', event => {
      const url = new URL('/workspace/reports/results', location.origin);
      url.search = location.search;
      url.searchParams.set('campus_id', event.points[0].customdata);
      location.assign(url);
    });
  });
  document.querySelectorAll('[data-month-chart]').forEach(el => {
    Plotly.newPlot(el, [{ type: 'scatter', mode: 'lines+markers', x: JSON.parse(el.dataset.chartLabels),
      y: JSON.parse(el.dataset.chartValues), line: { color: '#00408b', width: 3 }, marker: { size: 7 },
      hovertemplate: '%{x}: %{y} conducted activities<extra></extra>' }], { ...layout, xaxis: { type: 'category', fixedrange: true } }, config);
  });
  document.querySelectorAll('[data-target-chart]').forEach(el => {
    Plotly.newPlot(el, [{ type: 'bar', x: ['Target', 'Verified actual'], y: JSON.parse(el.dataset.chartValues),
      marker: { color: ['#66758a', '#00408b'] } }], { ...layout, height: 240, yaxis: { title: el.dataset.unit } }, config);
  });
  if (window.ResizeObserver) {
    document.querySelectorAll('[data-campus-chart], [data-month-chart], [data-target-chart]').forEach(el => {
      new ResizeObserver(() => requestAnimationFrame(() => {
        if (el.isConnected && el.data) Plotly.Plots.resize(el);
      })).observe(el);
    });
  }
})();
