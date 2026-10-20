// Dependency-free regression checks for the real shared submission script.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

function setup() {
  const listeners = {};
  class Element {
    constructor() {
      this.dataset = {};
      this.attributes = new Map();
      this.classes = new Set();
      this.classList = {
        add: (value) => this.classes.add(value),
        remove: (value) => this.classes.delete(value),
      };
    }
    setAttribute(key, value) { this.attributes.set(key, value); }
    getAttribute(key) { return this.attributes.get(key) ?? null; }
    removeAttribute(key) { this.attributes.delete(key); }
  }
  class Form extends Element {}
  class Button extends Element {
    constructor(form, value) {
      super();
      this.form = form;
      this.name = 'decision';
      this.value = value;
      this.disabled = false;
      this.innerHTML = value;
    }
  }
  const source = fs.readFileSync(path.join(__dirname, '../static/scripts/form-submit-state.js'), 'utf8');
  vm.runInNewContext(source, {
    HTMLFormElement: Form, HTMLButtonElement: Button,
    document: { addEventListener: (name, handler) => { listeners[name] = handler; } },
    window: { addEventListener: (name, handler) => { listeners[name] = handler; } },
  });
  function submit(form, button, prevented = false) {
    const event = { target: form, submitter: button, defaultPrevented: prevented,
      preventDefault() { this.defaultPrevented = true; } };
    listeners.submit(event);
    return event;
  }
  return { Form, Button, submit, restore: () => listeners.pageshow() };
}

for (const value of ['approved', 'rejected']) {
  test(`preserves the successful named submitter: ${value}`, () => {
    const { Form, Button, submit } = setup();
    const form = new Form();
    const button = new Button(form, value);
    assert.equal(submit(form, button).defaultPrevented, false);
    assert.equal(button.disabled, false, 'native disabled buttons lose their name/value');
    assert.equal(button.name, 'decision');
    assert.equal(button.value, value);
    assert.equal(button.getAttribute('aria-disabled'), 'true');
    assert.equal(form.getAttribute('aria-busy'), 'true');
  });
}

test('blocks repeat submissions, including the other decision and implicit Enter', () => {
  const { Form, Button, submit } = setup();
  const form = new Form();
  const approve = new Button(form, 'approved');
  const reject = new Button(form, 'rejected');
  submit(form, approve);
  assert.equal(submit(form, approve).defaultPrevented, true);
  assert.equal(submit(form, reject).defaultPrevented, true);
  assert.equal(submit(form, null).defaultPrevented, true);
  assert.equal(reject.innerHTML, 'rejected');
});

test('pageshow restores state and permits another decision without stale data', () => {
  const { Form, Button, submit, restore } = setup();
  const form = new Form();
  const button = new Button(form, 'approved');
  submit(form, button);
  restore();
  restore();
  assert.equal(button.innerHTML, 'approved');
  assert.equal(button.getAttribute('aria-disabled'), null);
  assert.equal(button.getAttribute('aria-busy'), null);
  assert.equal(form.getAttribute('aria-busy'), null);
  assert.equal(button.classes.size, 0);
  assert.equal(button.dataset.originalLabel, undefined);
  button.value = 'rejected';
  assert.equal(submit(form, button).defaultPrevented, false);
  assert.equal(button.value, 'rejected');
});

test('does not alter opted-out, already-cancelled, or non-button submissions', () => {
  const { Form, Button, submit } = setup();
  const form = new Form();
  const button = new Button(form, 'approved');
  form.dataset.noSubmitState = '';
  submit(form, button);
  delete form.dataset.noSubmitState;
  submit(form, button, true);
  submit(form, null);
  assert.equal(button.innerHTML, 'approved');
  assert.equal(form.getAttribute('aria-busy'), null);
});

test('supports unnamed buttons and leaves other forms independent', () => {
  const { Form, Button, submit } = setup();
  const first = new Form();
  const second = new Form();
  const button = new Button(first, '');
  button.name = '';
  assert.equal(submit(first, button).defaultPrevented, false);
  assert.equal(submit(second, new Button(second, 'approved')).defaultPrevented, false);
});
