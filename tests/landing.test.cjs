const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({ Date });
vm.runInContext(readFileSync('app/static/js/landing.js', 'utf8'), context);

test('discovery combines case-insensitive name search with open voting filter', () => {
  const page = context.landingPage([
    { name: 'Komunitas Kreatif', is_voting_open: true },
    { name: 'Komunitas Kampus', is_voting_open: false },
    { name: 'Fotografi', is_voting_open: true },
  ]);
  page.query = ' KOMUNITAS ';
  assert.equal(page.filteredEvents.length, 2);
  page.openOnly = true;
  assert.equal(page.filteredEvents.length, 1);
  assert.equal(page.filteredEvents[0].name, 'Komunitas Kreatif');
  page.query = 'missing';
  assert.equal(page.filteredEvents.length, 0);
  page.query = '';
  assert.equal(page.filteredEvents.length, 2);
});

test('unscheduled events have an honest identity instead of an invented date', () => {
  const page = context.landingPage();
  assert.equal(page.dateMonth({}), 'Event');
  assert.equal(page.dateDay({}), 'RVD');
  assert.equal(page.filteredEvents.length, 0);
});

test('featured event countdown supports scheduled and expired events', () => {
  const future = context.eventCountdown({closes_at: new Date(Date.now() + 2 * 86400000).toISOString()});
  future._updateCountdown();
  assert.ok(Number(future.countdown.days) >= 1);
  const invalid = context.eventCountdown({closes_at: 'invalid'});
  invalid._updateCountdown();
  assert.equal(invalid.countdown.days, '00');
});
