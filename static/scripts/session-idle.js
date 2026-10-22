(() => {
  'use strict';
  const dialog = document.getElementById('session-idle');
  if (!dialog) return;
  const stay = dialog.querySelector('[data-idle-stay]');
  const status = dialog.querySelector('[data-idle-status]');
  const countdown = dialog.querySelector('[data-idle-countdown]');
  const warningMs = Number(dialog.dataset.warningSeconds) * 1000;
  const activityInterval = Math.min(30000, warningMs / 2);
  let expires = Number(dialog.dataset.expiresAt) * 1000;
  let offset = Number(dialog.dataset.serverTime) * 1000 - Date.now();
  let lastRenewal = Date.now();
  let checkedDeadline = null;
  let dismissedDeadline = null;
  let busy = false;
  let leaving = false;
  let previousFocus;
  const remaining = () => expires - (Date.now() + offset);

  function showWarning() {
    if (!dialog.open && dismissedDeadline !== expires) {
      previousFocus = document.activeElement;
      stay.disabled = false;
      dialog.showModal();
      stay.focus();
    }
  }

  function closeWarning() {
    if (dialog.open) {
      dialog.close();
      if (previousFocus?.isConnected) previousFocus.focus();
    }
  }

  async function check(renew = false) {
    if (busy || leaving) return;
    busy = true;
    stay.disabled = true;
    status.textContent = renew ? 'Keeping you signed in…' : 'Checking your session…';
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(dialog.dataset.statusUrl, {
        method: renew ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store',
        headers: renew ? { 'X-CSRFToken': dialog.dataset.csrfToken } : {},
        signal: controller.signal,
      });
      if (response.status === 401) {
        leaving = true;
        window.location.replace(dialog.dataset.loginUrl);
        return;
      }
      if (!response.ok) throw new Error('Session check failed');
      const data = await response.json();
      if (!Number.isFinite(data.server_time) || !Number.isFinite(data.expires_at)) {
        throw new Error('Invalid session response');
      }
      offset = data.server_time * 1000 - Date.now();
      if (typeof data.csrf_token === 'string') {
        dialog.dataset.csrfToken = data.csrf_token;
        dialog.querySelector('[name="csrf_token"]').value = data.csrf_token;
      }
      const newDeadline = data.expires_at * 1000;
      if (newDeadline !== expires) dismissedDeadline = null;
      expires = newDeadline;
      checkedDeadline = remaining() <= warningMs ? expires : null;
      status.textContent = '';
      if (renew) lastRenewal = Date.now();
      if (remaining() > warningMs) closeWarning();
      else showWarning();
    } catch (_) {
      status.textContent = 'Unable to check your session. Check your connection, then select Stay signed in to try again. Unsaved changes have not been saved.';
      // A network failure is not proof of expiry; the server still checks every action.
      dismissedDeadline = null;
      showWarning();
    } finally {
      window.clearTimeout(timeout);
      busy = false;
      stay.disabled = false;
    }
  }

  stay.addEventListener('click', () => check(true));
  dialog.addEventListener('cancel', () => { dismissedDeadline = expires; });
  dialog.querySelector('form').addEventListener('submit', () => { leaving = true; });

  function activity(event) {
    if (!event.isTrusted || document.hidden || dialog.open || leaving
        || dialog.contains(event.target)) return;
    if (Date.now() - lastRenewal >= activityInterval) check(true);
  }
  ['pointerdown', 'keydown', 'input', 'scroll'].forEach(name => {
    document.addEventListener(name, activity, { passive: true, capture: true });
  });

  function tick() {
    const milliseconds = remaining();
    countdown.textContent = `${Math.max(0, Math.ceil(milliseconds / 1000))} seconds`;
    if (document.hidden || leaving) return;
    // Read the shared cookie first: another tab may have renewed this session.
    if (milliseconds <= 0 || (milliseconds <= warningMs && checkedDeadline !== expires)) {
      check();
    }
  }
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) check();
  });
  window.addEventListener('pageshow', event => { if (event.persisted) check(); });
  window.setInterval(tick, 1000);
  tick();
})();
