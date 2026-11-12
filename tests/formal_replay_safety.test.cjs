const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

test('replay snapshots are isolated by mode, dataset and replay session', () => {
  assert.match(html, /REPLAY_STATE_PREFIX="tmf\.replay\.state\."\+SIM_MODE/);
  assert.match(html, /function replayStateKey\(date,mode,stamp\)/);
  assert.match(html, /function datasetAccountKey\(date,mode\)/);
  assert.match(html, /datasetId:replayDatasetId/);
  assert.match(html, /s\.datasetId!==replayDatasetId/);
  assert.match(html, /s\.session!==date/);
  assert.match(html, /s\.checksum===replayChecksum\(s\)/);
});

test('manual save, rolling versions, recovery selection and pause lifecycle are wired', () => {
  assert.match(html, /id="saveReplayNow"/);
  assert.match(html, /id="restoreReplayBackup"/);
  assert.match(html, /REPLAY_BACKUP_INDEX/);
  assert.match(html, /item\.session===snapshot\.session&&item\.replayMode===snapshot\.replayMode\?3:2/);
  assert.match(html, /x\.key\.startsWith\(prefix\)/);
  assert.match(html, /已安全保存，可以離開/);
  assert.match(html, /prompt\("選擇要恢復的有效備份/);
  assert.match(html, /document\.addEventListener\("visibilitychange"/);
  assert.match(html, /window\.addEventListener\("pagehide"/);
});

test('limit entries only evaluate the next revealed bar and expire after a miss', () => {
  assert.match(html, /expiresAfterNextBar:true/);
  assert.match(html, /bar\.l<=order\.limitPrice&&bar\.h>=order\.limitPrice/);
  assert.match(html, /限價委託未成交：下一根 K 線未觸及/);
  assert.match(html, /type==="limitBuy"\|\|order\.type==="limitSell"/);
});

test('daily 4 percent loss and 5/9/12 loss warnings enforce the entry gate', () => {
  assert.match(html, /dayStartEquity\)\*0\.04/);
  assert.match(html, /replayRisk\.lossStreak>=5/);
  assert.match(html, /replayRisk\.lossStreak>=9/);
  assert.match(html, /replayRisk\.lossStreak>=12/);
  assert.match(html, /replayRisk\.blockedDate=current\.d/);
  assert.match(html, /\["buy","sell","limitBuy","limitSell"\]\.includes\(pendingOrder\.type\)/);
  assert.match(html, /風控已封鎖今日新增進場/);
});

test('historical margin is loaded before replay and applied by after-close effective date', () => {
  assert.match(html, /await loadHistoricalMarginData\(\)/);
  assert.match(html, /function applyHistoricalMarginForReplayDate\(date\)/);
  assert.match(html, /r\.effective_date<date/);
  assert.match(html, /account\.initial_margin_per_contract=Number\(row\.initial\)/);
  assert.match(html, /account\.maintenance_margin_per_contract=Number\(row\.maintenance\)/);
});

test('margin calls persist to the next trading-day noon and are included in snapshots', () => {
  assert.match(html, /function evaluateMarginCall\(bar\)/);
  assert.match(html, /dates\.find\(d=>d>bar\.d\)/);
  assert.match(html, /deadline:next\+" 12:00"/);
  assert.match(html, /保證金追繳期限屆滿強制平倉/);
  assert.match(html, /marginCallStatus/);
  assert.match(html, /account,marginLiquidationPending,marginCall,replayRisk/);
});

test('formal test requires a locked configuration and seals the append-only decision log at completion', () => {
  assert.match(html, /function lockFormalRun\(\)/);
  assert.match(html, /replayStartDate!=="2024-07-29"/);
  assert.match(html, /commission_per_side:10,base_slippage:1,range_slippage:0,low_volume_penalty:0,dynamic_slippage:false/);
  assert.match(html, /function recordFormalDecision\(eventType,details=\{\}\)/);
  assert.match(html, /function sealFormalDecisionLog\(\)/);
  assert.match(html, /formalRunLock\.completedAt/);
  assert.match(html, /正式盲測已完成並封存/);
  assert.match(html, /recordFormalDecision\("entry_order_submitted"/);
  assert.match(html, /recordFormalDecision\("entry_order_filled"/);
  assert.match(html, /recordFormalDecision\("entry_order_expired"/);
  assert.match(html, /if\(revealed>=bars\.length\)sealFormalDecisionLog\(\)/);
});

test('formal mode cumulative stats use only revealed completed exits from the active dataset', () => {
  assert.match(html, /formalPerformancePanel/);
  assert.match(html, /replay_dataset_id:replayDatasetId/);
  assert.match(html, /Date\.parse\(e\.market_timestamp\)<=cutoff/);
  assert.match(html, /e\.context\?\.replay_dataset_id===replayDatasetId/);
});

test('portable backup import preserves an existing valid snapshot instead of overwriting it', () => {
  assert.match(html, /const existingRaw=localStorage\.getItem\(key\)/);
  assert.match(html, /existing\.checksum===snapshot\.checksum/);
  assert.match(html, /snapshot\.key=key;snapshot\.checksum=replayChecksum\(snapshot\)/);
});

test('existing journals are not cleared and pruning is limited to feature-owned backup keys', () => {
  assert.doesNotMatch(html, /localStorage\.clear\(/);
  assert.match(html, /old\.key\.startsWith\(REPLAY_STATE_PREFIX/);
  assert.match(html, /tmf\.behaviourJournal\."\+SIM_MODE/);
  assert.match(html, /tmf\.sim\.account\."\+SIM_MODE/);
});
