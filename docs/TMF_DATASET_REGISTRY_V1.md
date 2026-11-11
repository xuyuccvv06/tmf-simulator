# TMF 資料集登錄管理器 V1.0

## Dataset ID

標準化資料集以輸出 CSV 的 SHA-256 前 16 位建立內容定址 ID：`ds_<16 hex>`。相同位元組內容會得到相同 ID；資料內容改變會得到不同 ID。

## 登錄流程

`scripts/register_dataset.py` 重新讀取 CSV 與 manifest，驗證：

- SHA-256 與 manifest 相符。
- 欄位名稱及欄位順序完全符合 canonical schema。
- 時間戳嚴格遞增且不混用有時區/無時區格式。
- OHLCV 數值有限且合法。
- 單一商品、單一週期。
- 列數、首末時間、商品與週期與 manifest 相符。
- Manifest 聲明未刪列、未補值、未合成資料。

通過後狀態為 `accepted`。驗證失敗直接拒絕登錄，不提供自動修復。

## Registry 規則

- JSON registry 採 append-only。
- 相同 Dataset ID 重複登錄視為冪等，不新增重複記錄。
- 相同內容若被不同 ID 表示，拒絕登錄。
- 不允許靜默覆寫既有記錄。

## 目前資料

TMFR1 5 分 K 由 CI 每次從原始 CSV 重新標準化、重新驗證並登錄；標準 CSV、manifest、registry 一起保存為 workflow artifact。

目前只有 5 分 K；1 分 K 尚未匯入。TMFR1 仍是連續序列，不能當成個別到期月份合約。

## 限制

此版 registry 是 GitHub Actions 執行產物，不是跨工作執行的永久資料庫。每次 CI 會從受版本控制的來源重新建置 registry。未來若要保存多份使用者上傳資料及跨執行版本，需要持久化資料庫或物件儲存。
