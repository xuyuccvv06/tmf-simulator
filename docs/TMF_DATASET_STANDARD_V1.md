# TMF OHLCV 標準資料集 V1.0

## 目的

建立單一、可重現、可追溯的資料介面，供回測引擎、Gemini 研究員、GPT 反方審查與 Python 計算共用。

## 標準欄位

`timestamp, trading_date, product_id, timeframe, open, high, low, close, volume`

- 時區：Asia/Taipei。來源無時區時間戳保留原始鐘面時間，不做時差平移。
- 價格：指數點。
- 週期：每份資料必須明確標示 1m 或 5m，不可混檔。
- `trading_date`：原樣保留來源值，不以日曆日期自行改寫。
- `product_id`：TMFR1 仍標記為連續合約，不得冒充個別到期月份。

## 轉換流程

`scripts/standardize_csv.py` 會：

1. 計算原始來源 SHA-256。
2. 嚴格檢查標題、時間排序、OHLCV 合法性。
3. 對應標準欄位並輸出固定欄序。
4. 保留每一列；不刪列、不補值、不插值、不合成。
5. 輸出 manifest：來源/輸出 SHA-256、列數、首末時間、商品、週期、時區及轉換聲明。

來源檔與標準輸出路徑不得相同，避免覆蓋原始備份。

## 目前資料狀態

- 已有：TMFR1 5 分 K，79,689 列。
- 尚未匯入：獨立 1 分 K 資料。
- 不會由 5 分 K 反推或合成 1 分 K。
- 目前 5 分 K 的標準化輸出由 GitHub Actions artifact 保存；來源 CSV 不會被修改。

## 驗收條件

- 自動測試通過。
- 原始 CSV 嚴格讀取成功。
- 標準化後列數與來源一致。
- Manifest 的來源與輸出 SHA-256 可重算。
- `row_filtering=false`、`gap_filling=false`、`synthetic_rows=0`。
- 任何一列格式錯誤都讓流程失敗，不默默跳過。

## 尚未宣稱完成

此標準化流程不是交易所認證，也不會自動修正連續合約換月偏差。合約月份識別與實際換月成本仍需個別月份合約資料。
