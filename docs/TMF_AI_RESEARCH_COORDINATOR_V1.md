# TMF AI 研究協調器 V1.0

## 執行順序

1. 讀取已登錄的實驗規格（呼叫端負責先完成 dataset/spec 登錄及人工核准）。
2. Gemini 研究員收到研究問題、實驗 ID、策略版本、資料集 ID/hash、週期及已知資料背景。
3. Python 驗證 Gemini Proposal schema、必要規則及 Experiment ID / Strategy ID 關聯；拒絕任何績效欄位。
4. GPT 反方審查員收到完整 Proposal、Proposal SHA-256、資料集/成本/成交背景。
5. Python 驗證 Review 是否引用同一 Proposal hash、Finding 欄位及 Verdict。
6. 僅 `accept_for_test` 可產生 handoff packet；`revise` / `reject` 會停止。
7. Packet 只表示可交給下一階段 Python 驗證，不會執行回測、不會建立正式績效、不會送出交易。

## 使用方式

```python
from research_engine import (
    build_gemini_from_env, build_openai_from_env, run_research_cycle
)

result = run_research_cycle(
    researcher=build_gemini_from_env(),
    reviewer=build_openai_from_env(),
    experiment_spec=experiment_spec,
    research_question="測試開盤 FVG 延續結構是否具有可重複的日內優勢",
    data_context={"known_limitations": ["TMFR1 是連續序列，不是個別月份合約"]}
)
```

API 金鑰只能由環境變數讀取。呼叫會產生供應商 API 費用，請由操作人員明確啟動。

## 人工控制

協調器不呼叫 approve_experiment，不會自行核准實驗。正式回測前仍需獨立的人工核准與 Python 執行政策。AI 的 accept_for_test 不是策略有效性的證明。

## 限制

- 每個 provider 本輪最多呼叫一次；目前沒有自動重試。
- 目前沒有 token / 成本計量與預算閥值。
- 沒有自動保存原始 prompt 與 provider 原始回應；呼叫端應保存已脫敏的研究 artifact。
- API 呼叫錯誤或 schema 錯誤會中止整個 cycle，不會自動把不完整結果送去回測。
- 本模組沒有交易下單能力。
