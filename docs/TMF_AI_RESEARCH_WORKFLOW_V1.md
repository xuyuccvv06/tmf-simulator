# TMF AI 策略研究工作流 V1.0

## 角色分工

- Gemini 研究員：提出可證偽的市場假設、策略規則、參數搜尋範圍及資料需求。
- GPT 反方審查員：針對同一份提案 SHA-256，檢查前視偏誤、倖存者偏誤、過度擬合、交易成本、成交可行性、樣本選擇及失效條件。
- Python：只負責確定性資料驗證、回測執行及統計計算，不把 AI 的文字推論當作績效事實。
- 人工研究負責人：核准正式實驗；AI 不可自行核准。

## 提案契約

研究員必須提供 experiment_id、strategy_id/version、hypothesis、market_mechanism、entry_rules、exit_rules、invalidation_rules 及 parameter_search_space。提案不得帶入勝率、淨點數或回測績效欄位。

## 反方審查契約

GPT 必須引用 proposal_sha256，確保審查的是完全相同的提案。每項 finding 必須包含 issue、evidence_or_test 及 severity（low/medium/high/critical）。

Verdict:
- accept_for_test：可進入 Python 的資料與執行條件驗證，不代表策略有效。
- revise：退回研究員修正。
- reject：停止該提案。

含 critical finding 的審查不可標示 accept_for_test。

## Python 交接

只有 accept_for_test 且 experiment_id 一致的提案與實驗規格才能產生 handoff packet。Packet 只表示 ready_for_python_validation；它不會自行執行回測，也不會產生績效。

## 稽核與版本

每個 artifact 使用 canonical JSON SHA-256。Review 必須綁定 proposal hash；handoff packet 保存 proposal、review、experiment spec 三者雜湊。修改任一文件後，必須重新審查並產生新的 packet。

## 使用方式

```bash
python scripts/create_research_packet.py \
  --proposal proposal.json \
  --review adversarial_review.json \
  --experiment-spec experiment.json \
  --output research_packet.json
```

## 安全邊界

- 不呼叫 AI API、不傳送資料到外部服務。
- 不將自由文字中的績效數字視為回測結果。
- 不把「允許進入測試」描述為「策略通過」。
- 正式結果仍需通過資料稽核、成交模型、成本模型、樣本外驗證及人工審核。
