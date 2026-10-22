const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

function setup() {
  let now = 1000000, tick, response, serverExpiry = 2800;
  const requests = [], listeners = {}, windowListeners = {}, dialogListeners = {};
  const stay = { disabled: false, focus() { this.focusedWhileEnabled = !this.disabled; },
    addEventListener(_, fn) { this.click = fn; } };
  const status = { textContent: '' }, countdown = { textContent: '' };
  const previous = { isConnected: true, focused: false, focus() { this.focused = true; } };
  const form = { addEventListener(_, fn) { this.submit = fn; } };
  const csrfField = { value: 'csrf-qa' };
  const dialog = {
    open: false, dataset: { statusUrl: '/auth/session', loginUrl: '/auth/login',
      serverTime: '1000', expiresAt: '2800', warningSeconds: '60', csrfToken: 'csrf-qa' },
    querySelector(selector) {
      return { '[data-idle-stay]': stay, '[data-idle-status]': status,
        '[data-idle-countdown]': countdown, 'form': form,
        '[name="csrf_token"]': csrfField }[selector];
    },
    contains(target) { return target === stay; },
    showModal() { this.open = true; }, close() { this.open = false; },
    addEventListener(name, fn) { dialogListeners[name] = fn; },
  };
  const document = { hidden: false, activeElement: previous,
    getElementById() { return dialog; }, addEventListener(name, fn) { listeners[name] = fn; } };
  const window = { location: { replace(url) { this.replaced = url; } },
    setInterval(fn) { tick = fn; }, setTimeout() {}, clearTimeout() {},
    addEventListener(name, fn) { windowListeners[name] = fn; } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/scripts/session-idle.js'), 'utf8'), {
    document, window, Date: { now: () => now }, AbortController,
    fetch: async (url, options) => {
      requests.push({ url, options });
      if (response instanceof Error) throw response;
      if (options.method === 'POST') serverExpiry = now / 1000 + 1800;
      return response || { ok: true, status: 200, json: async () => ({
        server_time: now / 1000, csrf_token: 'csrf-refreshed',
        expires_at: serverExpiry }) };
    },
  });
  const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
  return { dialog, stay, form, csrfField, status, countdown, previous, document, window, requests, listeners,
    windowListeners, flush, advance(seconds) { now += seconds * 1000; }, tick: () => tick(),
    respond(value) { response = value; }, escape() { dialogListeners.cancel(); dialog.close(); },
    activity(name = 'keydown', trusted = true) { listeners[name]({ isTrusted: trusted, target: {} }); } };
}

test('unattended timer reads once at warning and never renews', async () => {
  const ui = setup();
  ui.advance(1740); ui.tick(); await ui.flush();
  assert.equal(ui.dialog.open, true);
  assert.equal(ui.stay.focusedWhileEnabled, true);
  assert.equal(ui.requests[0].options.method, 'GET');
  for (let n = 0; n < 5; n++) ui.tick();
  assert.equal(ui.requests.length, 1);
  assert.match(ui.countdown.textContent, /60 seconds/);
});

test('stay signed in uses CSRF POST then closes and restores focus', async () => {
  const ui = setup(); ui.advance(1740); ui.tick(); await ui.flush();
  ui.stay.click(); await ui.flush();
  assert.equal(ui.requests[1].options.method, 'POST');
  assert.equal(ui.requests[1].options.headers['X-CSRFToken'], 'csrf-refreshed');
  assert.equal(ui.csrfField.value, 'csrf-refreshed');
  assert.equal(ui.dialog.open, false);
  assert.equal(ui.previous.focused, true);
  assert.equal(ui.stay.disabled, false);
  ui.advance(1740); ui.tick(); await ui.flush();
  assert.equal(ui.requests.length, 3);
  assert.equal(ui.dialog.open, true);
  assert.equal(ui.countdown.textContent, '60 seconds');
});

test('human activity is throttled; synthetic events and hidden tabs never renew', async () => {
  const ui = setup(); ui.advance(40);
  ui.activity('input', false); assert.equal(ui.requests.length, 0);
  ui.document.hidden = true; ui.activity(); assert.equal(ui.requests.length, 0);
  ui.document.hidden = false; ui.activity(); await ui.flush();
  ui.activity('scroll'); await ui.flush();
  assert.equal(ui.requests.length, 1);
  assert.equal(ui.requests[0].options.method, 'POST');
});

test('escape dismisses without renewing; expired server response redirects to login', async () => {
  const ui = setup(); ui.advance(1740); ui.tick(); await ui.flush(); ui.escape();
  ui.tick(); await ui.flush(); assert.equal(ui.dialog.open, false);
  assert.equal(ui.requests.length, 1);
  ui.respond({ status: 401 }); ui.advance(60); ui.tick(); await ui.flush();
  assert.equal(ui.window.location.replaced, '/auth/login');
  assert.equal(ui.requests[1].options.method, 'GET');
});

test('another tab renewal is read before warning and before expiry', async () => {
  const ui = setup(); ui.advance(1740);
  ui.respond({ ok: true, status: 200, json: async () => ({ server_time: 2740, expires_at: 4500 }) });
  ui.tick(); await ui.flush(); assert.equal(ui.dialog.open, false);
  ui.advance(60); ui.tick(); await ui.flush();
  assert.equal(ui.window.location.replaced, undefined);
  assert.equal(ui.requests.length, 1);
  ui.advance(1640);
  ui.respond({ ok: true, status: 200, json: async () => ({ server_time: 4440, expires_at: 4500 }) });
  ui.tick(); await ui.flush();
  assert.equal(ui.dialog.open, true);
});

test('network errors are visible, retryable, and never falsely claim expiry', async () => {
  const ui = setup(); ui.respond(new Error('offline'));
  ui.advance(1740); ui.tick(); await ui.flush();
  assert.equal(ui.dialog.open, true); assert.match(ui.status.textContent, /Check your connection/);
  assert.equal(ui.window.location.replaced, undefined); assert.equal(ui.stay.disabled, false);
  ui.respond(null); ui.stay.click(); await ui.flush(); assert.equal(ui.dialog.open, false);
});

test('background restore checks status without renewal; logout prevents heartbeat races', async () => {
  const ui = setup(); ui.advance(40); ui.listeners.visibilitychange(); await ui.flush();
  assert.equal(ui.requests[0].options.method, 'GET');
  ui.windowListeners.pageshow({ persisted: true }); await ui.flush();
  assert.equal(ui.requests[1].options.method, 'GET');
  ui.form.submit(); ui.activity(); ui.tick(); await ui.flush();
  assert.equal(ui.requests.length, 2);
});
