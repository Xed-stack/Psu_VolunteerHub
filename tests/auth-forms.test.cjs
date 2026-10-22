const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

function setup({ invalid = false, dialog = false, retained = false } = {}) {
  const documentListeners = {};
  const windowListeners = {};
  const formListeners = {};
  const input = { type: 'password', focused: false, focus() { this.focused = true; } };
  const attributes = { 'aria-label': 'Show password', 'aria-pressed': 'false' };
  let click;
  const button = { dataset: { togglePassword: 'password' }, hidden: true,
    getAttribute(name) { return attributes[name]; },
    setAttribute(name, value) { attributes[name] = value; },
    addEventListener(name, listener) { click = listener; } };
  const form = { dataset: { warnUnsaved: String(retained) },
    addEventListener(name, listener) { formListeners[name] = listener; } };
  const nativeDialog = { open: false, showModal() { this.open = true; },
    addEventListener(name, listener) { this[name] = listener; } };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/scripts/auth-forms.js'), 'utf8'), {
    document: {
      querySelectorAll() { return [button]; },
      getElementById() { return input; },
      querySelector(selector) {
        if (selector.includes('aria-invalid')) return invalid ? input : null;
        if (selector === 'dialog[data-auto-open]') return dialog ? nativeDialog : null;
        if (selector === 'form[data-warn-unsaved]') return form;
        return null;
      },
      addEventListener(name, listener) { documentListeners[name] = listener; },
    },
    window: { addEventListener(name, listener) { windowListeners[name] = listener; } },
  });
  const unload = () => {
    const event = { prevented: false, preventDefault() { this.prevented = true; } };
    windowListeners.beforeunload(event);
    return event.prevented;
  };
  return { input, button, attributes, form, nativeDialog, click: () => click(),
    change: () => formListeners.change(), unload,
    submit: (cancelled = false) => documentListeners.submit({ target: form, defaultPrevented: cancelled }),
    restore: () => windowListeners.pageshow() };
}

test('password toggle is enhanced only after initialization and updates accessible state', () => {
  const ui = setup();
  assert.equal(ui.button.hidden, false);
  ui.click();
  assert.equal(ui.input.type, 'text');
  assert.equal(ui.attributes['aria-label'], 'Hide password');
  assert.equal(ui.attributes['aria-pressed'], 'true');
  ui.click();
  assert.equal(ui.input.type, 'password');
  assert.equal(ui.attributes['aria-pressed'], 'false');
});

test('invalid fields receive focus', () => {
  assert.equal(setup({ invalid: true }).input.focused, true);
});

test('reactivation uses native modal and restores form focus on close', () => {
  const ui = setup({ dialog: true });
  assert.equal(ui.nativeDialog.open, true);
  ui.nativeDialog.close();
  assert.equal(ui.input.focused, true);
});

test('warns only for edited data, not successful submission; restores warning on pageshow', () => {
  const ui = setup();
  assert.equal(ui.unload(), false);
  ui.change();
  assert.equal(ui.unload(), true);
  ui.submit();
  assert.equal(ui.unload(), false);
  ui.restore();
  assert.equal(ui.unload(), true);
});

test('cancelled submission does not suppress the unsaved-data warning', () => {
  const ui = setup();
  ui.change();
  ui.submit(true);
  assert.equal(ui.unload(), true);
});

test('retained account data warns immediately after server-side validation', () => {
  assert.equal(setup({ retained: true }).unload(), true);
});
