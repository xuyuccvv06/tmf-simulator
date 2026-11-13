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

test('multiple CSV datasets are fingerprinted and keep independent replay state', () => {
  assert.match(html, /id="datasetSelector"/);
  assert.match(html, /id="datasetUploadFile"/);
  assert.match(html, /async function loadReplayDatasetFromJournalDB\(datasetId\)/);
  assert.match(html, /market_timestamp:x\.t,trading_date:x\.d/);
  assert.match(html, /function selectedDatasetStorageKey\(\)/);
  assert.match(html, /saveReplayState\(false\);saveAccount\(\);/);
  assert.match(html, /if\(SIM_MODE==="formal"&&formalRunLock\)/);
  assert.match(html, /localStorage\.setItem\(selectedDatasetStorageKey\(\),datasetId\)/);
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
  assert.match(html, /id="cancelPendingOrder"/);
  assert.match(html, /function cancelPendingEntryOrder\(\)/);
  assert.match(html, /使用者手動取消/);
  assert.match(html, /bar\.l<=order\.limitPrice&&bar\.h>=order\.limitPrice/);
  assert.match(html, /限價委託未成交：下一根 K 線未觸及/);
  assert.match(html, /type==="limitBuy"\|\|order\.type==="limitSell"/);
});

test('daily 4 percent loss and 5/9/12 loss warnings enforce the entry gate', () => {
  assert.match(html, /dayStartEquity\)\*0\.04/);
  assert.match(html, /equity-replayRisk\.dayStartEquity-\(replayRisk\.dayDeposits\|\|0\)/);
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
  assert.match(html, /applyHistoricalMarginForReplayDate\(nextDate\)/);
});

test('daily profit giveback is tracked for reporting but does not block new trades', () => {
  assert.match(html, /replayRisk\.dayPeakNet=Math\.max/);
  assert.match(html, /replayRisk\.profitGiveback=Math\.max/);
  assert.match(html, /replayRisk\.maxProfitGiveback=Math\.max/);
  assert.match(html, /當日獲利回吐/);
  assert.doesNotMatch(html, /if\(replayRisk\.(profitGiveback|maxProfitGiveback)/);
});

test('broker-specific intraday risk liquidation is not guessed without a confirmed broker contract', () => {
  assert.match(html, /永豐期貨風控模擬：日盤風險指標低於 25% 時觸發代為沖銷/);
  assert.match(html, /TMF 夜盤屬豁免商品/);
  assert.match(html, /function brokerRiskIndicatorPercent\(bar\)/);
  assert.match(html, /return equity\/account\.initial_margin_per_contract\*100/);
  assert.match(html, /ratio>=25/);
  assert.match(html, /replayRisk\.brokerRiskTriggered=true/);
  assert.match(html, /evaluateBrokerIntradayRisk\(current\)/);
  assert.match(html, /marginLiquidationPending&&position&&isTMFDaySession\(nextBar\)/);
});

test('margin calls persist to the next trading-day noon and are included in snapshots', () => {
  assert.match(html, /function evaluateMarginCall\(bar\)/);
  assert.match(html, /isTMFDaySession\(bar\)&&bar\.t\.slice\(11,16\)==="13:45"/);
  assert.match(html, /isTMFDaySession\(last\)&&last\.t\.slice\(11,16\)==="13:45"/);
  assert.match(html, /dates\.find\(d=>d>bar\.d\)/);
  assert.match(html, /deadline:next\?next\+" 12:00":null/);
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
  assert.match(html, /recordFormalDecision\("position_closed"/);
  assert.match(html, /recordFormalDecision\("position_stop_modified"/);
  assert.match(html, /recordFormalDecision\("position_target_modified"/);
  assert.match(html, /if\(revealed>=bars\.length\)sealFormalDecisionLog\(\)/);
});

test('formal mode cumulative stats use only revealed completed exits from the active dataset', () => {
  assert.match(html, /formalPerformancePanel/);
  assert.match(html, /replay_dataset_id:replayDatasetId/);
  assert.match(html, /Date\.parse\(e\.market_timestamp\)<=cutoff/);
  assert.match(html, /e\.context\?\.replay_dataset_id===replayDatasetId/);
});

test('portable backups include formal decision audit and lock metadata', () => {
  assert.match(html, /formalDecisionLog,formalRunLock/);
  assert.match(html, /incoming\.checksum===formalDecisionChecksum\(incoming\.events\)/);
  assert.match(html, /payload\.formalRunLock\.startDate===replayStartDate/);
});

test('portable backup export includes all replay sessions for the active dataset', () => {
  assert.match(html, /function validateReplayBackupEnvelope\(s\)/);
  assert.match(html, /if\(!item\|\|typeof item\.key!=="string"\|\|!item\.key\.startsWith\(prefix\)\)continue/);
  assert.match(html, /!validateReplayBackupEnvelope\(item\.snapshot\)/);
  assert.match(html, /payload\.datasetId!==replayDatasetId/);
});

test('portable backup import preserves an existing valid snapshot instead of overwriting it', () => {
  assert.match(html, /const existingRaw=localStorage\.getItem\(key\)/);
  assert.match(html, /existing\.checksum===snapshot\.checksum/);
  assert.match(html, /snapshot\.key=key;snapshot\.checksum=replayChecksum\(snapshot\)/);
});

test('existing journals are not cleared and pruning is limited to feature-owned backup keys', () => {
  assert.doesNotMatch(html, /localStorage\.clear\(/);
  assert.match(html, /x\.key\.startsWith\(prefix\)/);
  assert.match(html, /tmf\.behaviourJournal\."\+SIM_MODE/);
  assert.match(html, /tmf\.sim\.account\."\+SIM_MODE/);
});
