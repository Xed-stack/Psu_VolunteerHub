(() => {
  const page = document.querySelector('.aop-page');
  if (!page) return;
  const drafts = [...page.children].find(element =>
    element.matches('section') && element.querySelector('h2')?.textContent === 'Saved Drafts');
  const list = [...page.children].find(element =>
    element.matches('.aop-director-deliverables, #campus-results'));
  if (!drafts || !list) return;
  const originalPosition = document.createComment('Saved drafts position');
  drafts.before(originalPosition);
  const desktop = window.matchMedia('(min-width:1024px)');
  const arrangeDrafts = () => {
    if (desktop.matches) list.before(drafts);
    else originalPosition.after(drafts);
  };
  desktop.addEventListener('change', arrangeDrafts);
  arrangeDrafts();
})();
