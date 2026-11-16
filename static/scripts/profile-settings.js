(() => {
  const forms = [...document.querySelectorAll('[data-profile-form]')];
  if (!forms.length) return;
  const openSection = () => {
    const section = document.getElementById(location.hash.slice(1));
    if (section?.matches('.profile-account-section')) section.open = true;
  };
  openSection();
  window.addEventListener('hashchange', openSection);
  const campus = document.getElementById('account-campus_id');
  const college = document.getElementById('account-college_affiliation');
  const colleges = JSON.parse(document.getElementById('profile-colleges').textContent);
  campus?.addEventListener('change', () => {
    college.replaceChildren(new Option('Select your college', ''));
    (colleges[campus.value] || []).forEach(name => college.add(new Option(name, name)));
  });
  document.querySelectorAll('[data-profile-password]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => {
      const field = document.getElementById(button.dataset.profilePassword);
      const show = field.type === 'password';
      field.type = show ? 'text' : 'password';
      button.textContent = show ? 'Hide' : 'Show';
      button.setAttribute('aria-pressed', String(show));
      const label = document.querySelector(`label[for="${field.id}"]`).textContent.replace(/\s*\*\s*$/, '').trim();
      button.setAttribute('aria-label', `${show ? 'Hide' : 'Show'} ${label}`);
    });
  });
  document.querySelector('[data-profile-errors]')?.focus();
  const preferences = document.getElementById('profile-form');
  const updateCounts = () => {
    document.querySelectorAll('[data-profile-count]').forEach(count => {
      const name = count.dataset.profileCount;
      const fields = [...preferences.querySelectorAll(`input[name="${name}"]`)];
      const text = `${fields.filter(field => field.checked).length} of ${fields.length} selected.`;
      count.hidden = false;
      if (count.textContent !== text) count.textContent = text;
    });
  };
  if (preferences) {
    updateCounts();
    preferences.addEventListener('change', updateCounts);
    preferences.addEventListener('draft:restored', updateCounts);
  }
  const photo = document.getElementById('profile-image');
  const preview = document.querySelector('[data-profile-photo-preview]');
  const fallback = document.querySelector('[data-profile-photo-fallback]');
  let previewUrl = null;
  photo?.addEventListener('change', () => {
    const file = photo.files[0];
    if (!file || !['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 3*1024*1024 || !preview) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
    if (fallback) fallback.hidden = true;
  });
  window.addEventListener('pagehide', () => { if (previewUrl) URL.revokeObjectURL(previewUrl); });
  const snapshots = new Map();
  const values = form => JSON.stringify([...new FormData(form)].filter(([key]) => !['csrf_token', '_draft_key'].includes(key))
    .map(([key, value]) => [key, value instanceof File ? [value.name, value.size, value.lastModified] : value]));
  forms.forEach(form => snapshots.set(form, values(form)));
  forms.forEach(form => {
    form.addEventListener('draft:saved', () => snapshots.set(form, values(form)));
    form.addEventListener('draft:restored', () => snapshots.set(form, values(form)));
  });
  let submitting = null;
  const restore = () => { submitting = null; };
  document.addEventListener('submit', event => {
    if (forms.includes(event.target) && !event.defaultPrevented) submitting = event.target;
  });
  window.addEventListener('beforeunload', event => {
    if (forms.some(form => form !== submitting && values(form) !== snapshots.get(form))) {
      event.preventDefault();
      event.returnValue = '';
      // A cancelled navigation must leave every form usable.
      setTimeout(() => {
        restore();
        document.dispatchEvent(new Event('form-submit-cancelled'));
      }, 0);
    }
  });
  window.addEventListener('pageshow', restore);
})();
