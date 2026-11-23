(() => {
  const error = document.querySelector('.goal-form-error');
  if (error) {
    error.tabIndex = -1;
    error.focus();
  }
  let changed = false;
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
