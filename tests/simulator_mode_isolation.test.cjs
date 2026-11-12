const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const main = fs.readFileSync("index.html", "utf8");
const journal = fs.readFileSync("trade_journal.html", "utf8");

function accountForMode(mode, initialStorage = {}) {
  const storage = new Map(Object.entries(initialStorage));
  const localStorage = {
    getItem: key => storage.has(key) ? storage.get(key) : null,
    setItem: (key, value) => storage.set(key, String(value))
  };
  const start = main.indexOf("const MODE_PARAM=");
  const end = main.indexOf("let account=loadAccount()", start);
  assert.ok(start >= 0 && end > start, "mode-aware account loader must exist");
  const code = main.slice(start, end) + "let account=loadAccount(); globalThis.result={SIM_MODE,ACCOUNT_KEY,account};";
  const sandbox = { URLSearchParams, location: { search: mode === "formal" ? "?mode=formal" : "?mode=practice" }, localStorage, Date, Number };
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox);
  return { ...sandbox.result, storage };
}

test("legacy account migrates to practice mode without changing its balance or ledger", () => {
  const legacy = { version: 1, balance: 60140, initial_margin_per_contract: 50000, maintenance_margin_per_contract: 40000, ledger: [{ type: "initial_capital", amount: 50000, recorded_at: "2026-11-12T00:00:00.000Z" }, { type: "deposit", amount: 10000, recorded_at: "2026-11-12T00:01:00.000Z" }] };
  const result = accountForMode("practice", { "tmf.sim.account.v1": JSON.stringify(legacy) });
  assert.equal(result.SIM_MODE, "practice");
  assert.equal(result.account.balance, 60140);
  assert.equal(result.account.initial_margin_per_contract, 50000);
  assert.equal(JSON.parse(result.storage.get("tmf.sim.account.practice.v1")).balance, 60140);
});

test("formal mode starts with an independent NT$50,000 account and does not copy practice funds", () => {
  const legacy = { version: 1, balance: 99999, initial_margin_per_contract: 50000, maintenance_margin_per_contract: 40000, ledger: [] };
  const result = accountForMode("formal", { "tmf.sim.account.v1": JSON.stringify(legacy), "tmf.sim.account.practice.v1": JSON.stringify(legacy) });
  assert.equal(result.SIM_MODE, "formal");
  assert.equal(result.account.balance, 50000);
  assert.equal(result.account.initial_margin_per_contract, 0);
  assert.equal(result.storage.has("tmf.sim.account.formal.v1"), true);
  assert.equal(JSON.parse(result.storage.get("tmf.sim.account.practice.v1")).balance, 99999);
});

test("mode switch and navigation preserve the selected mode", () => {
  assert.match(main, /location\.href="\.\/index\.html\?mode="\+\$\("modeSelector"\)\.value/);
  assert.match(main, /journalNav"\)\.href="\.\/trade_journal\.html\?mode="\+SIM_MODE/);
  assert.match(journal, /location\.href="\.\/trade_journal\.html\?mode="\+\$\("modeSelector"\)\.value/);
  assert.match(journal, /replayNav"\)\.href="\.\/index\.html\?mode="\+SIM_MODE/);
});

test("legacy journal migrates only into practice and journal namespaces are separate", () => {
  assert.match(main, /tmf\.behaviourJournal\.\"\+SIM_MODE\+\"\.v1/);
  assert.match(main, /SIM_MODE==="practice"/);
  assert.match(journal, /KEY="tmf\.behaviourJournal\.\"\+SIM_MODE\+\"\.v1"/);
  assert.match(journal, /if\(!s&&SIM_MODE==="practice"\)/);
});

test("backup exports carry mode and imports reject cross-mode restores", () => {
  assert.match(journal, /mode:SIM_MODE/);
  assert.match(journal, /backupMode!==SIM_MODE/);
  assert.match(journal, /localStorage\.setItem\(ACCOUNT_KEY,JSON\.stringify\(b\.account\)\)/);
});
