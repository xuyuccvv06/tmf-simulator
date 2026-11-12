const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const html = fs.readFileSync("trade_journal.html", "utf8");
const start = html.indexOf("function eventVoided(");
const end = html.indexOf("function renderStats(", start);
assert.ok(start >= 0 && end > start, "journal statistics helpers must exist");
const helpers = html.slice(start, end);
const sandbox = {
  db: { events: [] },
  Date, Set, Number
};
vm.createContext(sandbox);
vm.runInContext(helpers + String.fromCharCode(10) + "function tradeEvents(tid) { return db.events.filter(event => event.trade_id === tid); }" + String.fromCharCode(10) + "globalThis.api = { eventVoided, periodBounds, effectiveExitPnl, completedTrades };", sandbox);
const api = sandbox.api;
const event = (entry_id, event_type, extra = {}) => ({
  entry_id, event_type, trade_id: "T1",
  recorded_at: "2026-11-11T03:00:00.000Z",
  context: {}, ...extra
});

test("period boundaries use Monday weeks and calendar periods", () => {
  const now = new Date(2026, 10, 11, 12);
  const week = api.periodBounds("week", now);
  assert.equal(new Date(week.start).getDate(), 9);
  assert.equal(new Date(week.end).getDate(), 16);
  const month = api.periodBounds("month", now);
  assert.equal(new Date(month.start).getDate(), 1);
  assert.equal(new Date(month.end).getMonth(), 11);
  const half = api.periodBounds("half", now);
  assert.equal(new Date(half.start).getMonth(), 6);
  assert.equal(new Date(half.end).getMonth(), 0);
  assert.equal(new Date(half.end).getFullYear(), 2027);
  const year = api.periodBounds("year", now);
  assert.equal(new Date(year.start).getMonth(), 0);
  assert.equal(new Date(year.end).getFullYear(), 2027);
});

test("completed trades include one valid exit and exclude open, duplicate-exit, and voided trades", () => {
  const entry = event("e1", "exit", { context: { realized_pnl_twd: 1200 }, market_timestamp: "2026-11-10T02:00:00.000Z" });
  const open = event("e2", "entry", { trade_id: "T2" });
  const dup1 = event("e3", "exit", { trade_id: "T3", context: { realized_pnl_twd: 10 } });
  const dup2 = event("e4", "exit", { trade_id: "T3", context: { realized_pnl_twd: 20 } });
  const voidExit = event("e5", "exit", { trade_id: "T4", context: { realized_pnl_twd: -300 } });
  const voidMarker = event("v5", "void", { trade_id: "T4", target_entry_id: "e5" });
  sandbox.db.events = [entry, open, dup1, dup2, voidExit, voidMarker];
  const trades = api.completedTrades();
  assert.equal(trades.length, 1);
  assert.equal(trades[0].p, 1200);
  assert.equal(trades[0].ms, Date.parse(entry.market_timestamp));
});

test("latest valid P&L correction is used; voiding it restores prior effective value", () => {
  const exit = event("exit1", "exit", { context: { realized_pnl_twd: 100 } });
  const c1 = event("c1", "amendment", { target_entry_id: "exit1", recorded_at: "2026-11-11T03:01:00Z", context: { amendment_kind: "pnl_correction", corrected_realized_pnl_twd: -50 } });
  const c2 = event("c2", "amendment", { target_entry_id: "exit1", recorded_at: "2026-11-11T03:02:00Z", context: { amendment_kind: "pnl_correction", corrected_realized_pnl_twd: 250 } });
  const voidC2 = event("v2", "void", { target_entry_id: "c2" });
  const latest = api.effectiveExitPnl(exit, [exit, c1, c2]);
  assert.equal(latest.p, 250);
  assert.equal(latest.unit, "twd");
  const restored = api.effectiveExitPnl(exit, [exit, c1, c2, voidC2]);
  assert.equal(restored.p, -50);
  assert.equal(restored.unit, "twd");
});

test("voiding a void marker restores the original event", () => {
  const v1 = event("v1", "void", { target_entry_id: "exit1" });
  const v2 = event("v2", "void", { target_entry_id: "v1" });
  assert.equal(api.eventVoided("exit1", [v1]), true);
  assert.equal(api.eventVoided("exit1", [v1, v2]), false);
  assert.equal(api.eventVoided("v1", [v1, v2]), true);
});

test("completed trade uses latest corrected P&L and ignores voided correction", () => {
  const exit = event("exit1", "exit", { context: { realized_pnl_twd: 100 } });
  const correction = event("c1", "amendment", { target_entry_id: "exit1", context: { amendment_kind: "pnl_correction", corrected_realized_pnl_twd: -25 } });
  const voidCorrection = event("v1", "void", { target_entry_id: "c1" });
  sandbox.db.events = [exit, correction, voidCorrection];
  assert.equal(api.completedTrades()[0].p, 100);
});
