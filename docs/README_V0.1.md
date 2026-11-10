# TMF Research Platform V0.1

此為增量式研究引擎基礎，不取代原有回放網站。請保留根目錄既有 README、HTML、CSV 與歷史版本。

## 安裝與測試

```bash
python -m pip install -e '.[test]'
pytest
```

## 重要限制
目前 simulator 為研究骨架，需先補足保守成交規則、逐筆報告、交易時段與換月處理，再進行正式策略回測。
