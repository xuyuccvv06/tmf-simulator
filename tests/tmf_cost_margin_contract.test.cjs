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

test('browser dynamic slippage uses only completed bars before the fill bar', () => {
  const body = functionBody('slippageBreakdown');
  assert.match(body, /priorBars=bars\.slice/);
  assert.match(body, /previousRange/);
  assert.doesNotMatch(body, /bar\.(h|l|v)/);
  assert.match(functionBody('estimatedSlippage'), /slippageBreakdown\(bar\)\.total/);
});


test('simulation records and journal display itemized fees, tax and slippage components', () => {
  assert.match(html, /entry_commission_twd:entryCommission/);
  assert.match(html, /exit_commission_twd:exitCommission/);
  assert.match(html, /entry_tax_twd:entryTax/);
  assert.match(html, /exit_tax_twd:exitTax/);
  assert.match(html, /entry_slippage_range_points:entrySlip\.range/);
  assert.match(html, /exit_slippage_low_volume_points:exitSlip\.low_volume/);
  assert.match(html, /gross_before_slippage_points:grossBeforeSlippagePoints/);
  assert.match(journal, /交易成本明細/);
  assert.match(journal, /進場手續費/);
  assert.match(journal, /出場期交稅/);
  assert.match(journal, /進場滑價組成/);
  assert.match(journal, /最終淨利/);
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
  assert.ok(margins.records.length >= 16);
  assert.ok(margins.records.some(r => r.effective_date === '2025-01-22' && r.initial === 17700));
  assert.ok(margins.records.some(r => r.effective_date === '2025-02-06' && r.initial === 16100));
  const dates = margins.records.map(r => r.effective_date);
  assert.deepEqual(dates, [...dates].sort());
  for (const row of margins.records) {
    assert.ok(row.effective_date >= margins.period_start && row.effective_date <= margins.period_end);
    assert.ok(Number.isInteger(row.initial) && Number.isInteger(row.maintenance) && Number.isInteger(row.settlement));
    assert.ok(row.initial >= row.maintenance && row.maintenance >= row.settlement);
    assert.ok(row.source.startsWith('https://www.taifex.com.tw/'));
  }
  assert.equal(new Set(dates).size, dates.length);
});

test('historical margin is automatically applied by replay trading date and manual lookup remains available', () => {
  assert.match(html, /id="applyHistoricalMargin" disabled/);
  assert.match(html, /function applyHistoricalMargin\(\)/);
  assert.match(html, /function applyHistoricalMarginForReplayDate\(date\)/);
  assert.match(html, /r\.effective_date<date/);
  assert.match(html, /account\.initial_margin_per_contract=Number\(row\.initial\)/);
  assert.match(html, /account\.maintenance_margin_per_contract=Number\(row\.maintenance\)/);
  assert.match(html, /function saveMarginSettings\(\)/);
});

test('historical margin data loads before replay initialization and manual controls are wired', () => {
  assert.match(html, /\$\("lookupHistoricalMargin"\)\.onclick=lookupHistoricalMargin/);
  assert.match(html, /\$\("applyHistoricalMargin"\)\.onclick=applyHistoricalMargin/);
  assert.match(html, /async function init\(\)\{\s*try\{\s*await loadHistoricalMarginData\(\)/);
});

test('new simulation accounts start with the confirmed baseline trading costs', () => {
  assert.match(html, /commission_per_side:10,base_slippage:1,range_slippage:0,low_volume_penalty:0,dynamic_slippage:false/);
});


test('TMF execution prices and order levels respect the 1-point minimum tick', () => {
  assert.match(html, /const TMF_TICK_SIZE=1/);
  assert.match(html, /function snapPrice\(price\)/);
  assert.match(functionBody('adverseFill'), /snapPrice\(price\+sign\*slip\)/);
  assert.match(html, /adverseFill\(fill,side,bar,'entry'\)/);
  assert.match(html, /total=Math\.ceil\(\(rawTotal-1e-10\)\/TMF_TICK_SIZE\)\*TMF_TICK_SIZE/);
  assert.match(functionBody('readDistance'), /Number\.isSafeInteger\(value\)/);
  assert.match(functionBody('applyManagedStop'), /Number\.isSafeInteger\(next\)/);
  assert.match(functionBody('applyManagedTarget'), /Number\.isSafeInteger\(next\)/);
  assert.match(functionBody('updateTradeUI'), /Math\.round\(u\)\.toLocaleString/);
  assert.match(functionBody('updateTradeUI'), /Math\.round\(lastTrade\.points\)\.toLocaleString/);
});
