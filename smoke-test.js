
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL;
const HEADERS = { 'Accept': 'application/json' };

export const options = {
  stages: [
    { duration: '30s', target: 5 },
    { duration: '30s', target: 20 },
    { duration: '30s', target: 50 },
    { duration: '1m', target: 100 },
    { duration: '15s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
  },
};

export default function () {
  const events = http.get(
    `${BASE_URL}/api/v1/events`,
    { headers: HEADERS, tags: { endpoint: 'events' } }
  );

  check(events, {
    'events status 2xx': (r) => r.status >= 200 && r.status < 300,
  });

  const leaderboard = http.get(
    `${BASE_URL}/api/v1/leaderboard`,
    { headers: HEADERS, tags: { endpoint: 'leaderboard' } }
  );

  check(leaderboard, {
    'leaderboard status 2xx': (r) => r.status >= 200 && r.status < 300,
  });

  sleep(1);
}