(() => {
  document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click', () => window.print()));
  document.querySelector('[data-form-errors]')?.focus();
  document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', event => {
    if (!confirm(form.dataset.confirm)) event.preventDefault();
  }));
  document.querySelectorAll('input:not([autocomplete]), textarea:not([autocomplete])').forEach(el => {
    if (el.type !== 'password' && el.type !== 'hidden') el.autocomplete = 'off';
  });
  document.querySelectorAll('input[required], select[required], textarea[required]').forEach(input => {
    const label = input.closest('label') || (input.id ? document.querySelector('label[for="' + CSS.escape(input.id) + '"]') : null);
    if (label && !label.textContent.includes('*')) {
      const mark = document.createElement('span'); mark.textContent = ' *'; mark.setAttribute('aria-hidden','true'); label.prepend(mark);
    }
  });
})();
