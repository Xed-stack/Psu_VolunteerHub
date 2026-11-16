(() => {
  const shell = document.querySelector('[data-onboarding]');
  if (!shell) return;
  const form = shell.querySelector('form');
  const status = shell.querySelector('[data-onboarding-status]');
  if (!form || !status) return;
  status.hidden = false;
  const key = 'psu:signup';
  const preferences = form.hasAttribute('data-onboarding-preferences');
  const names = ['first_name', 'last_name', 'email', 'sex', 'volunteer_type', 'id_number', 'campus', 'college_affiliation'];
  const fields = names.map(name => form.elements.namedItem(name)).filter(Boolean);
  let saved = {};
  let storageAvailable = true;
  try {
    const parsed = JSON.parse(sessionStorage.getItem(key) || '{}');
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) saved = parsed;
  } catch {
    storageAvailable = false;
  }
  const serverValues = shell.dataset.serverValues === 'true';
  const campus = form.elements.namedItem('campus');
  const affiliation = form.elements.namedItem('college_affiliation');
  const campusData = document.getElementById('onboarding-campus-options');
  const optionsByCampus = campusData ? JSON.parse(campusData.textContent) : {};
  const preferenceData = document.getElementById('onboarding-preferences');
  const submittedPreferences = preferenceData ? JSON.parse(preferenceData.textContent) : {};

  const updateCampus = (announce = false) => {
    if (!campus || !affiliation) return;
    const previous = affiliation.value;
    const options = optionsByCampus[campus.value] || [];
    affiliation.replaceChildren(new Option(campus.value ? (options.length ? 'Select an Affiliation' : 'No Affiliations Configured') : 'Select a Campus First', ''));
    options.forEach(value => affiliation.add(new Option(value, value)));
    affiliation.disabled = !campus.value;
    if (options.includes(previous)) affiliation.value = previous;
    const hint = document.getElementById('college-affiliation-hint');
    hint.textContent = previous && !affiliation.value && announce
      ? 'Your previous affiliation is unavailable for this campus. Choose an affiliation again.'
      : campus.value && !options.length
        ? 'No affiliations are configured for this campus. PSU students and employees should contact their campus coordinator.'
        : 'Choose an affiliation for your preferred campus.';
  };
  if (!serverValues) {
    fields.filter(field => field !== affiliation).forEach(field => {
      if (typeof saved[field.name] === 'string') field.value = saved[field.name];
    });
  }
  updateCampus();
  if (!serverValues && affiliation && typeof saved.college_affiliation === 'string') {
    affiliation.value = saved.college_affiliation;
  }
  campus?.addEventListener('change', () => updateCampus(true));

  const groups = [...form.querySelectorAll('.choice-group')];
  const staleChoices = [];
  if (preferences && !serverValues) {
    for (const name of ['interests', 'skills']) {
      if (!Array.isArray(saved[name])) continue;
      const available = new Set([...form.querySelectorAll(`input[name="${name}"]`)].map(input => input.value));
      const archivedData = document.getElementById('onboarding-archived-skills');
      const archived = archivedData ? JSON.parse(archivedData.textContent) : {};
      saved[name].filter(value => !available.has(value)).forEach(value => staleChoices.push(name === 'skills' ? archived[value] || 'an unavailable skill' : 'an unavailable interest'));
      form.querySelectorAll(`input[name="${name}"]`).forEach(input => {
        input.checked = saved[name].includes(input.value);
      });
    }
  }
  const updatePreferences = () => {
    groups.forEach(group => {
      const selected = group.querySelector('input[name="interests"]').checked;
      const skills = group.querySelector('.related-skills');
      if (skills) skills.hidden = !selected;
      group.querySelectorAll('input[name="skills"]').forEach(input => {
        input.disabled = !selected;
        if (!selected) input.checked = false;
      });
    });
    const count = form.querySelector('[data-selection-count]');
    if (count) {
      const interests = form.querySelectorAll('input[name="interests"]:checked').length;
      const skills = new Set([...form.querySelectorAll('input[name="skills"]:checked')].map(input => input.value)).size;
      count.hidden = false;
      count.textContent = `${interests} interest${interests === 1 ? '' : 's'} and ${skills} skill${skills === 1 ? '' : 's'} selected.`;
    }
  };
  updatePreferences();
  form.addEventListener('change', event => {
    if (event.target.name === 'skills') {
      form.querySelectorAll('input[name="skills"]').forEach(input => {
        if (!input.disabled && input.value === event.target.value) input.checked = event.target.checked;
      });
    }
    updatePreferences();
  });

  const message = text => { if (status.textContent !== text) status.textContent = text; };
  const save = () => {
    try {
      // Keep only ordinary onboarding fields, including when upgrading an older draft.
      const next = {};
      names.forEach(name => {
        const field = form.elements.namedItem(name);
        if (field) next[name] = field.value;
        else if (typeof saved[name] === 'string') next[name] = saved[name];
      });
      for (const name of ['interests', 'skills']) {
        next[name] = preferences
          ? [...new Set([...form.querySelectorAll(`input[name="${name}"]:checked`)].map(input => input.value))]
          : Array.isArray(submittedPreferences[name]) ? submittedPreferences[name].map(String) : [];
      }
      sessionStorage.setItem(key, JSON.stringify(next));
      saved = next;
      storageAvailable = true;
      message('Draft saved in this browser tab. Passwords and consent are not saved.');
    } catch {
      storageAvailable = false;
      message('Your input could not be saved in this browser tab. Keep this page open and try again. Passwords and consent are never saved.');
    }
  };
  form.addEventListener('input', save);
  // Change fires after dependent campus options and preference selections update.
  form.addEventListener('change', save);
  form.addEventListener('submit', save);
  if (!storageAvailable) message('Browser storage is unavailable. Keep this page open; your input cannot be restored after refresh.');
  else if (staleChoices.length) message(`Saved choices are no longer available: ${[...new Set(staleChoices)].join(', ')}. Choose replacements before continuing.`);
  else if (!serverValues && Object.keys(saved).length) message('Draft restored in this browser tab. Enter passwords and consent again.');
  else message('Your ordinary fields will be saved in this browser tab. Passwords and consent are not saved.');
})();
