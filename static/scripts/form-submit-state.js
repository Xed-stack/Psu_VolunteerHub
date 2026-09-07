(() => {
  const trackedButtons = new Set();

  const restoreButtons = () => {
    trackedButtons.forEach((button) => {
      button.disabled = false;
      button.classList.remove('is-submitting');
      button.removeAttribute('aria-busy');
      if (button.dataset.originalLabel) {
        button.innerHTML = button.dataset.originalLabel;
        delete button.dataset.originalLabel;
      }
      button.form?.removeAttribute('aria-busy');
    });
    trackedButtons.clear();
  };

  document.addEventListener('submit', (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.dataset.noSubmitState !== undefined) {
      return;
    }

    const button = event.submitter;
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }

    button.dataset.originalLabel = button.innerHTML;
    button.disabled = true;
    button.classList.add('is-submitting');
    button.setAttribute('aria-busy', 'true');
    button.innerHTML = '<span class="submit-spinner" aria-hidden="true"></span><span>Working…</span>';
    form.setAttribute('aria-busy', 'true');
    trackedButtons.add(button);
  });

  window.addEventListener('pageshow', restoreButtons);
})();
