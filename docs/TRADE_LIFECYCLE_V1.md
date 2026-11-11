# 逐筆交易生命週期管理 V1

## 目的
把交易者自行記錄的事前觀察、進場、持倉管理、出場及事後回顧，依 opaque trade_id 串成同一條事件時間線。這是紀錄管理，不是交易策略規則。

## 事件流程
- `pre_trade`：可有多筆，必須在 entry 之前
- `entry`：每個 trade_id 一筆
- `management`：可有多筆，需在 entry 後、exit 前
- `exit`：每個 trade_id 一筆
- `post_trade`：需在 exit 後，最多一筆

可保留尚未完成的交易紀錄；系統只標示缺少哪些階段，不會自行補造事件。一般盤面觀察仍使用獨立 observation，不強制歸屬某筆交易。

## API
- `new_trade_id()`：產生不帶策略意義的識別碼
- `append_trade_event(...)`：驗證事件關聯與行政順序後追加保存
- `get_trade_timeline(...)`：依追加順序取得單筆交易事件
- `list_trade_summaries(...)`：產生中性摘要及未完成狀態

## 邊界
- 不判斷交易方向正確與否。
- 不推導或預設 FVG、HH/HL、流動性掃除等數學規則。
- 不用事件紀錄順序替代市場時間；每筆事件仍保留 recorded_at 與 market_timestamp。
- 目前 JSONL 為單一程序追加檔案；多使用者並行寫入、資料庫交易鎖與 UI 編輯尚未包含。
