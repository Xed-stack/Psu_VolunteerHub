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
      y: rows.map(r => r.name), width: .55, marker: { color: '#00408b' }, customdata: rows.map(r => r.id),
      hovertemplate: '%{y}: %{x} conducted activities<extra></extra>' }], { ...structuredClone(layout), height:Math.max(180,Math.min(420,rows.length*26+80)) }, config);
    el.on('plotly_click', event => {
      const url = new URL(document.body.dataset.tourRole === 'director' ? '/workspace/campuses/' + event.points[0].customdata : '/workspace/reports/results', location.origin);
      url.search = location.search;
      if (document.body.dataset.tourRole === 'director' && !location.pathname.startsWith('/workspace/campuses/')) url.searchParams.set('return_to',location.pathname + location.search);
      url.searchParams.set('campus_id', event.points[0].customdata);
      url.searchParams.set('delivery', 'conducted');
      url.searchParams.delete('page');
      location.assign(url);
    });
  });
  document.querySelectorAll('[data-month-chart]').forEach(el => {
    const labels = JSON.parse(el.dataset.chartLabels);
    const singleYear = new Set(labels.filter(label=>label.includes(' ')).map(label=>label.split(' ').at(-1))).size === 1;
    const ticks = labels.filter((_,index)=>innerWidth > 500 || labels.length <= 8 || index % 2 === 0);
    Plotly.newPlot(el, [{ type: 'scatter', mode: 'lines+markers', x: JSON.parse(el.dataset.chartLabels),
      y: JSON.parse(el.dataset.chartValues), line: { color: '#00408b', width: 3 }, marker: { size: 7 },
      hovertemplate: '%{x}: %{y} conducted activities<extra></extra>' }], { ...structuredClone(layout), margin:{...layout.margin,b:50}, yaxis:{...layout.yaxis,rangemode:'tozero',autorange:true}, xaxis: { type:'category',fixedrange:true,automargin:true,tickmode:'array',tickvals:ticks,ticktext:ticks.map(label=>singleYear ? label.split(' ')[0] : label),tickangle:0 } }, config);
  });
  document.querySelectorAll('[data-target-chart]').forEach(el => {
    Plotly.newPlot(el, [{ type: 'bar', x: ['Target', 'Verified actual'], y: JSON.parse(el.dataset.chartValues),
      marker: { color: ['#66758a', '#00408b'] } }], { ...structuredClone(layout), height: 240, yaxis: { title: el.dataset.unit } }, config);
  });
  document.querySelectorAll('[data-target-group]').forEach(el => {
    const rows = JSON.parse(el.dataset.chartValues);
    Plotly.newPlot(el, [
      {type:'bar',orientation:'h',name:'Target',y:rows.map((_,i)=>i),x:rows.map(r=>r.target),customdata:rows.map(r=>r.name),hovertemplate:'%{customdata}: %{x}<extra>Target</extra>',marker:{color:'#66758a'}},
      {type:'bar',orientation:'h',name:'Verified actual',y:rows.map((_,i)=>i),x:rows.map(r=>r.actual),customdata:rows.map(r=>r.name),hovertemplate:'%{customdata}: %{x}<extra>Verified actual</extra>',marker:{color:'#00408b'}}
    ], {...structuredClone(layout),showlegend:true,barmode:'group',height:Math.max(260,rows.length*65+100),
      legend:{orientation:'h',y:1.15},xaxis:{...layout.xaxis,title:el.dataset.unit},
      yaxis:{...layout.yaxis,autorange:'reversed',tickmode:'array',tickvals:rows.map((_,i)=>i),ticktext:rows.map(r=>r.name)}},config);
  });
  document.querySelectorAll('[data-historical-chart]').forEach(el => {
    const rows = JSON.parse(el.dataset.chartValues);
    Plotly.newPlot(el,[{type:'bar',orientation:'h',y:rows.map(r=>r.name),x:rows.map(r=>r.count),marker:{color:'#00408b'},
      hovertemplate:'%{y}: %{x} known reported participations<extra></extra>'}],structuredClone(layout),config);
  });
  if (window.ResizeObserver) {
    document.querySelectorAll('[data-campus-chart], [data-month-chart], [data-target-chart], [data-target-group], [data-historical-chart]').forEach(el => {
      new ResizeObserver(() => requestAnimationFrame(() => {
        if (el.isConnected && el.data) Plotly.Plots.resize(el);
      })).observe(el);
    });
  }
})();
