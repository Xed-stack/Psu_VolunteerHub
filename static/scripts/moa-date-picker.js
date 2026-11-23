(() => {
  const dialog = document.getElementById('moa-date-picker');
  if (!dialog || !window.HTMLDialogElement) return;
  const buttons = [...document.querySelectorAll('[data-moa-picker]')];
  const fields = buttons.map(button => document.getElementById(button.dataset.moaPicker));
  const form = fields[0].form;
  const picker = document.getElementById('moa-picker-date');
  const pickerError = document.getElementById('moa-picker-error');
  const rangeError = document.getElementById('moa-range-error');
  const labels = buttons.map((button, index) => button.dataset.dateLabel || `Valid ${index ? 'Until' : 'From'}`);
  const year = form.elements.namedItem('year');
  const format = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
  let active = 0;
  const refresh = () => {
    fields.forEach((field, index) => {
      const value = field.value;
      buttons[index].setAttribute('aria-label', `${labels[index]} (required): ${value ? format.format(new Date(value + 'T00:00:00Z')) : 'not selected'}`);
      buttons[index].textContent = value ? format.format(new Date(value + 'T00:00:00Z')) : `Select ${labels[index]}${labels[index].endsWith('Date') ? '' : ' Date'}`;
    });
    const reversed = fields[0].value && fields[1].value && fields[1].value < fields[0].value;
    const outsideYear = year?.value && fields.some(field => field.value && field.value.slice(0, 4) !== year.value);
    rangeError.textContent = reversed ? `${labels[1]} must be on or after ${labels[0]}.` : outsideYear ? 'Both dates must be within the AOP year.' : '';
    rangeError.hidden = !reversed && !outsideYear;
  };
  fields.forEach((field, index) => {
    field.hidden = true;
    field.required = false;
    buttons[index].hidden = false;
    document.querySelector(`[data-moa-label="${field.id}"]`).htmlFor = buttons[index].id;
    if (field.hasAttribute('aria-describedby')) {
      buttons[index].setAttribute('aria-describedby', field.getAttribute('aria-describedby'));
      buttons[index].setAttribute('aria-invalid', 'true');
    }
    document.querySelectorAll(`a[href="#${field.id}"]`).forEach(link => { link.href = '#' + buttons[index].id; });
    buttons[index].addEventListener('click', () => {
      active = index;
      document.getElementById('moa-date-heading').textContent = `Choose ${labels[index]}${labels[index].endsWith('Date') ? '' : ' Date'}`;
      picker.value = field.value;
      picker.min = index ? fields[0].value : '';
      picker.max = '';
      if (year?.value && year.checkValidity()) {
        picker.min = picker.min > `${year.value}-01-01` ? picker.min : `${year.value}-01-01`;
        picker.max = `${year.value}-12-31`;
      }
      pickerError.hidden = true;
      dialog.showModal();
    });
    field.addEventListener('input', refresh);
    field.addEventListener('change', refresh);
  });
  dialog.querySelector('[data-moa-cancel]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => buttons[active].focus());
  dialog.querySelector('[data-moa-confirm]').addEventListener('click', () => {
    if (!picker.value || !picker.checkValidity()) {
      pickerError.textContent = active && fields[0].value ? `Choose a date on or after ${labels[0]}.` : 'Choose a valid calendar date.';
      pickerError.hidden = false;
      picker.focus();
      return;
    }
    fields[active].value = picker.value;
    fields[active].dispatchEvent(new Event('input', { bubbles: true }));
    fields[active].dispatchEvent(new Event('change', { bubbles: true }));
    buttons[active].removeAttribute('aria-invalid');
    dialog.close();
  });
  picker.addEventListener('keydown', event => {
    if (event.key === 'Enter') { event.preventDefault(); dialog.querySelector('[data-moa-confirm]').click(); }
  });
  form.addEventListener('draft:restored', refresh);
  year?.addEventListener('input', refresh);
  window.addEventListener('load', refresh);
  form.addEventListener('submit', event => {
    if (event.submitter?.formNoValidate) return;
    const missing = fields.findIndex(field => !field.value);
    refresh();
    if (missing !== -1 || !rangeError.hidden) {
      event.preventDefault();
      if (missing !== -1) { rangeError.textContent = 'Choose both dates.'; rangeError.hidden = false; }
      buttons[missing === -1 ? 1 : missing].focus();
    }
  });
  refresh();
})();
