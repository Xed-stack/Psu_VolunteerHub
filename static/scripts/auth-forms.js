(() => {
  document.querySelectorAll('[data-toggle-password]').forEach((button) => {
    const input = document.getElementById(button.dataset.togglePassword);
    if (!input) return;
    const label = button.getAttribute('aria-label').replace(/^Show /, '');
    button.hidden = false;
    button.addEventListener('click', () => {
      const showing = input.type === 'password';
      input.type = showing ? 'text' : 'password';
      button.textContent = showing ? 'Hide' : 'Show';
      button.setAttribute('aria-label', `${showing ? 'Hide' : 'Show'} ${label}`);
      button.setAttribute('aria-pressed', String(showing));
    });
  });

  const invalidField = document.querySelector('input[aria-invalid="true"], select[aria-invalid="true"]');
  const summary = document.querySelector('[data-error-summary]');
  (invalidField || summary)?.focus();

  const dialog = document.querySelector('dialog[data-auto-open]');
  if (dialog) {
    dialog.showModal();
    dialog.addEventListener('close', () => document.getElementById('identifier')?.focus());
  }

  const form = document.querySelector('form[data-warn-unsaved]');
  if (form) {
    let dirty = form.dataset.warnUnsaved === 'true';
    let submitting = false;
    form.addEventListener('input', () => { dirty = true; });
    form.addEventListener('change', () => { dirty = true; });
    document.addEventListener('submit', (event) => {
      // The shared document-level submit guard was registered first.
      if (event.target === form && !event.defaultPrevented) submitting = true;
    });
    window.addEventListener('beforeunload', (event) => {
      if (dirty && !submitting) {
        event.preventDefault();
        event.returnValue = '';
      }
    });
    window.addEventListener('pageshow', () => { submitting = false; });
  }
})();
