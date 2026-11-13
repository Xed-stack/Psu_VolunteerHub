(() => {
  if (document.body.hasAttribute("data-clear-signup-draft")) {
    try { sessionStorage.removeItem("psu:signup"); } catch {}
  }
  const csrf = () => document.querySelector('meta[name="csrf-token"]')?.content || document.querySelector('input[name="csrf_token"]')?.value;
  const endpoint = key => '/workspace/drafts/' + encodeURIComponent(key);
  const request = async (key, method, payload) => {
    const response = await fetch(endpoint(key), { method, credentials: 'same-origin', redirect: 'error',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() || '' },
      body: payload ? JSON.stringify(payload) : undefined });
    if (!response.ok) throw new Error('Draft unavailable');
    return response.status === 204 ? {} : response.json();
  };
  document.querySelectorAll('[data-discard-draft]').forEach(button => button.addEventListener('click', async () => {
    if (!confirm('Discard this saved draft?')) return;
    try { await request(button.dataset.discardDraft, 'DELETE'); location.reload(); }
    catch { button.textContent = 'Could not discard. Try again.'; }
  }));
  const safeNames = new Set(['first_name','last_name','interests','skills','title','description','date','end_date','location','category','slots','cancellation_days',
    'required_skills','sdg_ids','target_participants','participation_agreement_text','conducting_department','participant_type',
    'departments','volunteer_ids','agreement_id','name','full_name','email','phone','contact_name','campus','campus_id',
    'college_affiliation','volunteer_type','sex','id_number','interest_ids','skill_ids','reference','valid_from','valid_until',
    'notes','program','indicator','definition','unit','target_value','deadline','evidence_basis','source_document',
    'coverage_note','actual_value','year','plan_type','first_name','last_name','skills','interests','responsible_office','comparison_rule','coverage_start','coverage_end','note','code','unit','program','college_affiliation_add','college_affiliation_remove','default_password_length','max_slots_per_event','nda_text','nda_version','nda_required','participation_agreement_version','message','announcement_type']);
  document.querySelectorAll('form[method="post"], form[method="POST"]').forEach((form, index) => {
    if (form.dataset.noDraft !== undefined ||
        /cancel|delete|withdraw|logout|\/auth\/|consent|accept|attendance|import|change-password/.test(form.action)) return;
    const controls = [...form.elements].filter(el => safeNames.has(el.name) && !['password','hidden','file'].includes(el.type));
    const uploads = [...form.elements].filter(el => el.type === 'file' && ['document','file','profile_image','cover_image','evidence_file'].includes(el.name));
    if (!controls.length && !uploads.length) return;
    const source = new URL(location.href);
    source.searchParams.delete('draft_form');
    if (index) source.searchParams.set('draft_form', String(index));
    const key = form.dataset.draftKey || 'form:' + source.pathname + source.search;
    const status = document.createElement('div');
    status.className = 'draft-status';
    const text = document.createElement('span');
    text.setAttribute('role','status'); text.setAttribute('aria-live','polite'); text.textContent = 'Checking saved draft…';
    const discard = document.createElement('button'); discard.type = 'button'; discard.className = 'underline font-semibold text-psu'; discard.textContent = 'Discard draft';
    status.append(text, discard); form.prepend(status);
    const hidden = document.createElement('input'); hidden.type = 'hidden'; hidden.name = '_draft_key'; hidden.value = key; form.append(hidden);
    let dirty = false, timer, ready = false, revision = 0, saving = Promise.resolve();
    const uploadTasks = new Set();
    let submitting = false, preparing = false;
    const collect = () => {
      const data = {};
      controls.forEach(el => {
        data[el.name] ||= [];
        if (['checkbox','radio'].includes(el.type) && !el.checked) return;
        if (el.multiple) data[el.name].push(...[...el.selectedOptions].map(o => o.value));
        else data[el.name].push(el.value);
      });
      return data;
    };
    const save = () => {
      const current = revision; const payload = collect(); text.textContent = 'Saving…';
      saving = saving.catch(() => {}).then(() => request(key, 'PUT', payload)).then(() => {
        if (revision === current) { dirty = false; text.textContent = 'Draft saved'; form.dispatchEvent(new Event('draft:saved')); }
      }).catch(() => { text.textContent = 'Draft could not be saved. Keep this page open and try again.'; dirty = true; });
      return saving;
    };
    const hasErrors = document.querySelector('[data-form-errors], .flash--error, .field-error, .auth-error');
    request(key, 'GET').then(result => {
      if (!dirty && !hasErrors) {
        controls.forEach(el => {
          const values = result.payload[el.name];
          if (!Array.isArray(values)) return;
          if (['checkbox','radio'].includes(el.type)) el.checked = values.includes(el.value);
          else if (el.multiple) [...el.options].forEach(o => { o.selected = values.includes(o.value); });
          else el.value = values[0] || '';
        });
        form.dispatchEvent(new CustomEvent('draft:restored'));
      }
      text.textContent = result.updated_at ? 'Draft restored' : 'Changes will be saved automatically'; ready = true;
      Object.entries(result.payload._files || {}).forEach(([name, meta]) => {
        const note = document.createElement('p'); note.className = 'text-sm text-psu';
        note.textContent = 'Saved attachment: ' + meta.name + '. It will be submitted unless replaced.';
        uploads.find(el => el.name === name)?.after(note);
        const control = uploads.find(el => el.name === name);
        if (control) control.required = false;
      });
    }).catch(() => { text.textContent = 'Draft storage unavailable. Unsaved changes may be lost.'; ready = true; });
    form.addEventListener('input', event => {
      if (!controls.includes(event.target)) return;
      dirty = true; revision++; text.textContent = 'Unsaved changes'; clearTimeout(timer); timer = setTimeout(save, 500);
    });
    form.addEventListener('change', event => { if (ready && controls.includes(event.target)) { dirty = true; revision++; clearTimeout(timer); save(); } });
    uploads.forEach(control => control.addEventListener('change', () => {
      const file = control.files[0]; if (!file) return;
      const task = (async () => {
      dirty = true; text.textContent = 'Saving attachment…';
      const data = new FormData(); data.append('field', control.name); data.append('upload', file);
      try {
        const response = await fetch('/workspace/draft-uploads/' + encodeURIComponent(key), { method:'POST',
          headers:{'X-CSRFToken':csrf() || ''}, body:data, redirect:'error' });
        if (!response.ok) throw new Error('Upload failed');
        await save();
      } catch { text.textContent = 'Attachment could not be saved. Keep this page open and try again.'; }
      })();
      uploadTasks.add(task);
      task.finally(() => uploadTasks.delete(task));
    }));
    form.addEventListener('submit', async event => {
      if (submitting || event.defaultPrevented) return;
      event.preventDefault();
      if (preparing) return;
      preparing = true;
      clearTimeout(timer);
      await Promise.all([...uploadTasks]);
      await saving;
      if (dirty) await save();
      dirty = false;
      submitting = true;
      form.requestSubmit(event.submitter);
    });
    window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
    discard.addEventListener('click', async () => {
      if (!confirm('Discard the saved input for this form?')) return;
      clearTimeout(timer);
      await saving;
      try { await request(key, 'DELETE'); dirty = false; form.reset(); text.textContent = 'Draft discarded'; }
      catch { text.textContent = 'Could not discard the draft. Try again.'; }
    });
  });
  const signup = document.querySelector('form[data-signup-draft]');
  if (signup) {
    const key = 'psu:signup';
    const fields = [...signup.elements].filter(el => safeNames.has(el.name) && !['password','hidden','file','checkbox'].includes(el.type));
    try {
      const saved = JSON.parse(sessionStorage.getItem(key) || '{}');
      fields.forEach(el => { if (saved[el.name] !== undefined && !el.value) el.value = saved[el.name]; });
      signup.querySelector('[name=campus]')?.dispatchEvent(new Event('change', { bubbles:true }));
      fields.forEach(el => { if (saved[el.name] !== undefined && !el.value) el.value = saved[el.name]; });
      signup.addEventListener('input', () => sessionStorage.setItem(key, JSON.stringify(Object.fromEntries(fields.map(el => [el.name, el.value])))));
    } catch { /* Browser storage can be unavailable in private sessions. */ }
  }
})();
