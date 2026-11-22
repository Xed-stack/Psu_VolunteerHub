(() => {
  if (!window.Plotly) return;
  const layout = { font: { family: 'Inter, sans-serif', color: '#111c2c', size: 13 },
    margin: { t: 24, r: 16, b: 42, l: 90 }, paper_bgcolor: '#fff', plot_bgcolor: '#fff',
    height: 300, showlegend: false, xaxis: { rangemode: 'tozero', fixedrange: true },
    yaxis: { fixedrange: true, automargin: true } };
  const config = { responsive: true, displayModeBar: false, staticPlot: false };
  const numbers = new Intl.NumberFormat(document.documentElement.lang || 'en');
  const responsiveLayouts = new WeakMap();
  const escape = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const wrap = (value, limit) => {
    const lines = [''];
    String(value).split(/\s+/).forEach(word => {
      const chunks = word.match(new RegExp(`.{1,${limit}}`, 'gu')) || [''];
      chunks.forEach(chunk => {
        if ((lines.at(-1) + ' ' + chunk).trim().length > limit) lines.push(chunk);
        else lines[lines.length - 1] = (lines.at(-1) + ' ' + chunk).trim();
      });
    });
    return lines.map(escape).join('<br>');
  };
  const countAxis = values => ({rangemode:'tozero',fixedrange:true,tickformat:',d',
    ...(Math.max(0,...values) < 10 ? {dtick:Math.max(1,Math.ceil(Math.max(0,...values)/4))} : {nticks:5})});
  const draw = (el, traces, settings) => {
    el.hidden = false;
    return Plotly.newPlot(el, traces, {...settings, transition:{duration:0}}, config).then(() => {
      const status = el.parentElement.querySelector('[data-chart-status]');
      if (status) status.hidden = true;
    }).catch(() => { el.hidden = true; });
  };
  const horizontal = (el, rows) => {
    const values = rows.map(row => row.count);
    const sizing = () => {
      const narrow = el.parentElement.clientWidth < 400;
      const labels = rows.map(row => wrap(row.name, narrow ? 13 : 20));
      let height = 0;
      const positions = labels.map(label => {
        const rowHeight = Math.max(40,label.split('<br>').length*17+12);
        const center = height + rowHeight/2; height += rowHeight; return center;
      });
      return {width:el.parentElement.clientWidth,height:Math.max(230,height+76),
        margin:{t:16,r:45,b:50,l:narrow ? 112 : 155},
        'yaxis.ticktext':labels,'yaxis.tickvals':positions,'yaxis.range':[height,0]};
    };
    responsiveLayouts.set(el, sizing);
    const size = sizing();
    draw(el, [{type:'bar',orientation:'h',x:values,y:size['yaxis.tickvals'],width:20,
      marker:{color:'#00408b'},text:rows.map(row => numbers.format(row.count)),
      textposition:'outside',cliponaxis:false,
      customdata:rows.map(row => row.id),
      hovertemplate:'%{text} conducted activities<extra></extra>'
    }], {...structuredClone(layout),width:size.width,height:size.height,margin:size.margin,
      xaxis:{...countAxis(values),title:{text:'Conducted Activities',font:{size:12}},range:[0,Math.max(1,...values)*1.15]},
      yaxis:{fixedrange:true,autorange:false,range:size['yaxis.range'],tickmode:'array',tickvals:size['yaxis.tickvals'],ticktext:size['yaxis.ticktext'],automargin:true,ticks:'outside',ticklen:6,tickcolor:'#fff'}
    });
  };
  document.querySelectorAll('[data-campus-chart]').forEach(el => {
    const rows = JSON.parse(el.dataset.chartValues);
    horizontal(el, rows);
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
  document.querySelectorAll('[data-sex-chart]').forEach(el => {
    const rows = JSON.parse(el.dataset.chartValues);
    const total = rows.reduce((sum,row) => sum + row.total,0);
    const sizing = () => ({width:el.parentElement.clientWidth,height:Math.min(340,Math.max(240,el.parentElement.clientWidth)),
      'annotations[0].font.size':Math.min(30,Math.max(16,el.parentElement.clientWidth/11))});
    responsiveLayouts.set(el,sizing);
    const size = sizing();
    draw(el,[{type:'pie',hole:.62,sort:false,direction:'clockwise',
      labels:rows.map(row=>row.label),values:rows.map(row=>row.total),
      text:rows.map(row=>row.share === null ? '' : row.share.toFixed(1) + '%'),
      marker:{colors:['#00408b','#f4bd27','#475569','#cbd5e1'],line:{color:'#111c2c',width:1.5}},
      texttemplate:'%{text}',textposition:'inside',insidetextorientation:'horizontal',
      textfont:{size:14,color:['#ffffff','#111c2c','#ffffff','#111c2c']},
      hovertemplate:'%{label}: %{value:,d} (%{text})<extra></extra>'
    }],{font:layout.font,paper_bgcolor:'#fff',showlegend:false,width:size.width,height:size.height,
      margin:{t:16,r:16,b:16,l:16},uniformtext:{minsize:12,mode:'hide'},
      annotations:[{text:numbers.format(total),showarrow:false,x:.5,y:.5,xref:'paper',yref:'paper',
        font:{color:'#00408b',size:size['annotations[0].font.size']}}]});
  });
  document.querySelectorAll('[data-month-chart]').forEach(el => {
    const labels = JSON.parse(el.dataset.chartLabels);
    const singleYear = new Set(labels.filter(label=>label.includes(' ')).map(label=>label.split(' ').at(-1))).size === 1;
    const sizing = () => {
      const stride = Math.max(1, Math.ceil(labels.length / (el.parentElement.clientWidth < 400 ? 4 : 8)));
      const ticks = labels.filter((_,index)=>index % stride === 0 || index === labels.length - 1);
      return {width:el.parentElement.clientWidth,'xaxis.tickvals':ticks,'xaxis.ticktext':ticks.map(label=>singleYear ? label.split(' ')[0] : label)};
    };
    responsiveLayouts.set(el, sizing);
    const size = sizing();
    const values = JSON.parse(el.dataset.chartValues);
    draw(el, [{ type: 'scatter', mode: 'lines+markers', x: labels,
      y: JSON.parse(el.dataset.chartValues), line: { color: '#00408b', width: 3 }, marker: { size: 7 },
      hovertemplate: '%{x}: %{y:,d} conducted activities<extra></extra>' }], { ...structuredClone(layout),width:size.width, margin:{t:24,r:16,b:55,l:40}, yaxis:{...countAxis(values),autorange:true}, xaxis: { type:'category',fixedrange:true,automargin:true,tickmode:'array',tickvals:size['xaxis.tickvals'],ticktext:size['xaxis.ticktext'],tickangle:0 } });
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
    document.querySelectorAll('[data-campus-chart], [data-sex-chart], [data-month-chart], [data-target-chart], [data-target-group], [data-historical-chart]').forEach(el => {
      let previousWidth = 0;
      new ResizeObserver(() => requestAnimationFrame(() => {
        if (el.isConnected && el.data && el.clientWidth && el.clientWidth !== previousWidth) {
          previousWidth = el.clientWidth;
          const sizing = responsiveLayouts.get(el);
          if (sizing) {
            const settings = sizing();
            Plotly.update(el, settings['yaxis.tickvals'] ? {y:[settings['yaxis.tickvals']]} : {}, settings);
          }
          Plotly.Plots.resize(el);
        }
      })).observe(el);
    });
  }
})();
