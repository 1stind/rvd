const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

for (const [page, handler] of [['transactions', 'loadTransactions'], ['audit_logs', 'loadAuditLogs']]) {
  test(`${page} filters can invoke their page handler`, () => {
    const html = fs.readFileSync(`app/templates/pages/admin_${page}.html`, 'utf8');
    const context = vm.createContext({window: {adminEscapeHTML: value => String(value ?? "")}, localStorage: {getItem: () => ''},
      document: {getElementById: () => ({value: '', classList: {add() {}, remove() {}}})},
      fetch: () => new Promise(() => {})});
    vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
    assert.equal(typeof context.window[handler], 'function');
  });
}

test('mobile navigation manages focus, Escape, and desktop resizing', () => {
  const listeners = {};
  const ready = [];
  const document = {querySelectorAll: () => [], addEventListener: (name, fn) => {if (name === 'DOMContentLoaded') ready.push(fn); else if (name === 'keydown') (listeners.keys ||= []).push(fn); else listeners[name] = fn;}};
  function element() {
    const classes = new Set();
    return {offsetParent: {}, attributes: {}, focus() {document.activeElement = this;},
      setAttribute(name, value) {this.attributes[name] = value;},
      classList: {contains: name => classes.has(name), toggle(name, active) {
        if (active) classes.add(name); else classes.delete(name);
      }}};
  }
  const sidebar = element(), overlay = element(), menu = element();
  const close = element(), last = element();
  sidebar.querySelector = () => close;
  sidebar.querySelectorAll = () => [close, last];
  document.body = element();
  document.getElementById = id => ({sidebar, overlay, 'admin-menu': menu})[id];
  const media = {matches: true, addEventListener: (_, fn) => {listeners.resize = fn;}};
  const window = {matchMedia: () => media};
  vm.runInNewContext(fs.readFileSync('app/static/js/admin.js', 'utf8'), {window, document});
  ready.forEach(fn => fn());
  listeners.keydown = event => listeners.keys.forEach(fn => fn(event));
  assert.equal(sidebar.inert, true);
  window.toggleSidebar();
  assert.equal(sidebar.inert, false);
  assert.equal(menu.attributes['aria-expanded'], 'true');
  assert.equal(document.activeElement, close);
  let prevented = false;
  listeners.keydown({key: 'Tab', shiftKey: true, preventDefault() {prevented = true;}});
  assert.equal(prevented, true);
  assert.equal(document.activeElement, last);
  listeners.keydown({key: 'Escape'});
  assert.equal(sidebar.inert, true);
  assert.equal(document.activeElement, menu);
  media.matches = false;
  listeners.resize();
  assert.equal(sidebar.inert, false);
  assert.equal(overlay.classList.contains('hidden'), true);
});
