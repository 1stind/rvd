const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');

function page(events = []) {
  const context = vm.createContext({ Intl, Date });
  vm.runInContext(readFileSync(require('node:path').join(__dirname, '../app/static/js/events.js'), 'utf8'), context);
  return context.eventsPage(null, events);
}

test('event search combines the entered phrase with open voting filter', () => {
  const view = page([
    { id: 'open', name: 'Kompetisi Foto', description: 'Karya komunitas', is_voting_open: true },
    { id: 'closed', name: 'Kompetisi Foto', description: '', is_voting_open: false },
    { id: 'other', name: 'Debat Pelajar', description: '', is_voting_open: true },
  ]);
  view.eventQuery = '  FOTO  ';
  assert.equal(view.filteredEvents.length, 2);
  view.openOnly = true;
  assert.equal(view.filteredEvents.length, 1);
  assert.equal(view.filteredEvents[0].id, 'open');
  view.eventQuery = 'not found';
  assert.equal(view.filteredEvents.length, 0);
});

test('participant pagination and counts use the filtered results', () => {
  const view = page();
  view.dataPeserta = Array.from({ length: 25 }, (_, index) => ({ id: index, name: `Peserta ${index}`, school: index < 13 ? 'Komunitas Seni' : 'Sekolah Debat' }));
  view.participantQuery = 'seni';
  assert.equal(view.filteredParticipants.length, 13);
  assert.equal(view.participantTotalPages, 2);
  assert.equal(view.paginatedParticipants.length, 12);
  view.nextParticipantPage();
  assert.equal(view.paginatedParticipants.length, 1);
  assert.equal(view.participantDisplayStart, 13);
  assert.equal(view.participantDisplayEnd, 13);
  view.participantQuery = 'unknown';
  view.participantPage = 1;
  assert.equal(view.participantDisplayStart, 0);
  assert.equal(view.participantDisplayEnd, 0);
});
