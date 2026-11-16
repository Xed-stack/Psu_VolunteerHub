(() => {
  document.querySelector('.documents-page')?.addEventListener('focusin', event => {
    const control = event.target;
    if (!control.matches('a,button,input,select,textarea')) return;
    requestAnimationFrame(() => {
      if (document.activeElement !== control) return;
      const box = control.getBoundingClientRect();
      const header = document.querySelector('.role-topbar').getBoundingClientRect();
      const navigation = document.querySelector('.mobile-nav').getBoundingClientRect();
      const bottom = navigation.height ? navigation.top : window.innerHeight;
      if (box.top < header.bottom || box.bottom > bottom) {
        control.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'auto' });
      }
    });
  });
  const form = document.querySelector('[data-activity-document="announcement"]');
  if (!form) return;
  const type = form.querySelector('#announcement_type');
  const message = form.querySelector('#message');
  const update = () => {
    form.querySelector('[data-preview-type]').textContent = type.value ? type.selectedOptions[0].textContent : 'Select an announcement type';
    form.querySelector('[data-preview-message]').textContent = message.value.trim() || 'Your message preview will appear here.';
    form.querySelector('[data-message-count]').textContent = `${message.value.length} of 1,000 characters`;
  };
  form.addEventListener('input',update);
  form.addEventListener('change',update);
  form.addEventListener('draft:restored',update);
  update();
})();
