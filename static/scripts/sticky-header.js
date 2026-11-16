(() => {
  const header = document.querySelector('.role-topbar');
  if (!header) return;
  const root = document.documentElement;
  const update = () => {
    const height = Math.ceil(header.getBoundingClientRect().height);
    const active = document.activeElement;
    const covered = active && !header.contains(active) && !active.closest('dialog[open], .role-sidebar') &&
      active.matches('a,button,input,select,textarea,summary,[data-form-errors]') &&
      active.getBoundingClientRect().top < height && active.getBoundingClientRect().bottom > 0;
    root.style.setProperty('--role-header-height', `${height}px`);
    if (covered) requestAnimationFrame(() => active.scrollIntoView({block:'start'}));
  };
  update();
  if ('ResizeObserver' in window) new ResizeObserver(update).observe(header);
  else window.addEventListener('resize', update);
  // A direct fragment can be positioned before fonts and the header finish layout.
  if (location.hash) requestAnimationFrame(() => {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    document.getElementById(id)?.scrollIntoView({block:'start'});
  });
})();
