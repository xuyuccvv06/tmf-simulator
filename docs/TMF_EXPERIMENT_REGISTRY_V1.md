# TMF 回測實驗管理器 V1.0

## 目的

把回測規格與回測結果分開保存，確保任何績效數字都能追溯到固定資料、策略、參數、成本模型、成交模型及程式版本。

## Experiment ID

Experiment ID 由規格內容的 canonical JSON SHA-256 前 20 位產生。資料集、策略版本、參數、成本模型、成交模型或程式版本任一變動，都會形成不同實驗 ID。

## 實驗規格必要內容

- 已接受的 Dataset ID 與資料 SHA-256。
- 商品及週期。
- Strategy ID、Strategy Version、參數。
- 成本模型：往返成本點數、滑價點數及版本。
- 成交模型 ID 與版本。
- 程式碼 revision。
- 研究假設。

## 審核與執行狀態

新實驗預設為 `pending_human_approval` 與 `registered`。在使用者/研究負責人明確核准前，不允許附加正式回測結果。此版不會由 AI 自行核准。

## 結果保存

結果另存為 `<experiment_id>.result.json`，並計算結果 JSON SHA-256。既有結果若內容不同，拒絕覆寫。不同參數或成本設定必須建立新實驗，不得改寫舊規格。

## 使用方式

```bash
python scripts/create_experiment.py --registry build/datasets/registry.json --root build/experiments --dataset-id ds_<registered-id> --strategy-id opening_fvg --strategy-version 0.1.0 --parameters-json '{"min_gap_points":5}' --cost-model-json '{"round_trip_cost_points":5.3,"slippage_points":1.0,"version":"v1"}' --execution-model-json '{"model_id":"next_bar_open","version":"1.0"}' --code-revision <git-commit-sha> --hypothesis "測試開盤 FVG 延續"
```

## 目前限制

- 此版以 JSON 檔案保存，尚非多使用者資料庫。
- 核准需由人工流程完成；AI 只能提出建議與反方審查。
- 目前 simulator 是獨立交易基礎模組，不代表完整期交所撮合、保證金、持倉組合或換月模型。

## 研究規範

正式績效報告必須引用 Experiment ID、Dataset ID、資料 SHA-256、策略版本、成本模型及成交模型。未通過資料驗證或未經人工核准的結果不得標示為正式結論。
