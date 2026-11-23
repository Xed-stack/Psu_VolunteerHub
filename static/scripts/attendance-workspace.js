(() => {
  const workspace = document.querySelector('[data-attendance-workspace], [data-roster-entry]');
  if (!workspace) return;

  const statuses = [...workspace.querySelectorAll('[data-attendance-status]')];
  const countNodes = [...workspace.querySelectorAll('[data-attendance-count]')];
  const changeStatus = workspace.querySelector('[data-attendance-change-status]');
  const labels = { present: 'Attended', absent: 'Not Attended' };
  const initial = statuses.map(select => select.value);
  const entry = workspace.hasAttribute('data-roster-entry');
  const entryControls = entry ? [...workspace.elements].filter(el => el.name && el.type !== 'hidden') : [];
  const retainedEntry = workspace.dataset.entryUnsaved === 'true' && entryControls.some(el => el.type === 'checkbox' ? el.checked : el.value);
  const entryValues = () => JSON.stringify(entryControls.map(el => el.type === 'checkbox' ? el.checked : el.value));
  const initialEntry = entryValues();
  const dirty = () => entry ? retainedEntry || entryValues() !== initialEntry : statuses.some((select,index) => select.value !== initial[index]);
  let submitting = false;
  workspace.addEventListener('submit', () => { submitting = true; });
  window.addEventListener('beforeunload', event => {
    if (!submitting && dirty()) {
      event.preventDefault();
      event.returnValue = '';
    }
  });
  window.addEventListener('pageshow', () => { submitting = false; });
  if (entry) {
    const feedback = () => {
      if (changeStatus) changeStatus.textContent = dirty() ? 'Unsaved input. Save the named roster before leaving this page.' : 'Input is not saved automatically.';
    };
    workspace.addEventListener('input',feedback);
    workspace.addEventListener('change',feedback);
    feedback();
  }

  const updateCounts = () => {
    const counts = { registered: statuses.length, present: 0, absent: 0, excused: 0, unmarked: 0 };
    statuses.forEach(select => { counts[select.value || 'unmarked'] += 1; });
    countNodes.forEach(node => { node.textContent = counts[node.dataset.attendanceCount]; });
  };

  const setAll = status => {
    if (!statuses.length) return;
    const message = `Mark all ${statuses.length} displayed volunteer${statuses.length === 1 ? '' : 's'} as ${labels[status]}? You can make individual corrections before saving.`;
    if (!window.confirm(message)) return;
    statuses.forEach(select => { select.value = status; });
    updateCounts();
    if (changeStatus) changeStatus.textContent = `All displayed volunteers are marked ${labels[status]}. Save attendance to record these changes.`;
  };

  statuses.forEach(select => select.addEventListener('change', () => {
    updateCounts();
    const changed = statuses.filter((select,index) => select.value !== initial[index]).length;
    if (changeStatus) changeStatus.textContent = changed ? `${changed} unsaved attendance change${changed === 1 ? '' : 's'}. Save attendance before leaving this page.` : 'No unsaved changes.';
  }));
  workspace.querySelectorAll('[data-attendance-bulk]').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => setAll(button.dataset.attendanceBulk));
  });
  updateCounts();
})();
