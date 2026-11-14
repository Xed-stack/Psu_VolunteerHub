(() => {
  document.querySelectorAll('[data-print]').forEach(button => button.addEventListener('click', () => window.print()));
  document.querySelector('[data-form-errors]')?.focus();
  document.querySelectorAll('input:not([autocomplete]), textarea:not([autocomplete])').forEach(el => {
    if (el.type !== 'password' && el.type !== 'hidden') el.autocomplete = 'off';
  });
  document.querySelectorAll('input[required], select[required], textarea[required]').forEach(input => {
    const label = input.closest('label') || (input.id ? document.querySelector('label[for="' + CSS.escape(input.id) + '"]') : null);
    if (label && !label.textContent.includes('*')) {
      const mark = document.createElement('span'); mark.textContent = ' *'; mark.setAttribute('aria-hidden','true'); label.prepend(mark);
    }
  });
  document.querySelectorAll('form').forEach(form => {
    const clearError = input => {
      if (!input.dataset.inlineError || !input.validity.valid) return;
      document.getElementById(input.dataset.inlineError)?.remove();
      input.removeAttribute('aria-invalid');
      const description = (input.getAttribute('aria-describedby') || '').split(' ').filter(id => id !== input.dataset.inlineError);
      if (description.length) input.setAttribute('aria-describedby', description.join(' '));
      else input.removeAttribute('aria-describedby');
      delete input.dataset.inlineError;
      const summary = form.previousElementSibling;
      if (summary?.matches('[data-validation-summary]')) {
        summary.querySelector(`[data-validation-for="${CSS.escape(input.id)}"]`)?.remove();
        if (!summary.querySelector('li')) summary.remove();
      }
    };
    form.addEventListener('invalid', event => {
      for (let parent = event.target.parentElement; parent; parent = parent.parentElement) {
        if (parent.tagName === 'DETAILS') parent.open = true;
      }
      let summary = form.previousElementSibling;
      if (!summary?.matches('[data-validation-summary]')) {
        summary = document.createElement('section');
        summary.className = 'auth-errors mb-5';
        summary.dataset.validationSummary = '';
        summary.setAttribute('role', 'alert');
        form.before(summary);
      }
      summary.replaceChildren();
      const title = document.createElement('h2'); title.textContent = 'Review These Details';
      const list = document.createElement('ul'); summary.append(title, list);
      [...form.querySelectorAll(':invalid')].filter(input => input.willValidate).forEach((input,index) => {
        input.dataset.fieldLabel ||= input.labels?.[0]?.textContent.trim() || 'Field';
        if (!input.id) input.id = `invalid-${input.name || 'field'}-${index}`;
        const errorId = input.id + '-validation';
        let message = document.getElementById(errorId);
        if (!message) {
          message = document.createElement('p'); message.id = errorId; message.className = 'field-error';
          const field = input.closest('.field, [data-choice-panel]');
          if (field) field.append(message); else input.after(message);
        }
        message.textContent = input.validationMessage;
        input.setAttribute('aria-invalid','true');
        const descriptions = new Set((input.getAttribute('aria-describedby') || '').split(' ').filter(Boolean));
        descriptions.add(errorId); input.setAttribute('aria-describedby',[...descriptions].join(' '));
        input.dataset.inlineError = errorId;
        const item = document.createElement('li'), link = document.createElement('a');
        link.href = '#' + input.id;
        link.textContent = `${input.dataset.fieldLabel}: ${input.validationMessage}`;
        item.dataset.validationFor = input.id;
        item.append(link); list.append(item);
      });
    }, true);
    form.addEventListener('input', event => clearError(event.target));
    form.addEventListener('change', event => clearError(event.target));
  });
  document.querySelectorAll('[data-period-controls]').forEach(form => {
    const period = form.elements.period, segment = form.elements.segment;
    if (!period || !segment) return;
    const labels = ['First', 'Second', 'Third', 'Fourth'];
    form.querySelectorAll('[data-period-inactive]').forEach(field => field.removeAttribute('data-period-inactive'));
    const update = () => {
      const half = period.value === 'semiannual';
      const maximum = period.value === 'quarterly' ? 4 : half ? 2 : 1;
      if (+segment.value > maximum) segment.value = '1';
      [...segment.options].forEach((option, index) => {
        option.hidden = +option.value > maximum;
        option.textContent = `${labels[index]} ${half ? 'Half' : 'Quarter'}`;
      });
      form.querySelector('[data-period-segment]').hidden = maximum === 1;
      form.querySelector('[data-segment-label]').textContent = half ? 'Half-Year' : 'Quarter';
      form.querySelectorAll('[data-period-date]').forEach(field => {
        field.hidden = period.value !== 'custom';
        field.querySelector('input').required = period.value === 'custom';
      });
    };
    period.addEventListener('change', update);
    form.addEventListener('submit', () => {
      if (period.value !== 'custom') ['start_date', 'end_date'].forEach(name => { form.elements[name].value = ''; });
    });
    update();
  });
  const tips = [...document.querySelectorAll('.info-tip')];
  const placeTip = tip => {
    if (!tip.open) return;
    const content = tip.querySelector('.info-tip__content');
    const rect = tip.querySelector('summary').getBoundingClientRect();
    content.style.position = 'fixed';
    content.style.maxHeight = `${Math.max(80, window.innerHeight - 32)}px`;
    content.style.overflowY = 'auto';
    content.style.left = `${Math.max(16, Math.min(rect.left, window.innerWidth - content.offsetWidth - 16))}px`;
    content.style.top = `${Math.max(16, Math.min(rect.bottom + 6, window.innerHeight - content.offsetHeight - 16))}px`;
  };
  tips.forEach(tip => tip.addEventListener('toggle', () => {
    if (!tip.open) return;
    tips.forEach(other => { if (other !== tip) other.open = false; });
    placeTip(tip);
  }));
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    tips.filter(tip => tip.open).forEach(tip => { tip.open = false; tip.querySelector('summary').focus(); });
  });
  document.addEventListener('click', event => tips.forEach(tip => {
    if (tip.open && !tip.contains(event.target)) tip.open = false;
  }));
  window.addEventListener('resize', () => tips.forEach(placeTip));
  window.addEventListener('scroll', () => tips.forEach(placeTip), true);
})();
