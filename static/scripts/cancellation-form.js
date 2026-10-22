(() => {
  const form = document.querySelector('[data-cancellation-form]');
  if (!form) return;
  const details = form.querySelector('[name="details"]');
  const updateRequired = () => {
    details.required = form.querySelector('[name="reason"]:checked')?.value === 'Other';
  };
  form.addEventListener('change', updateRequired);
  updateRequired();
  form.querySelector('[aria-invalid="true"]')?.focus();
})();
