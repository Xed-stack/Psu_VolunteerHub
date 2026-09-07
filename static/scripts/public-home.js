(() => {
  const hero = document.querySelector('[data-hero-carousel]');
  const heroControls = document.querySelector('[data-hero-controls]');

  if (hero && heroControls) {
    const slides = [...hero.querySelectorAll('[data-hero-slide]')];
    const dots = [...heroControls.querySelectorAll('[data-hero-dot]')];
    const pauseButton = heroControls.querySelector('[data-hero-pause]');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let activeIndex = 0;
    let rotationTimer = null;
    let isPaused = reduceMotion.matches;

    const showSlide = (index) => {
      activeIndex = (index + slides.length) % slides.length;
      slides.forEach((slide, slideIndex) => {
        slide.classList.toggle('is-active', slideIndex === activeIndex);
      });
      dots.forEach((dot, dotIndex) => {
        const isActive = dotIndex === activeIndex;
        dot.classList.toggle('is-active', isActive);
        dot.setAttribute('aria-pressed', String(isActive));
      });
    };

    const stopRotation = () => {
      window.clearInterval(rotationTimer);
      rotationTimer = null;
    };

    const startRotation = () => {
      stopRotation();
      if (!isPaused && slides.length > 1) {
        rotationTimer = window.setInterval(() => showSlide(activeIndex + 1), 6000);
      }
    };

    const setPaused = (paused) => {
      isPaused = paused;
      pauseButton.querySelector('.material-symbols-outlined').textContent = paused
        ? 'play_arrow'
        : 'pause';
      pauseButton.setAttribute(
        'aria-label',
        paused ? 'Resume photo rotation' : 'Pause photo rotation',
      );
      startRotation();
    };

    heroControls.querySelector('[data-hero-prev]').addEventListener('click', () => {
      showSlide(activeIndex - 1);
      startRotation();
    });
    heroControls.querySelector('[data-hero-next]').addEventListener('click', () => {
      showSlide(activeIndex + 1);
      startRotation();
    });
    dots.forEach((dot) => {
      dot.addEventListener('click', () => {
        showSlide(Number(dot.dataset.heroDot));
        startRotation();
      });
    });
    pauseButton.addEventListener('click', () => setPaused(!isPaused));
    hero.addEventListener('mouseenter', stopRotation);
    hero.addEventListener('mouseleave', startRotation);
    hero.addEventListener('focusin', stopRotation);
    hero.addEventListener('focusout', startRotation);
    reduceMotion.addEventListener('change', (event) => setPaused(event.matches));

    setPaused(isPaused);
  }

  const carousel = document.querySelector('[data-carousel]');
  const controls = document.querySelector('[data-carousel-controls]');

  if (carousel && controls) {
    controls.hidden = false;
    const previous = controls.querySelector('[data-carousel-prev]');
    const next = controls.querySelector('[data-carousel-next]');
    const card = carousel.querySelector('.featured-card');

    const updateButtons = () => {
      previous.disabled = carousel.scrollLeft <= 4;
      next.disabled = carousel.scrollLeft + carousel.clientWidth >=
        carousel.scrollWidth - 4;
    };

    const move = (direction) => {
      const distance = (card?.getBoundingClientRect().width || 320) + 20;
      carousel.scrollBy({
        left: direction * distance,
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
          ? 'auto'
          : 'smooth',
      });
    };

    previous.addEventListener('click', () => move(-1));
    next.addEventListener('click', () => move(1));
    carousel.addEventListener('scroll', updateButtons, { passive: true });
    updateButtons();
  }

  document.querySelectorAll('[data-open-event]').forEach((button) => {
    button.addEventListener('click', () => {
      const dialog = document.getElementById(button.dataset.openEvent);
      if (dialog?.showModal) dialog.showModal();
    });
  });

  document.querySelectorAll('[data-close-dialog]').forEach((button) => {
    button.addEventListener('click', () => button.closest('dialog')?.close());
  });

  document.querySelectorAll('dialog').forEach((dialog) => {
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) dialog.close();
    });
  });
})();
