(() => {
  const body = document.body;
  const role = body.dataset.tourRole;
  const replay = body.dataset.tourReplay === 'true';
  const firstUse = body.dataset.tourFirstUse === 'true';
  if (!role || (!replay && !firstUse) || !window.HTMLDialogElement) return;

  const steps = {
    volunteer: [
      ['recommendations', 'Find Your Next Activity', 'Recommendations use your selected interests and show your preferred campus first. Open an activity to review its schedule and details.'],
      ['calendar', 'Follow Your Commitments', 'The calendar shows upcoming registrations. It becomes your starting view when you have an active upcoming registration.'],
      ['opportunities', 'Review Details Before Registering', 'Browse all activities, read the participation agreement, and confirm only when the schedule works for you.'],
      ['registrations', 'Check Registration History', 'Open a registration to review its schedule, recorded participation, and exact withdrawal deadline. You can withdraw directly while eligible.'],
      ['profile', 'Keep Your Profile Current', 'Use Update Your Profile beside Recent Participation to maintain your interests, skills, and preferred campus.'],
    ],
    coordinator: [
      ['metrics', 'Start with Your Campus Overview', 'Activity figures use the reporting period. Volunteer accounts are all-time; verified attendees count each recorded presence. Information icons explain the measures.'],
      ['follow-up', 'Start with the Work Queue', 'Needs Attention explains each finding and opens its source. Ongoing events allow attendance entry; ended events use printed corrections.'],
      ['create-activity', 'Start with an Approved Proposal', 'Upload the approved PDF or DOCX, review extracted details, then complete audience and partners before publishing. Saved drafts survive refresh.'],
      ['activity-workspace', 'Follow Your Campus Schedule', 'Your agenda shows the next five ongoing or upcoming activities. Open an activity workspace or the full calendar. Record attendance during the event; it locks at the end.'],
      ['annual-goals', 'Track Annual Achievements', 'Review targets and evidence. Pending evidence remains unknown until verified.'],
      ['reports', 'Use Reports for Your Campus', 'Choose a report and scope, review its graphical results, and export matching values. Later attendance corrections belong on the printed report.'],
    ],
    director: [
      ['metrics', 'Start with University Results', 'Review approved and conducted activities, all-time volunteer accounts, verified presences, and annual AOP achievement. Information icons explain each calculation.'],
      ['follow-up', 'Follow up with Evidence', 'Open the work queue to review missing recording, schedule limitations, and verified target findings. Notify a campus coordinator only when you choose to send a reminder.'],
      ['campus-comparison', 'Compare Campuses', 'Compare activity delivery for the selected period beside annual AOP, ASP, and pending evidence. Open a campus for details. Delivery volume does not measure quality.'],
      ['annual-goals', 'Review Annual Achievements', 'Campus obligations are combined without averaging percentages. University-wide targets stay separate. Pending evidence remains unknown; open the source targets for details.'],
      ['reports', 'Choose and Export a Report', 'Reports covers activity accomplishments, AOPs, approved proposals, and historical records. Screen filters follow through to exports.'],
      ['management', 'Manage Accounts and Policies', 'Open dedicated screens for users, policies, settings, and imports. Imports require a validation preview and explicit confirmation.'],
    ],
  };

  const visibleTarget = (id) => Array.from(document.querySelectorAll(`[data-tour-id="${id}"]`))
    .find((node) => {
      const rect = node.getBoundingClientRect();
      const style = window.getComputedStyle(node);
      return rect.width > 0 && rect.height > 0 && rect.right > 0
        && rect.left < window.innerWidth && style.visibility !== 'hidden'
        && style.display !== 'none' && !node.closest('[hidden], [inert]');
    });
  const tourSteps = (steps[role] || []).map(([id, title, text]) => ({
    id, target: visibleTarget(id), title, text,
  })).filter((step) => step.target);
  if (!tourSteps.length) return;

  const dialog = document.createElement('dialog');
  dialog.className = 'first-use-tour';
  dialog.setAttribute('aria-labelledby', 'tourTitle');
  dialog.setAttribute('aria-describedby', 'tourText');
  dialog.innerHTML = `
    <div class="first-use-tour__spotlight" aria-hidden="true"></div>
    <section class="first-use-tour__card" aria-labelledby="tourTitle" aria-describedby="tourText">
      <p class="first-use-tour__count"></p>
      <h2 id="tourTitle"></h2>
      <p id="tourText" aria-live="polite"></p>
      <div class="first-use-tour__actions">
        <button class="btn btn--ghost" type="button" data-tour-skip>Skip Guide</button>
        <span class="first-use-tour__navigation">
          <button class="btn btn--outline" type="button" data-tour-back>Back</button>
          <button class="btn btn--primary" type="button" data-tour-next>Next</button>
        </span>
      </div>
    </section>`;
  document.body.append(dialog);

  const spotlight = dialog.querySelector('.first-use-tour__spotlight');
  const count = dialog.querySelector('.first-use-tour__count');
  const title = dialog.querySelector('#tourTitle');
  const text = dialog.querySelector('#tourText');
  const back = dialog.querySelector('[data-tour-back]');
  const next = dialog.querySelector('[data-tour-next]');
  const card = dialog.querySelector('.first-use-tour__card');
  const skip = dialog.querySelector('[data-tour-skip]');
  let index = 0;
  let target = null;
  const replayControl = document.querySelector('[data-guide-replay]');

  const restoreFocus = () => {
    const focusTarget = replay && replayControl ? replayControl : target;
    if (!focusTarget) return;
    if (!focusTarget.matches('a[href], button, input, select, textarea, [tabindex]')) {
      focusTarget.setAttribute('tabindex', '-1');
      focusTarget.addEventListener('blur', () => focusTarget.removeAttribute('tabindex'), { once: true });
    }
    focusTarget.focus({ preventScroll: true });
  };

  const dismiss = async () => {
    if (skip.disabled) return;
    skip.disabled = true;
    back.disabled = true;
    next.disabled = true;
    if (!replay) {
      const token = document.querySelector('meta[name="csrf-token"]')?.content;
      try {
        const response = await fetch(body.dataset.tourDismissUrl, {
          method: 'POST', credentials: 'same-origin',
          headers: token ? { 'X-CSRFToken': token, 'Accept': 'application/json' } : {},
        });
        if (!response.ok) throw new Error('Guide save failed');
      } catch (_) {
        text.textContent = 'The guide could not be saved. Please try again.';
        skip.disabled = back.disabled = next.disabled = false;
        return;
      }
    }
    dialog.close();
    resizeObserver.disconnect();
    window.removeEventListener('resize', place);
    window.removeEventListener('scroll', place, true);
    if (replay) {
      const url = new URL(location.href); url.searchParams.delete('tour');
      history.replaceState(null, '', url);
    }
    restoreFocus();
  };

  const place = () => {
    if (!target) return;
    const currentTarget = visibleTarget(tourSteps[index].id);
    if (!currentTarget) {
      if (index < tourSteps.length - 1) {
        index += 1;
        show();
      } else dismiss();
      return;
    }
    target = currentTarget;
    const rect = spotlightTarget().getBoundingClientRect();
    spotlight.style.setProperty('--tour-x', `${Math.max(8, rect.left - 6)}px`);
    spotlight.style.setProperty('--tour-y', `${Math.max(8, rect.top - 6)}px`);
    spotlight.style.setProperty('--tour-width', `${Math.min(window.innerWidth - 16, rect.width + 12)}px`);
    spotlight.style.setProperty('--tour-height', `${Math.min(window.innerHeight - 16, rect.height + 12)}px`);
    if (window.innerWidth > 767) {
      const width = card.offsetWidth;
      const height = card.offsetHeight;
      const left = rect.right + width + 24 < window.innerWidth
        ? rect.right + 16 : Math.max(16, Math.min(rect.left, window.innerWidth - width - 16));
      const top = rect.bottom + height + 24 < window.innerHeight
        ? rect.bottom + 16 : Math.max(16, rect.top - height - 16);
      card.style.left = `${left}px`;
      card.style.top = `${Math.min(top, window.innerHeight - height - 16)}px`;
    } else {
      card.style.removeProperty('left');
      card.style.removeProperty('top');
    }
  };

  const spotlightTarget = () => {
    const availableHeight = window.innerHeight - card.offsetHeight - 48;
    if (window.innerWidth <= 767 && target.getBoundingClientRect().height > availableHeight) {
      return target.querySelector('.metric-tile, .section-top, .summary-stat, .panel__header, h2') || target;
    }
    return target;
  };

  const resizeObserver = new ResizeObserver(place);
  resizeObserver.observe(card);
  resizeObserver.observe(document.documentElement);

  const show = () => {
    const step = tourSteps[index];
    target = visibleTarget(step.id) || step.target;
    count.textContent = `Step ${index + 1} of ${tourSteps.length}`;
    title.textContent = step.title;
    text.textContent = step.text;
    back.hidden = index === 0;
    next.textContent = index === tourSteps.length - 1 ? 'Finish' : 'Next';
    spotlightTarget().scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
    if (window.innerWidth <= 767 && !target.closest('.role-sidebar')) {
      window.scrollBy({ top: card.offsetHeight / 2, behavior: 'instant' });
    }
    place();
    if (card.scrollHeight > card.clientHeight) {
      card.scrollTop = 0;
      title.tabIndex = -1;
      title.focus({ preventScroll: true });
    } else next.focus();
  };

  back.addEventListener('click', () => { index -= 1; show(); });
  next.addEventListener('click', () => {
    if (index === tourSteps.length - 1) dismiss();
    else { index += 1; show(); }
  });
  skip.addEventListener('click', dismiss);
  dialog.addEventListener('cancel', (event) => { event.preventDefault(); dismiss(); });
  dialog.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab') return;
    const controls = Array.from(dialog.querySelectorAll('button'))
      .filter((button) => !button.hidden && !button.disabled);
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (!controls.length) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  window.addEventListener('resize', place);
  window.addEventListener('scroll', place, true);
  dialog.showModal();
  show();
})();
