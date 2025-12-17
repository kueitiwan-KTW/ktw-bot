# KTW Admin Dashboard - 版本歷史

## v1.1.2 (2025-12-17)

### ✨ 新功能
- **已 KEY 訂單自動匹配驗證**
  - 按下「已 KEY」時，後端自動與 PMS 今日入住名單進行匹配
  - 匹配邏輯：電話號碼後 9 碼相同
  - **匹配成功**：訂單從列表中消失（已完成）
  - **匹配失敗**：訂單狀態變為「KEY 錯」，顯示橘色標籤與「重新匹配」按鈕
- **列表排序優化**
  - 優先順序：KEY 錯 (Mismatch) > 待入住 (Pending) > 已入住 (Checked In) > 已取消 (Cancelled)
  - 已 KEY 成功 (Checked In) 的訂單默認隱藏，保持列表整潔
- **批量處理優化**
  - `markAllAsKeyed` 支援批量處理 Pending、Interrupted 和 Mismatch 狀態的訂單

### 🎨 UI 改進
- 新增 `group-status-mismatch` CSS 樣式（橘色脈衝效果）
- 新增 `mismatch-btn-sm` 按鈕樣式
- 調整未入住/已取消訂單的視覺呈現

### 📝 修改的文件
- `src/App.vue` - 狀態判定、排序邏輯、API 串接
- `src/style.css` - 新增狀態樣式
- `package.json` - 版本號更新 (1.1.1 → 1.1.2)

---

## v1.1.1 (2025-12-16)

### 🐛 Bug 修復
- **客人卡片展開連動問題**
  - 修復點擊一個客人卡片時，其他卡片框架也被撐開的問題
  - 根本原因：CSS Grid 默認 `align-items: stretch` 導致同行項目高度同步
  - 解決方案：在 `.guest-cards-list` 添加 `align-items: start`

### 🧹 代碼清理
- 移除所有調試代碼（console.log、[NEW VERSION] 標記）
- 移除 GuestCard 的 onMounted 調試 hook
- 清理展開狀態管理邏輯

### 📝 修改的文件
- `src/style.css` - CSS Grid 修復
- `src/App.vue` - 清理調試代碼
- `src/components/GuestCard.vue` - 移除 onMounted
- `package.json` - 版本號更新 (1.1.0 → 1.1.1)

---

## v1.1.0 (2025-12-15)

### ✨ 新功能
- **真實 PMS API 數據整合**
  - 四格區塊（今日入住、今日退房、住房率、空房數）改用真實 PMS API 數據
  - 取代之前的假數據

- **30 秒倒數計時器**
  - 顯示下次自動更新的倒數時間

### ⚡ 性能優化
- **差異化更新頻率**
  - 服務狀態：5 秒
  - PMS 統計：15 秒
  - 入住客人列表：30 秒
  - 房況：15 秒

### 🎨 UI 改進
- 修正 tooltip 房間瑕疵紀錄排版
- 四格區塊平均分配寬度（每個 25%）
- 新增 `GuestCard.vue` 元件（客人資訊卡片）

### 📝 修改的文件
- `src/App.vue` - 主要邏輯更新
- `src/components/GuestCard.vue` - 新增元件
- `src/style.css` - 樣式更新
- `vite.config.js` - 配置調整
- `package.json` - 版本號更新 (1.0.x → 1.1.0)

---

## v1.0.2 (2025-12-14)

### ✨ Dashboard 優化
- 優化儀表板佈局
- 完善客人資訊卡片顯示
- PMS 數據整合

---

## v1.0.1 (2025-12-13)

### ✨ 初始功能
- Admin Dashboard 基礎架構
- PMS 整合與 UI 優化

---

## 版本命名規則

遵循 [Semantic Versioning](https://semver.org/)：
- **主版本 (X)**：重大架構變更或不兼容的 API 修改
- **次版本 (Y)**：新增功能，向後兼容
- **修訂版本 (Z)**：Bug 修復和小改進
