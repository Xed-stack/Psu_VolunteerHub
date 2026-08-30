(() => {
  const colors = ['#00408b', '#f6bf22', '#2f8f5b', '#8b5cf6', '#e66b2e', '#3b82f6', '#ba1a1a'];
  const baseLayout = {
    autosize: true,
    margin: { t: 16, r: 16, b: 48, l: 48 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'Inter, system-ui, sans-serif', color: '#111c2c' },
    legend: { orientation: 'h', y: -0.2 },
  };
  const config = { responsive: true, displayModeBar: false };

  const readData = (id) => {
    const source = document.getElementById(id);
    if (!source) return null;
    try { return JSON.parse(source.textContent); } catch (_) { return null; }
  };

  const render = (node, type, data) => {
    if (!window.Plotly || !data) return;
    let traces = [];
    let layout = { ...baseLayout };
    if (type === 'pie' || type === 'donut') {
      traces = [{ type: 'pie', labels: data.labels, values: data.values,
        hole: type === 'donut' ? 0.58 : 0, marker: { colors }, textinfo: 'label+percent' }];
      layout = { ...layout, margin: { t: 8, r: 8, b: 48, l: 8 } };
    } else if (type === 'bar') {
      traces = [{ type: 'bar', x: data.labels, y: data.values,
        marker: { color: colors[0] }, name: data.name || 'Participation' }];
      layout = { ...layout, yaxis: { rangemode: 'tozero', gridcolor: '#e5e7eb' } };
    } else {
      traces = [
        { type: 'scatter', mode: 'lines+markers', x: data.labels,
          y: data.primary, name: data.primaryName || 'Registrations', line: { color: colors[0] } },
        { type: 'scatter', mode: 'lines+markers', x: data.labels,
          y: data.secondary, name: data.secondaryName || 'Attended', line: { color: colors[1] } },
      ];
      layout = { ...layout, yaxis: { rangemode: 'tozero', gridcolor: '#e5e7eb' } };
    }
    if (!data.values?.some(Number) && !data.primary?.some(Number)) {
      node.innerHTML = '<div class="empty-state">No chart data available.</div>';
      return;
    }
    window.Plotly.react(node, traces, layout, config);
  };

  document.querySelectorAll('[data-chart]').forEach((node) => {
    render(node, node.dataset.chart, readData(node.dataset.source));
  });
  document.querySelectorAll('[data-chart-switch]').forEach((select) => {
    const target = document.getElementById(select.dataset.chartSwitch);
    const datasets = readData(select.dataset.source);
    const update = () => render(target, 'line', datasets?.[select.value]);
    select.addEventListener('change', update);
    update();
  });
})();
