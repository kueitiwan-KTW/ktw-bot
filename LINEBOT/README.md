# LINE Bot 模組

> KTW Hotel LINE 客服機器人 - 智能化旅館客戶服務系統

---

## 📋 模組概述

LINE Bot 是 KTW Hotel 的智能客服系統,整合 Google Gemini AI、PMS API 和 Gmail API,提供 24/7 自動化客戶服務。

### 核心功能
- ✅ AI 智能對話 (Gemini 2.5 Flash)
- ✅ 訂單查詢 (PMS + Gmail)
- ✅ 當日預訂系統
- ✅ 天氣預報查詢
- ✅ 語音訊息辨識
- ✅ 圖片訂單識別
- ✅ VIP 客戶管理

---

## 🏗️ 技術架構

### 技術棧
- **語言**: Python 3.9+
- **框架**: Flask (LINE Webhook)
- **AI 模型**: Google Gemini 2.5 Flash
- **API 整合**: LINE Messaging API, PMS API, Gmail API, 中央氣象署 API

### 系統架構
```
LINE 用戶
    ↓
LINE Webhook (app.py)
    ↓
HotelBot (bot.py)
    ├→ Gemini AI 對話
    ├→ 訂單查詢 (PMS/Gmail)
    ├→ 當日預訂 (same_day_booking.py)
    ├→ 天氣查詢 (weather_helper.py)
    └→ 對話記錄 (chat_logger.py)
```

---

## 📁 檔案結構

```
LINEBOT/
├── README.md                    ← 本文件
├── CHANGELOG.md                 ← 版本變更記錄
├── persona.md                   ← Bot 人格設定 (程式碼依賴)
├── app.py                       ← Flask Webhook 主程式
├── bot.py                       ← Bot 核心邏輯
├── same_day_booking.py          ← 當日預訂模組
├── pms_client.py                ← PMS API 客戶端
├── gmail_helper.py              ← Gmail 訂單查詢
├── weather_helper.py            ← 天氣查詢
├── chat_logger.py               ← 對話記錄
├── google_services.py           ← Google API 服務
├── line_bot_guide.md            ← LINE Bot 使用指南
└── same_day_booking_guide.md    ← 當日預訂指南
```

---

## 🚀 快速開始

### 環境需求
- Python 3.9+
- LINE Messaging API 帳號
- Google Gemini API Key
- PMS API 存取權限

### 環境變數
在專案根目錄的 `.env` 檔案中設定:

```env
# LINE API
LINE_CHANNEL_ACCESS_TOKEN=your_access_token
LINE_CHANNEL_SECRET=your_channel_secret

# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# 中央氣象署 API
CWA_API_KEY=your_cwa_api_key

# PMS API
PMS_API_URL=http://192.168.8.3:3000
```

### 啟動服務

```bash
# 安裝依賴
pip install -r requirements.txt

# 啟動 Bot
cd LINEBOT
python3 app.py

# 或使用 PM2 (推薦)
pm2 start ecosystem.config.js --only Line-Bot-Py
```

---

## 📚 核心功能說明

### 1. AI 智能對話
- **模型**: Gemini 2.5 Flash
- **知識庫**: `../data/knowledge_base.json`
- **人格設定**: `persona.md`
- **支援格式**: 文字、圖片、語音

### 2. 訂單查詢
- **自動識別**: 5位數以上數字自動觸發查詢
- **圖片識別**: 上傳訂單截圖自動提取編號
- **資料來源**: PMS API (優先) / Gmail API (備用)
- **天氣提醒**: 自動查詢入住日天氣

### 3. 當日預訂
- **服務時間**: 每日 22:00 前
- **流程**: 房型選擇 → 數量確認 → 客人資訊 → 訂單確認
- **支援**: 多房型組合 (如「1間雙人1間三人」)
- **自動升等**: 庫存不足時自動升等

### 4. 語音訊息
- **技術**: Gemini 2.5 Flash 多模態
- **支援語言**: 繁體中文
- **處理**: 自動轉文字後進入對話流程

### 5. VIP 客戶
- **配置**: `vip_users.json`
- **功能**: 自動識別、優先推送、Dashboard 標記

---

## 🔧 開發指南

### 修改 Bot 人格
編輯 `persona.md` 檔案 (⚠️ 不可移動此檔案,程式碼依賴)

### 更新知識庫
編輯 `../data/knowledge_base.json`

### 新增功能
1. 閱讀 [DEVELOPMENT_SOP.md](../docs/DEVELOPMENT_SOP.md)
2. 更新 `bot.py` 或建立新模組
3. 更新 `CHANGELOG.md`
4. 更新本 README

---

## 📊 對話記錄

### 儲存位置
- **對話 LOG**: `../data/chat_logs/{USER_ID}.txt`
- **用戶資料**: `../data/chat_logs/user_profiles.json`
- **系統 LOG**: `../data/chat_logs/server.log`

### 查看對話
```bash
# 查看特定用戶對話
cat ../data/chat_logs/U03943bbf6c3db14367df7a78a1e883e8.txt

# 查看最新對話
ls -lt ../data/chat_logs/*.txt | head -5
```

---

## 🔗 相關文檔

- [CHANGELOG.md](./CHANGELOG.md) - 版本變更記錄
- [line_bot_guide.md](./line_bot_guide.md) - 完整功能說明
- [same_day_booking_guide.md](./same_day_booking_guide.md) - 當日預訂詳細指南
- [persona.md](./persona.md) - Bot 人格設定
- [DEVELOPMENT_SOP.md](../docs/DEVELOPMENT_SOP.md) - 開發標準作業程序

---

## 🐛 故障排除

### Bot 無回應
```bash
# 檢查服務狀態
pm2 list

# 查看錯誤日誌
pm2 logs Line-Bot-Py --err --lines 50

# 重啟服務
pm2 restart Line-Bot-Py
```

### 天氣查詢失敗
檢查 `.env` 中的 `CWA_API_KEY` 是否正確設定 (不要加引號)

### 訂單查詢失敗
1. 檢查 PMS API 連線: `curl http://192.168.8.3:3000/api/health`
2. 檢查 Gmail API 憑證

---

## 📝 版本資訊

- **當前版本**: v1.1.6
- **最後更新**: 2025-12-17
- **維護者**: KTW Hotel IT Team

詳細變更記錄請參閱 [CHANGELOG.md](./CHANGELOG.md)

---

## 🤝 貢獻指南

在進行任何修改前,請:
1. 閱讀 [DEVELOPMENT_SOP.md](../docs/DEVELOPMENT_SOP.md)
2. 確認修改不會破壞現有功能
3. 更新相關文檔
4. 更新 CHANGELOG.md

---

**注意**: `persona.md` 檔案被程式碼直接引用,請勿移動或重命名!
