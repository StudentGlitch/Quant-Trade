import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const AUTH_TOKEN = __ENV.AUTH_TOKEN || "";

export const errorRate = new Rate("errors");
export const latencyTrend = new Trend("latency_ms");

const headers = AUTH_TOKEN
  ? { Authorization: `Bearer ${AUTH_TOKEN}` }
  : {};

export const options = {
  scenarios: {
    smoke: {
      executor: "ramping-arrival-rate",
      startRate: 1,
      timeUnit: "1s",
      preAllocatedVUs: 20,
      maxVUs: 50,
      stages: [
        { target: 2, duration: "2m" },
        { target: 5, duration: "3m" },
      ],
      exec: "smoke",
    },
    baseline: {
      executor: "ramping-arrival-rate",
      startRate: 2,
      timeUnit: "1s",
      preAllocatedVUs: 30,
      maxVUs: 80,
      stages: [
        { target: 6, duration: "3m" },
        { target: 10, duration: "10m" },
      ],
      exec: "baseline",
      startTime: "5m",
    },
    stress: {
      executor: "ramping-arrival-rate",
      startRate: 4,
      timeUnit: "1s",
      preAllocatedVUs: 40,
      maxVUs: 120,
      stages: [
        { target: 12, duration: "4m" },
        { target: 20, duration: "10m" },
      ],
      exec: "stress",
      startTime: "18m",
    },
    soak: {
      executor: "constant-arrival-rate",
      rate: 8,
      timeUnit: "1s",
      duration: "60m",
      preAllocatedVUs: 30,
      maxVUs: 80,
      exec: "soak",
      startTime: "32m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000", "p(99)<2000"],
    errors: ["rate<0.01"],
  },
};

function hitEndpoints(ticker, year) {
  const root = http.get(`${BASE_URL}/`, { headers });
  const reports = http.get(`${BASE_URL}/api/v1/reports/${ticker}`, { headers });
  const live = http.get(`${BASE_URL}/api/v1/ticker/${ticker}/live`, { headers });
  const score = http.get(`${BASE_URL}/api/v1/scoring/${ticker}/${year}`, { headers });

  const responses = [root, reports, live, score];
  for (const res of responses) {
    latencyTrend.add(res.timings.duration);
    errorRate.add(res.status >= 500);
    check(res, { "status below 500": (r) => r.status < 500 });
  }
}

const tickers = ["BBCA", "TLKM", "BMRI", "BBRI"];
const years = [2022, 2023, 2024];

export function smoke() {
  hitEndpoints("BBCA", 2023);
  sleep(1);
}

export function baseline() {
  const ticker = tickers[Math.floor(Math.random() * tickers.length)];
  const year = years[Math.floor(Math.random() * years.length)];
  hitEndpoints(ticker, year);
  sleep(Math.random() * 1.5);
}

export function stress() {
  const ticker = tickers[Math.floor(Math.random() * tickers.length)];
  const year = years[Math.floor(Math.random() * years.length)];
  hitEndpoints(ticker, year);
  sleep(Math.random() * 0.5);
}

export function soak() {
  const ticker = tickers[Math.floor(Math.random() * tickers.length)];
  const year = years[Math.floor(Math.random() * years.length)];
  hitEndpoints(ticker, year);
  sleep(1);
}
