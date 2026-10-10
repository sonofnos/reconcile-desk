import http from "k6/http";
import { check } from "k6";

// Hits the transaction search endpoint against the 2M-row seeded dataset
// (see backend/ledger/management/commands/seed_benchmark.py). Run with:
//   k6 run scripts/load_test.js
// against a gunicorn-served instance, not `manage.py runserver` (the dev
// server is single-threaded and would measure Django's dev server, not
// the application).
export const options = {
  scenarios: {
    sustained_load: {
      executor: "constant-arrival-rate",
      rate: 1000,
      timeUnit: "1s",
      duration: "20s",
      preAllocatedVUs: 150,
      maxVUs: 400,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<200"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8234";
const TYPES = ["deposit", "withdrawal", "transfer"];

export default function () {
  const type = TYPES[Math.floor(Math.random() * TYPES.length)];
  const page = Math.floor(Math.random() * 20) + 1;
  const res = http.get(`${BASE_URL}/api/transactions/search/?type=${type}&page=${page}`);
  check(res, { "status is 200": (r) => r.status === 200 });
}
