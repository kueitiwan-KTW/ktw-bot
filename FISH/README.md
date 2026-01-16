# FISH - OTA 後台自動化 POC

> **F**etch **I**nventory & **S**ync **H**otel
>
> 使用 Playwright 自動化操作 OTA 後台，監控房況並同步房價庫存。

---

## 🎯 功能

- ✅ 保持長期登入 (Session 持久化)
- ✅ 定時輪詢房況
- ✅ 自動偵測 Session 過期並重新登入
- ✅ 支援 Agoda YCS 和 Booking.com Extranet

---

## 📁 專案結構

```
FISH/
├── README.md
├── requirements.txt
├── config.example.yaml     # 設定範本
├── config.yaml             # 實際設定 (不要 commit)
├── sessions/               # Session 檔案 (不要 commit)
│   ├── agoda_session.json
│   └── booking_session.json
├── src/
│   ├── __init__.py
│   ├── main.py             # 主程式入口
│   ├── session_manager.py  # Session 管理
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── base.py         # 平台基底類別
│   │   ├── agoda.py        # Agoda YCS 操作
│   │   └── booking.py      # Booking.com 操作
│   └── utils/
│       ├── __init__.py
│       └── logger.py       # 日誌工具
└── tests/
    └── test_login.py       # 測試腳本
```

---

## 🚀 快速開始

### 1. 安裝依賴

```bash
cd FISH
pip install -r requirements.txt
playwright install chromium
```

### 2. 設定

```bash
cp config.example.yaml config.yaml
# 編輯 config.yaml 填入帳號密碼
```

### 3. 首次登入 (手動)

```bash
python -m src.session_manager --platform agoda --login
```

### 4. 啟動監控

```bash
python -m src.main
```

---

## ⚠️ 注意事項

1. **Session 檔案機密**：`sessions/` 目錄已加入 `.gitignore`
2. **TOS 風險**：此為 POC，正式使用請考慮官方 API
3. **頻率限制**：預設每 5 分鐘輪詢一次，避免太頻繁
