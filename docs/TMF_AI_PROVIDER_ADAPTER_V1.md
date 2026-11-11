# TMF AI Provider Adapter V1.0

## 支援角色

- Gemini：研究員，預設模型名稱由 `TMF_GEMINI_MODEL` 指定，預設 `gemini-2.5-flash`。
- OpenAI：反方審查員，預設模型名稱由 `TMF_OPENAI_MODEL` 指定，預設 `gpt-4.1-mini`。

模型名稱與端點可由環境變數覆寫；實際可用模型取決於供應商帳戶權限及 API 狀態。

## 安全設定

僅從環境變數讀取：
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`

可選設定：
- `TMF_GEMINI_MODEL`
- `TMF_OPENAI_MODEL`
- `TMF_GEMINI_ENDPOINT`
- `TMF_OPENAI_ENDPOINT`
- `TMF_AI_TIMEOUT_SECONDS`（預設 45 秒）

禁止將 API 金鑰寫入程式碼、JSON 設定、測試資料、GitHub commit 或 Actions log。正式部署應使用部署平台的 Secret Manager；GitHub Actions 若日後需要呼叫 API，才由管理者在 GitHub Secrets 設定，不可把 secrets 複製到 repository。

## 介面行為

- Gemini 使用 generateContent 並要求 JSON MIME type。
- OpenAI 使用 Chat Completions JSON Object response format。
- 兩者均使用明確 timeout，限制回應最大 1 MB。
- HTTP 錯誤不輸出 request headers 或 API key。
- 回應必須可解析為 JSON object，否則拒絕。
- Provider adapter 不會自動重試、不會儲存 prompt/response、不會觸發回測或批准實驗。

## 本版驗證範圍

CI 使用 mock HTTP 回應測試 adapter，不會連接外部 API、不會消耗 Token，也不會產生費用。真正連線需在受控執行環境設定有效 API keys，並由操作者明確啟動。

## 目前尚未完成

- 真正 API 呼叫與帳戶權限確認。
- Token 用量、費用估算及預算上限。
- Rate limit/backoff 重試策略。
- API 輸出接入 proposal/review schema 的端到端流程。
- 人工確認後的安全執行工作台。
