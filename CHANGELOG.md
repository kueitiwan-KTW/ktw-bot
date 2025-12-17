# KTW Hotel System - Changelog

> 本文件記錄整個專案的重要變更。各模組的詳細變更請參閱各自的 CHANGELOG。

## 模組 CHANGELOG 連結

- [LINE Bot](./LINEBOT/CHANGELOG.md) - LINE 客服機器人
- [Admin Dashboard](./KTW-admin-web/CHANGELOG.md) - 管理後台
- [Backend API](./KTW-backend/CHANGELOG.md) - 後端 API 服務
- [PMS API](./pms-api/CHANGELOG.md) - PMS 資料庫 API

---

## [1.2.0] - 2025-12-17

### 整合更新: A.I. 當日預訂與自動驗證
- **LINE Bot (v1.2.0)**: 當日預訂邏輯重構，支援多房型 AI 解析與主動確認。
- **Admin Web (v1.1.2)**: 新增已 KEY 訂單「自動匹配驗證」功能，支援 KEY 錯狀態顯示與重新匹配。
- **Backend API (v1.0.1)**: 支援 PMS 電話號碼自動匹配邏輯。
- **PMS API**: 新增 mismatch 狀態記錄端點。

### 詳細變更
- [LINE Bot CHANGELOG](./LINEBOT/CHANGELOG.md#120---2025-12-17)
- [Admin Web CHANGELOG](./KTW-admin-web/CHANGELOG.md#v112-2025-12-17)
- [Backend API CHANGELOG](./KTW-backend/CHANGELOG.md#101---2025-12-17)

---

## [1.1.6] - 2025-12-17

### LINE Bot
- **修復**: 天氣查詢功能 (環境變數引號問題)
- **改善**: 錯誤處理機制 (完善 LOG 記錄)
- **新增**: 天氣資訊增強 (降雨機率、體感溫度)
- 詳見: [LINEBOT/CHANGELOG.md](./LINEBOT/CHANGELOG.md#116---2025-12-17)

---

## [1.1.5] - 2025-12-15

### LINE Bot
- **新增**: 語音訊息辨識功能 (Voice to Text)
- 詳見: [LINEBOT/CHANGELOG.md](./LINEBOT/CHANGELOG.md#115---2025-12-15)

---

## [1.1.1] - 2025-12-16

### Admin Dashboard
- **修復**: 客人卡片展開連動問題
- **清理**: 移除調試代碼
- 詳見: [KTW-admin-web/CHANGELOG.md](./KTW-admin-web/CHANGELOG.md#v111-2025-12-16)

---

## [1.1.0] - 2025-12-15

### Admin Dashboard
- **新增**: 真實 PMS API 數據整合
- **新增**: 30 秒倒數計時器
- **優化**: 差異化更新頻率
- 詳見: [KTW-admin-web/CHANGELOG.md](./KTW-admin-web/CHANGELOG.md#v110-2025-12-15)

### LINE Bot
- **新增**: 重新開始對話功能
- **新增**: 早餐資訊自動判斷
- **新增**: 房型對照表獨立管理
- **改進**: 訂單來源判斷邏輯優化
- **升級**: AI 模型 (Gemini 2.5 Flash)
- 詳見: [LINEBOT/CHANGELOG.md](./LINEBOT/CHANGELOG.md#110---2025-12-11)

---

## [1.0.1] - 2025-12-10

### 初始版本
- LINE Bot 基本功能
- PMS API 整合
- Admin Dashboard
- Gmail API 整合
- 天氣預報功能

---

## 版本命名規則

遵循 [Semantic Versioning](https://semver.org/):
- **主版本 (X)**: 重大架構變更或不兼容的 API 修改
- **次版本 (Y)**: 新增功能,向後兼容
- **修訂版本 (Z)**: Bug 修復和小改進
