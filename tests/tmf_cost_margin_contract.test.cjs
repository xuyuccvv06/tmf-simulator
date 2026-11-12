const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const journal = fs.readFileSync(path.join(__dirname, '..', 'trade_journal.html'), 'utf8');
const margins = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'tmf_margin_history_2024-2025.json'), 'utf8'));

function functionBody(name) {
  const start = html.indexOf('function ' + name + '(');
  assert.notEqual(start, -1, 'missing function ' + name);
  const brace = html.indexOf('{', start);
  let depth = 0, quote = null, escaped = false;
  for (let i = brace; i < html.length; i++) {
    const ch = html[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === '\\\\') escaped = true;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === '`') { quote = ch; continue; }
    if (ch === '{') depth++;
    if (ch === '}' && --depth === 0) return html.slice(brace + 1, i);
  }
  throw new Error('unclosed function ' + name);
}

test('take-profit limit exits do not receive adverse market slippage', () => {
  const body = functionBody('finishPosition');
  assert.match(body, /execution==='market'\?adverseFill/);
  assert.match(body, /execution==='market'&&exitBar/);
  assert.match(html, /finishPosition\(bar\.o,bar\.t,'跳空停利','limit'\)/);
  assert.match(html, /finishPosition\(p\.takeProfit,bar\.t,'停利','limit'\)/);
});

test('unrealized P&L estimates include closing slippage, both-side commission and futures tax', () => {
  const body = functionBody('accountUnrealized');
  assert.match(body, /adverseFill\(last\.c,position\.side,last\)/);
  assert.match(body, /commission=2\*c\.commission_per_side/);
  assert.match(body, /tax=\(position\.entry\+mark\)\*10\*0\.00002/);
});

test('cost setting rendering does not overwrite a field while the user is editing it', () => {
  const body = functionBody('renderCostSettings');
  assert.match(body, /document\.activeElement!==el/);
  assert.match(body, /document\.activeElement!==toggle/);
});

test('journal exit events store net TWD P&L and an auditable cost breakdown', () => {
  assert.match(html, /realized_pnl_twd:Number\.isFinite\(costBreakdown\.net_twd\)/);
  assert.match(html, /cost_breakdown:costBreakdown/);
  assert.match(journal, /typeof exit\.context\?\.realized_pnl_twd==="number"/);
});

test('TMF official margin history is ordered, bounded and contains all three margin fields', () => {
  assert.equal(margins.contract, 'TMF');
  assert.equal(margins.period_start, '2024-07-29');
  assert.equal(margins.period_end, '2025-12-31');
  assert.ok(margins.records.length >= 14);
  const dates = margins.records.map(r => r.effective_date);
  assert.deepEqual(dates, [...dates].sort());
  for (const row of margins.records) {
    assert.ok(row.effective_date >= margins.period_start && row.effective_date <= margins.period_end);
    assert.ok(Number.isInteger(row.initial) && Number.isInteger(row.maintenance) && Number.isInteger(row.settlement));
    assert.ok(row.initial >= row.maintenance && row.maintenance >= row.settlement);
    assert.match(row.source, /^https:\\/\\/www\\.taifex\\.com\\.tw\\//);
  }
  assert.equal(new Set(dates).size, dates.length);
});

test('historical margin apply is explicit and does not overwrite settings on page load', () => {
  assert.match(html, /id="applyHistoricalMargin" disabled/);
  assert.match(html, /function applyHistoricalMargin\(\)/);
  assert.match(html, /loadHistoricalMarginData\(\)/);
  assert.match(html, /function saveMarginSettings\(\)/);
});
