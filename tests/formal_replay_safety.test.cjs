const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');

test('replay snapshots are mode- and dataset-scoped and validate before restore', () => {
  assert.match(html, /REPLAY_STATE_PREFIX="tmf\.replay\.state\.\+SIM_MODE/);
  assert.match(html, /function replayStateKey\(date,mode\)/);
  assert.match(html, /function validateReplayState\(s\)/);
  assert.match(html, /function restoreReplayState\(date,mode\)/);
  assert.match(html, /s\.mode!==SIM_MODE/);
  assert.match(html, /s\.session!==date/);
});

test('manual save, multiple backup index and page lifecycle pause are wired', () => {
  assert.match(html, /id="saveReplayNow"/);
  assert.match(html, /id="restoreReplayBackup"/);
  assert.match(html, /REPLAY_BACKUP_INDEX/);
  assert.match(html, /已安全保存，可以離開/);
  assert.match(html, /document\.addEventListener\("visibilitychange"/);
  assert.match(html, /window\.addEventListener\("pagehide"/);
});

test('limit entries only evaluate the next revealed bar and expire after a miss', () => {
  assert.match(html, /expiresAfterNextBar:true/);
  assert.match(html, /bar\.l<=order\.limitPrice&&bar\.h>=order\.limitPrice/);
  assert.match(html, /限價委託未成交：下一根 K 線未觸及/);
  assert.match(html, /type==="limitBuy"\|\|order\.type==="limitSell"/);
});

test('daily 4 percent loss and 12-loss streak block new entries and cancel entry orders', () => {
  assert.match(html, /dayStartEquity\)\*0\.04/);
  assert.match(html, /replayRisk\.lossStreak>=12/);
  assert.match(html, /replayRisk\.blockedDate=current\.d/);
  assert.match(html, /\["buy","sell","limitBuy","limitSell"\]\.includes\(pendingOrder\.type\)/);
  assert.match(html, /風控已封鎖今日新增進場/);
});

test('existing account and behaviour journal keys are not deleted or cleared by replay backup code', () => {
  assert.doesNotMatch(html, /localStorage\.(removeItem|clear)\(/);
  assert.match(html, /tmf\.behaviourJournal\.\+SIM_MODE/);
  assert.match(html, /tmf\.sim\.account\.\+SIM_MODE/);
});
