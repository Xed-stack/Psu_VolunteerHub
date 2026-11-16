(() => {
  const hero = document.querySelector('.landing-hero');
  const controls = hero?.querySelector('[data-hero-controls]');
  if (hero && controls) {
    const slides = [...hero.querySelectorAll('[data-hero-slide]')];
    const dots = [...controls.querySelectorAll('[data-hero-dot]')];
    const pause = controls.querySelector('[data-hero-pause]');
    const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
    let active = 0, timer, paused = false, hovered = false;
    const show = index => {
      active = (index + slides.length) % slides.length;
      slides.forEach((slide,n) => {
        if (n === active && slide.dataset.src && !slide.getAttribute('src')) {
          slide.loading = 'eager'; slide.src = slide.dataset.src;
        }
        slide.classList.toggle('is-active',n === active);
        slide.setAttribute('aria-hidden',String(n !== active));
      });
      dots.forEach((dot,n) => {
        dot.classList.toggle('is-active',n === active);
        dot.setAttribute('aria-pressed',String(n === active));
      });
    };
    const stop = () => clearInterval(timer);
    const schedule = () => {
      stop();
      if (!paused && !hovered && !document.hidden && !reduceMotion.matches && slides.length > 1)
        timer = setInterval(() => show(active + 1),6000);
    };
    const setPaused = value => {
      paused = value;
      pause.disabled = reduceMotion.matches;
      pause.setAttribute('aria-label',reduceMotion.matches ? 'Photo Rotation Disabled for Reduced Motion' : paused ? 'Resume Photo Rotation' : 'Pause Photo Rotation');
      pause.querySelector('span').textContent = paused || reduceMotion.matches ? 'play_arrow' : 'pause';
      schedule();
    };
    controls.hidden = false;
    controls.querySelector('[data-hero-prev]').addEventListener('click',() => { setPaused(true); show(active - 1); });
    controls.querySelector('[data-hero-next]').addEventListener('click',() => { setPaused(true); show(active + 1); });
    dots.forEach(dot => dot.addEventListener('click',() => { setPaused(true); show(+dot.dataset.heroDot); }));
    pause.addEventListener('click',() => setPaused(!paused));
    hero.addEventListener('focusin',event => { if (event.target.matches(':focus-visible')) setPaused(true); });
    hero.addEventListener('mouseenter',() => { hovered = true; stop(); });
    hero.addEventListener('mouseleave',() => { hovered = false; schedule(); });
    document.addEventListener('visibilitychange',schedule);
    reduceMotion.addEventListener('change',() => setPaused(true));
    show(0); setPaused(false);
  }

  const carousel = document.querySelector('[data-carousel]');
  const arrows = document.querySelector('[data-carousel-controls]');
  if (carousel && arrows) {
    const previous = arrows.querySelector('[data-carousel-prev]');
    const next = arrows.querySelector('[data-carousel-next]');
    const update = () => {
      previous.disabled = carousel.scrollLeft <= 4;
      next.disabled = carousel.scrollLeft + carousel.clientWidth >= carousel.scrollWidth - 4;
      arrows.hidden = carousel.scrollWidth <= carousel.clientWidth + 4;
    };
    const move = direction => {
      const distance = (carousel.querySelector('.featured-card')?.getBoundingClientRect().width || 320) + 20;
      carousel.scrollBy({left:direction * distance,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
    };
    previous.addEventListener('click',() => move(-1));
    next.addEventListener('click',() => move(1));
    carousel.addEventListener('scroll',update,{passive:true});
    window.addEventListener('resize',update);
    update();
  }
})();
