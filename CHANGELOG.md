# KTW Hotel System - Changelog

> 本文件記錄整個專案的重要變更。各模組的詳細變更請參閱各自的 CHANGELOG。

## 模組 CHANGELOG 連結

- [LINE Bot](./LINEBOT/CHANGELOG.md) - LINE 客服機器人
- [Admin Dashboard](./KTW-admin-web/CHANGELOG.md) - 管理後台
- [Backend API](./KTW-backend/CHANGELOG.md) - 後端 API 服務
- [PMS API](./pms-api/CHANGELOG.md) - PMS 資料庫 API

---

## [1.9.9] - 2025-12-22
### 🔧 Bot 模組化重構
- **LINE Bot**: `bot.py` 從 1821 行減至 817 行（-55%）
- **新增模組**: `prompts/` 獨立管理 System Prompt
- **重構**: `check_order_status` 和 `create_same_day_booking` 改為 Wrapper，邏輯移至 Handler

#### 詳細模組變更
- [LINE Bot (v1.9.9)](./LINEBOT/CHANGELOG.md#199---2025-12-22) - 完整重構說明

---

## [1.9.8] - 2025-12-22
### ✨ 訂單查詢系統優化 Phase 1
- **LINE Bot**: 實作「AI + Helper 雙層驗證」架構，解決訂單編號被誤判為電話/時間的問題
- **新增 Helper**: `IntentDetector`（6 個方法）、`order_helper`（4 個時間方法）
- **重構 Handler**: `OrderQueryHandler` 整合新 Helper，提升意圖判斷準確度

#### 詳細模組變更
- [LINE Bot (v1.9.8)](./LINEBOT/CHANGELOG.md#198---2025-12-22) - Phase 1 完整說明

---

## [1.9.6] - 2025-12-21
### ✨ 修正查無訂單時住客資料同步失效
- **LINE Bot**: 實作查詢失敗時的強制同步邏輯，確保 LINE 姓名與需求能正確傳遞至後端。
- **Admin**: 確保 OTA 編號匹配之住客卡片能顯示完整資訊。

## [1.9.5] - 2025-12-21

### ✨ 結構重構與故障排除
- **架構優化**: 建立 `order_helper.py` 統一處理電話格式、OTA 編號與資訊同步邏輯 (SSOT)。
- **故障排除**: 修復 Admin Web (`App.vue`) 語法錯誤並恢復服務。
- **資料完整性**: 完成 `bot.py` 暫存資料自動匹配與 SQLite 同步整合。

## [1.9.1] - 2025-12-21

### 🐛 OTA 訂單查詢修復與完整 LOG 系統
- **查詢優化**: PMS API 調整為 OTA 模糊匹配優先，修復 `1671721966` 無法匹配 `RMAG1671721966` 的問題
- **LOG 系統**: 建立完整的三層日誌系統（Bot 內部 / API 調用 / PMS 伺服器），支援問題追溯
- **暫存機制**: 訂單查不到時自動暫存客人資料，查到後自動匹配補齊

#### 詳細模組變更
- [LINE Bot (v1.9.1)](./LINEBOT/CHANGELOG.md#191---2025-12-21) - LOG 系統、暫存機制
- [PMS API (v1.9.1)](./pms-api/CHANGELOG.md#191---2025-12-21) - 查詢順序、API Logger
- [LOG 系統指南](./docs/LOG_GUIDE.md) - 新增日誌查詢指南

---

## [1.9.0] - 2025-12-21

### 🧠 智慧日期查詢與 AI 意圖判斷
- **AI 意圖判斷**: VIP 查詢從硬編碼關鍵字升級為 Gemini AI 意圖分類，能理解口語表達
- **日期查詢擴展**: 支援昨日房況、特定日期查詢（12/25、25號）、完整月份統計
- **房況計算修正**: 正確區分「維修房 (R)」與「瑕疵房 (OOS)」，修正住房率計算

#### 詳細模組變更
- [LINE Bot (v1.9.0)](./LINEBOT/CHANGELOG.md#190---2025-12-21) - AI 意圖判斷、日期查詢、房況修正
- [PMS 文檔更新](./pms-api/PMS-DATABASE-REFERENCE.md) - 新增瑕疵房 vs 維修房說明

---

## [1.8.5] - 2025-12-21

### 🏗️ VIP 服務處理器結構重構與 Prompt 統一
- **重構優化**: 整合 `VIPServiceHandler` 內部重複的 PMS 查詢邏輯。
- **標準化 Prompt**: 統一 Vision 與 Chat 的系統指令，達成專業稱呼與語言自動適應。
- **健壯性提升**: 強化針對 Gemini SDK 的異常處理，提供更友善的管理層錯誤引導。

#### 詳細模組變更
- [LINE Bot (v1.8.5)](./LINEBOT/CHANGELOG.md#185---2025-12-21) - VIP Handler 重構

---

## [1.8.0] - 2025-12-21

### 📈 營運報表數據精準化與功能擴展
- **報表精準化**: 修正房間數計算邏輯（改用 `room_numbers`），呈現「筆 / 間」格式。
- **月報查詢**: LINE Bot 新增「本月房況」預測功能。
- **PMS API 升級**: 遠端 Server 新增動態日期查詢端點 (checkin-by-date)，支援跨日數據存取。
- **部署標準化**: 建立 `deploy-pms-api` 工作流，統一使用 NSSM 管理遠端服務。

#### 詳細模組變更
- [LINE Bot (v1.8.0)](./LINEBOT/CHANGELOG.md#180---2025-12-21) - 月報功能、數據修正
- [PMS API (v1.9.0)](./pms-api/CHANGELOG.md#190---2025-12-21) - 動態日期查詢、NSSM 管理

---

## [1.7.5] - 2025-12-21

### 🏗️ VIP 服務模組化與狀態機 (Modular FSM) 導入
- **架構解耦**: 將 VIP 邏輯從 `bot.py` 完整抽離至 `VIPServiceHandler`，解決代碼臃腫問題。
- **狀態管理**: 導入有限狀態機 (FSM)，支援「發送任務 -> 等待圖片」的跨對話狀態記憶。
- **靈活性提升**: 獨立的 Handler 結構讓未來新增 VIP 功能不需要動到核心路由。

#### 詳細模組變更
- [LINE Bot (v1.7.5)](./LINEBOT/CHANGELOG.md#175---2025-12-21) - Modular FSM 重構

---

---

## [1.5.0] - 2025-12-19

### 🚀 全系統同步、穩定性與 UI 佈局重構
> 本次更新為全模組同步升級，解決了核心資料庫連線問題，並大幅優化了 Bot 流程與後台顯示介面。

#### 重點更新內容
- **資料庫維修**: 成功修復 Oracle PMS 實例故障，恢復全系統即時訂單調研能力。
- **兩階段確認**: LINE Bot 導入強制確認邏輯，解決 AI 過度自信導致的錯誤同步。
- **UI 佈局更新**: Admin Dashboard 重新設計卡片佈局，提升資訊密度並優化變色標識。
- **穩定性修復**: 徹底解決 Bot 流程中頻發的 `KeyError` 與資料路徑配置錯誤。

#### 詳細模組變更
- [LINE Bot (v1.4.10)](./LINEBOT/CHANGELOG.md#1410---2025-12-19) - 流程優化、Bug 修復
- [Backend API (v1.1.1)](./KTW-backend/CHANGELOG.md#111---2025-12-19) - 資料匹配、Display Name 整合
- [Admin Web (v1.3.0)](./KTW-admin-web/CHANGELOG.md#v130-2025-12-19) - 佈局重構、變色標識
- [PMS API (v1.8.0)](./pms-api/CHANGELOG.md#180---2025-12-19) - Oracle 服務重啟

---

## [1.4.2] - 2025-12-18

### ⚡ 系統穩定性與 API 優化 (LINE Bot v1.4.3 / PMS API v1.7.1)
- **穩定性修復**：修復 LINE Bot 的核心崩潰問題 (IndentationError & NoneType crash)，大幅提升訂單查詢功能的穩定性。
- **API 簡化**：優化 PMS API 原有的 `/search` 端點，移除冗餘的 `id` 參數，使介面更簡潔且易於維護。
- **邏輯對齊**：確保 LINE Bot 與 PMS API 在處理組合式查詢（姓名/電話/單號）時的邏輯同步，提升查詢精準度。

### 詳細變更
- [LINE Bot CHANGELOG](./LINEBOT/CHANGELOG.md#143---2025-12-18)
- [PMS API CHANGELOG](./pms-api/CHANGELOG.md#171---2025-12-18)

---

## [1.4.1] - 2025-12-18

### 🛡️ 隱私攔截與精準查詢升級 (LINE Bot v1.4.2)
- **安全防護**: 實作日期格式攔截器，防止客人僅提供入住日期就查詢到訂單詳情。
- **組合查詢**: 支援「單號 + 姓名/電話」組合驗證，確保資料揭露的安全性與精準度。
- **PMS 優先**: 強化 PMS API 資料調用的絕對優先權，優化 Gmail 備援搜尋邏輯。

## [1.4.0] - 2025-12-18

### ✨ 新功能：長期住客追蹤與 A.I. 櫃檯共用備註系統
- **資料持久化**: 實作基於 SQLite 的 `guest_supplements` 表，支援跨時效資料存儲。
- **共享備註 (Shared Memo)**: 新增可供 A.I. 寫入與櫃檯人員編輯的共用區域，支援即時自動儲存。
- **跨平台同步**: LINE Bot 收集的電話與需求會自動同步至本地資料庫，並即時反應於 Admin 面板。

## [1.3.1] - 2025-12-18

### ✨ 訂單模組強化與 Bug 修復
- **LINE Bot (v1.3.1)**: 修復模組化後的連線與資料存取錯誤，優化路由攔截邏輯，確保訂單號能被精準處理。
- **詳情請見**: [LINEBOT/CHANGELOG.md](./LINEBOT/CHANGELOG.md)

## [1.3.0] - 2025-12-18

### 核心更新: 全面導入 Gemini 3.0 Flash
- **LINE Bot (v1.3.0)**: 將所有 AI 模型（對話、影像識別、隱私驗證）全面升級至 Gemini 3.0 Flash (Preview)。
- **知識庫強化**: 掃描歷史對話，新增關於發票統編、房型更換補差價、團體入住、寵物費、遊覽車停車等 7 項 FAQ 條目。
- **Notion AI Organizer**: 升級文檔整理與指令系統至 Gemini 3.0 Flash，提升分析速度與建議品質。
- **技術提升**: 顯著提升 OCR 文字識別準確率與視覺推理能力。

### 詳細變更
- [LINE Bot CHANGELOG](./LINEBOT/CHANGELOG.md#130---2025-12-18)

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
