(() => {
  const form = document.querySelector('[data-proposal-form], [data-activity-stage]');
  if (!form) return;
  document.querySelectorAll('[data-proposal-exit]').forEach(link => link.addEventListener('click', event => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    const button = document.createElement('button');
    button.type = 'submit'; button.name = 'save_step'; button.value = link.dataset.proposalExit;
    button.formNoValidate = Number(button.value) <= Number(form.dataset.step || form.dataset.activityStage);
    button.hidden = true; form.append(button); form.requestSubmit(button);
  }));
  if (!form.hasAttribute('data-proposal-form')) return;
  form.querySelectorAll('[data-control-error]').forEach(error => {
    const field = form.querySelector(`[name="${CSS.escape(error.dataset.controlError)}"]`);
    if (!field) return;
    field.setAttribute('aria-invalid', 'true');
    field.setAttribute('aria-describedby', `${field.getAttribute('aria-describedby') || ''} ${error.id}`.trim());
    field.closest('label')?.append(error);
  });
  const sectionIndex = form.querySelector('.proposal-index details');
  if (sectionIndex) sectionIndex.open = window.matchMedia('(min-width: 1024px)').matches;
  const reveal = target => {
    const section = target?.closest('details');
    if (section) section.open = true;
  };
  form.addEventListener('invalid', event => reveal(event.target), true);
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (link) reveal(document.getElementById(link.hash.slice(1)));
  });
  if (location.hash) reveal(document.getElementById(location.hash.slice(1)));
  const hidden = form.querySelector('[name="proposal_record"]');
  const read = () => { try { return JSON.parse(hidden.value || '{}'); } catch { return {}; } };
  const notify = () => hidden.dispatchEvent(new Event('input', { bubbles: true }));
  const collect = () => {
    const record = read();
    form.querySelectorAll('[data-record-field]').forEach(el => { record[el.dataset.recordField] = el.value; });
    form.querySelectorAll('[name^="pr.present."]').forEach(el => {
      const key = el.name.slice('pr.present.'.length);
      const rows = form.querySelector(`[data-proposal-rows="${CSS.escape(key)}"]`);
      if (rows) record[key] = [...rows.querySelectorAll('.proposal-row')].map(row =>
        Object.fromEntries([...row.querySelectorAll('[data-record-row]')].map(input => [input.dataset.recordRow, input.value])));
      else record[key] = [...form.querySelectorAll(`[name="pr.${CSS.escape(key)}"]:checked`)].map(input => input.value);
    });
    if (record.additional_agency_ids) record.additional_agency_ids = record.additional_agency_ids.filter(id => id !== record.agency_id);
    hidden.value = JSON.stringify(record);
    const conditional = {
      budget_reason: record.budget_na === 'yes', budget: record.budget_na !== 'yes',
      partnership_reason: record.partnership_status === 'none',
      beneficiary_other: (record.beneficiary_groups || []).includes('Other Stakeholders'),
      volunteer_other: (record.volunteer_groups || []).includes('Other Stakeholders')
    };
    for (const key of ['agency_id','psu_roles','partner_roles','partnership_duration']) conditional[key] = record.partnership_status !== 'none';
    const partnerDetails = form.querySelector('[data-partner-details]');
    if (partnerDetails) {
      const hasPartner = ['existing', 'renewal', 'new'].includes(record.partnership_status);
      partnerDetails.hidden = !hasPartner;
      partnerDetails.querySelectorAll('input,select,button').forEach(control => { control.disabled = !hasPartner; });
      const agency = partnerDetails.querySelector('[name="pr.agency_id"]');
      if (agency) agency.required = hasPartner;
      const agreement = partnerDetails.querySelector('[name="agreement_id"]');
      if (agreement) agreement.required = record.partnership_status === 'existing';
      conditional.agency_id = hasPartner;
      conditional.agreement_id = record.partnership_status === 'existing';
      const additional = partnerDetails.querySelector('[data-choice-panel]');
      additional?.querySelectorAll('input[type=checkbox]').forEach(input => {
        const primary = input.value === record.agency_id;
        input.dataset.choiceExcluded = String(primary);
        input.disabled = !hasPartner || primary;
        if (primary) input.checked = false;
      });
      additional?.dispatchEvent(new Event('choice:refresh'));
    }
    form.querySelectorAll('[data-required-marker]').forEach(marker => {
      const required = conditional[marker.dataset.requiredMarker];
      if (required === undefined) return;
      marker.textContent = required ? ' *' : ' (Optional)';
      marker.closest('label')?.querySelector('input,select,textarea')?.setAttribute('aria-required', String(required));
    });
    const total = form.querySelector('[data-budget-total]');
    if (total) {
      const scaled = (value, places) => {
        if (!new RegExp(`^(?:[0-9]+(?:\\.[0-9]{0,${places}})?|\\.[0-9]{1,${places}})$`).test(value)) return null;
        const [whole, fraction = ''] = value.split('.');
        return BigInt(whole || '0') * (10n ** BigInt(places)) + BigInt(fraction.padEnd(places, '0'));
      };
      let cents = 0n, valid = true;
      (record.budget || []).filter(row => Object.values(row).some(Boolean)).forEach(row => {
        const quantity = scaled(row.quantity, 3), cost = scaled(row.unit_cost, 2);
        if (quantity === null || cost === null || quantity <= 0n) valid = false;
        else cents += (quantity * cost + 500n) / 1000n;
      });
      total.textContent = valid ? `PHP ${new Intl.NumberFormat('en-PH').format(cents / 100n)}.${String(cents % 100n).padStart(2, '0')}` : 'Check budget entries';
    }
  };
  const renumber = container => container.querySelectorAll('.proposal-row').forEach((row, index) => {
    row.querySelector('[data-row-number]').textContent = String(index + 1);
    row.querySelector('[data-remove-proposal-row]').value = `remove:${container.dataset.proposalRows}:${index}`;
    row.querySelector('[data-remove-proposal-row]').setAttribute('aria-label', `Remove Row ${index + 1} From ${container.dataset.proposalRows}`);
  });
  const restore = () => {
    const record = read();
    form.querySelectorAll('[data-record-field]').forEach(el => { el.value = record[el.dataset.recordField] || ''; });
    form.querySelectorAll('[name^="pr."][type="checkbox"]').forEach(el => { el.checked = (record[el.name.slice(3)] || []).includes(el.value); });
    form.querySelectorAll('[data-proposal-rows]').forEach(container => {
      const values = record[container.dataset.proposalRows] || [];
      const prototype = container.querySelector('.proposal-row').cloneNode(true);
      container.replaceChildren();
      (values.length ? values : [{}]).forEach(value => {
        const row = prototype.cloneNode(true);
        row.querySelectorAll('[data-record-row]').forEach(input => { input.value = value[input.dataset.recordRow] || ''; });
        container.append(row);
      });
      renumber(container);
    });
    collect();
  };
  form.addEventListener('draft:restored', restore);
  form.addEventListener('input', event => {
    if (event.target === hidden) return;
    if (event.target.name?.startsWith('pr.')) { collect(); notify(); }
  });
  form.addEventListener('change', event => {
    if (event.target.name?.startsWith('pr.')) { collect(); notify(); }
    if (event.target.name === 'proposal') {
      const status = form.querySelector('[data-proposal-upload-status]');
      if (status) status.textContent = event.target.files.length ? 'Ready to capture. Choose Capture Proposal and Continue.' : 'Choose a completed proposal to capture its information.';
    }
  });
  form.addEventListener('submit', event => {
    collect();
    const button = event.submitter;
    if (button?.hasAttribute('data-add-proposal-row')) {
      event.preventDefault();
      const container = form.querySelector(`[data-proposal-rows="${CSS.escape(button.dataset.addProposalRow)}"]`);
      if (container.children.length >= 50) return;
      const row = container.firstElementChild.cloneNode(true);
      row.querySelectorAll('input,select').forEach(input => { input.value = ''; });
      container.append(row); renumber(container); collect(); notify(); row.querySelector('input,select')?.focus();
    } else if (button?.hasAttribute('data-remove-proposal-row')) {
      event.preventDefault();
      const row = button.closest('.proposal-row'), container = row.parentElement;
      if (container.children.length > 1) row.remove();
      else row.querySelectorAll('input,select').forEach(input => { input.value = ''; });
      renumber(container); collect(); notify(); container.querySelector('input,select')?.focus();
    } else if (button && !button.formNoValidate && form.querySelector('[name="proposal"]')?.files.length) {
      const status = form.querySelector('[data-proposal-upload-status]');
      if (status) status.textContent = 'Capturing proposal…';
    }
  });
  collect();
})();
