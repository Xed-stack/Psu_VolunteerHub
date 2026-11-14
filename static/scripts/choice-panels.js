(() => {
  document.querySelectorAll('[data-choice-panel]').forEach(panel => {
    const inputs = [...panel.querySelectorAll('input[type=checkbox]')];
    const tools = panel.querySelector('[data-choice-tools]');
    const query = panel.querySelector('[data-choice-query]');
    const selected = panel.querySelector('[data-choice-selected]');
    const clear = panel.querySelector('[data-choice-clear]');
    const status = panel.querySelector('[data-choice-results]');
    const filter = () => {
      const term = query.value.trim().toLocaleLowerCase();
      let visible = 0;
      inputs.forEach(input => {
        const show = input.dataset.choiceLabel.toLocaleLowerCase().includes(term);
        input.closest('label').hidden = !show;
        if (show) visible += 1;
      });
      status.textContent = visible ? `${visible} of ${inputs.length} options shown.`
        : term ? `No options match “${query.value.trim()}”. Choose Show All to see every option.` : 'No options are available.';
    };
    const update = () => {
      const checked = inputs.filter(input => input.checked);
      panel.querySelector('[data-choice-count]').textContent = `${checked.length} selected`;
      clear.hidden = checked.length === 0;
      selected.replaceChildren();
      const list = document.createElement('ul'); list.className = 'choice-panel__selected';
      const moreList = document.createElement('ul'); moreList.className = 'choice-panel__selected';
      checked.forEach((input,index) => {
        const li = document.createElement('li');
        const button = document.createElement('button'); button.type = 'button';
        button.className = 'choice-panel__remove';
        const caption = document.createElement('span'); caption.textContent = input.dataset.choiceLabel;
        button.setAttribute('aria-label', `Remove ${input.dataset.choiceLabel}`);
        const mark = document.createElement('span'); mark.textContent = '×'; mark.setAttribute('aria-hidden','true');
        button.append(caption,mark);
        button.addEventListener('click', () => {
          input.checked = false; input.dispatchEvent(new Event('change',{bubbles:true}));
          (selected.querySelector('button') || query).focus();
        });
        li.append(button); (index < 5 ? list : moreList).append(li);
      });
      selected.append(list);
      if (checked.length > 5) {
        const more = document.createElement('details'), summary = document.createElement('summary');
        summary.textContent = `View ${checked.length - 5} More Selected`; more.append(summary,moreList); selected.append(more);
      }
      if (panel.hasAttribute('data-choice-required') && inputs.length) {
        inputs[0].setCustomValidity(checked.length ? '' : 'Select at least one Sustainable Development Goal.');
      }
    };
    panel.querySelector('[data-choice-filter]').addEventListener('click',filter);
    query.addEventListener('keydown',event => { if (event.key === 'Enter') { event.preventDefault(); filter(); } });
    query.addEventListener('search',() => { if (!query.value) filter(); });
    panel.querySelector('[data-choice-reset]').addEventListener('click',() => { query.value = ''; filter(); query.focus(); });
    clear.addEventListener('click',() => {
      const changed = inputs.find(input => input.checked);
      inputs.forEach(input => { input.checked = false; });
      changed?.dispatchEvent(new Event('change',{bubbles:true})); query.focus();
    });
    panel.addEventListener('change',event => { if (inputs.includes(event.target)) update(); });
    panel.addEventListener('invalid',() => { query.value = ''; filter(); },true);
    panel.closest('form')?.addEventListener('draft:restored',update);
    panel.closest('form')?.addEventListener('reset',() => setTimeout(() => { query.value = ''; filter(); update(); },0));
    tools.hidden = false; filter(); update();
  });
})();
