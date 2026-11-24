(() => {
  const error = document.querySelector('.goal-form-error');
  if (error) {
    error.tabIndex = -1;
    error.focus();
  }
  let changed = false;
  const create = document.querySelector('.aop-create');
  if (create) {
    const form = create.querySelector('form.goal-form');
    const refresh = () => {
      create.querySelectorAll('[data-goal-count]').forEach(counter => {
        const field = form.elements.namedItem(counter.dataset.goalCount);
        counter.textContent = `${field.value.length} / ${field.maxLength}`;
      });
      const year = form.elements.namedItem('year').value;
      create.querySelector('[data-goal-year]').textContent = year || 'selected above';
      create.querySelector('.aop-calendar-coverage').hidden = !year ||
        form.elements.namedItem('start_date').value !== `${year}-01-01` ||
        form.elements.namedItem('end_date').value !== `${year}-12-31`;
    };
    form.addEventListener('input', refresh);
    refresh();
  }
  document.querySelectorAll('form.goal-form').forEach((form) => {
    form.addEventListener('input', (event) => { if (event.target.name) changed = true; });
    form.addEventListener('submit', (event) => {
      queueMicrotask(() => { if (!event.defaultPrevented) changed = false; });
    });
  });
  window.addEventListener('beforeunload', (event) => {
    if (!changed) return;
    event.preventDefault();
    event.returnValue = '';
  });
})();
