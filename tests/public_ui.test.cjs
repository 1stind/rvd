const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function load(file, extra = {}) {
  const context = vm.createContext({ URLSearchParams, console: {error() {}},
    window: { location: {search: ''}, addEventListener() {} },
    setTimeout() {}, ...extra });
  vm.runInContext(fs.readFileSync(file, 'utf8'), context);
  return context;
}

test('live ranking updates preserve participant artwork and new positions', () => {
  const {scoreboard} = load('app/static/js/leaderboard.js');
  const state = scoreboard([{id: 'a', rank: 2}], {live: false});
  state._apply([{team_id: 'a', rank: 1, name: 'Participant', votes: 120,
    logo_url: '/photo.png', photo_url: '/portrait.png'}]);
  assert.equal(state.teams[0].logo_url, '/photo.png');
  assert.equal(state.teams[0].photo_url, '/portrait.png');
  assert.equal(state.teams[0].trend, 'up');
  assert.equal(state.teams[0].votes, 120);
});

test('failed ranking requests show an error and remain retryable', async () => {
  const {eventsPage} = load('app/static/js/events.js', {
    fetch: async () => ({ok:false, status:503})});
  const state = eventsPage({id:'e1'}, []);
  await state.fetchIfNeeded('leaderboard');
  assert.equal(state.error.leaderboard, 'Gagal memuat data');
  assert.equal(state.loadedTabs.leaderboard, undefined);
  assert.equal(state.loading.leaderboard, false);
});
