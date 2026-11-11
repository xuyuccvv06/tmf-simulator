# TMF Strategy DSL V1.0

## 原則

策略以 JSON 宣告，不接受 Python、JavaScript、SQL、eval 或任意 expression。Compiler 僅允許白名單欄位、指標、運算子與風控參數。

## V1 支援

- 時間週期：1m、5m（策略宣告必須與資料集週期一致；執行入口目前由操作者負責確認）。
- 方向：long、short、both。
- 原始欄位：open、high、low、close、volume。
- 衍生欄位：range_points、body_points。
- 指標：SMA、volume_sma。
- 條件運算子：gt、gte、lt、lte、eq。
- 進場條件：all / any。
- 風控：固定 stop_points、target_points。

## 執行語意

- 使用完成的訊號 K 棒判斷條件。
- 訊號時間戳交給既有 simulator，下一根 K 棒開盤進場。
- SMA 暖機完成前不產生訊號。
- V1 每個交易日期、每個方向最多一筆訊號，避免過度重複進場。
- 停損停利及滑價沿用既有 baseline simulator 的保守規則。

## 不支援（不可假裝已完成）

- FVG / HH-HL-LH-LL / liquidity sweep 等結構辨識。
- 動態停損、移動停利、分批出場。
- 同一方向多筆持倉、組合保證金與爆倉。
- 真實期交所撮合、排隊、部分成交及換月處理。
- 交易時段、夜盤跨日 session calendar 自動綁定。
- 多時間框架同步。
- 策略最佳化與樣本外驗證。

## 範例

```json
{
  "dsl_version": "1.0",
  "strategy_id": "close_above_sma",
  "strategy_version": "0.1.0",
  "timeframe": "5m",
  "side": "long",
  "indicators": {
    "trend": {"type": "sma", "source": "close", "period": 20}
  },
  "entry": {
    "all": [
      {"left": {"indicator": "close"}, "operator": "gt", "right": {"indicator": "trend"}}
    ],
    "any": []
  },
  "risk": {"stop_points": 20, "target_points": 40}
}
```

## 警告

Strategy DSL V1 是最小可執行規則子集，不是完整市場結構語言。任何結果只代表該 DSL 及目前 simulator 的行為，不能直接外推為真實交易績效。
