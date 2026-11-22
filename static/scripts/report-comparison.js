(() => {
  const dropdown = document.querySelector('[data-comparison-dropdown]');
  if (!dropdown) return;
  const trigger = dropdown.querySelector('summary');
  const panel = dropdown.querySelector('form');
  const position = () => {
    if (!dropdown.open) return;
    const edge = 12;
    const viewport = window.visualViewport;
    const width = viewport?.width || innerWidth;
    const height = viewport?.height || innerHeight;
    const anchor = trigger.getBoundingClientRect();
    panel.style.width = Math.min(360,width-2*edge) + 'px';
    const below = Math.max(0,height-anchor.bottom-edge-8);
    const above = Math.max(0,anchor.top-edge-8);
    const openBelow = below >= panel.scrollHeight || below >= above;
    panel.style.maxHeight = Math.max(100,openBelow ? below : above) + 'px';
    const measured = panel.getBoundingClientRect();
    const top = openBelow ? anchor.bottom+8 : anchor.top-measured.height-8;
    panel.style.left = Math.max(edge,Math.min(anchor.right-measured.width,width-measured.width-edge)) + 'px';
    panel.style.top = Math.max(edge,Math.min(top,height-measured.height-edge)) + 'px';
  };
  dropdown.addEventListener('toggle',position);
  document.addEventListener('pointerdown',event => {
    if (dropdown.open && !dropdown.contains(event.target)) dropdown.open = false;
  });
  dropdown.addEventListener('keydown',event => {
    if (event.key === 'Escape' && dropdown.open) {
      event.preventDefault();dropdown.open = false;trigger.focus();
    }
  });
  dropdown.addEventListener('focusout',event => {
    if (event.relatedTarget && !dropdown.contains(event.relatedTarget)) dropdown.open = false;
  });
  addEventListener('resize',position);
  addEventListener('scroll',position,{passive:true});
  window.visualViewport?.addEventListener('resize',position);
  if (window.ResizeObserver) new ResizeObserver(position).observe(panel);
  dropdown.classList.add('is-enhanced');
})();
