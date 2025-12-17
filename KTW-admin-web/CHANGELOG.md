# KTW Admin Dashboard - 版本歷史

## v1.1.2 (2025-12-17)

### ✨ 新功能：已 KEY 訂單自動匹配驗證

#### 核心邏輯 (Frontend)
**檔案**: `src/App.vue`

1. **狀態計算與排序** (L197-220)
   - 新增 `hasMismatch` 狀態檢查
   - 更新 `groupStatus` 優先順序：`mismatch > pending > checked_in > cancelled`
   - 實作排序邏輯：KEY 錯訂單置頂，已 KEY 訂單過濾隱藏

2. **API 整合** (L261-282)
   - 修改 `markAsKeyed()` 函數，處理 Backend 返回的 `mismatch` 狀態
   - 延長 API timeout 至 10 秒（因需查詢 PMS）
   - 新增錯誤處理：匹配失敗時刷新列表顯示 KEY 錯狀態

3. **批量處理優化** (L313-323)
   - 更新 `markAllAsKeyed()` 支援 `mismatch` 狀態
   - 一次處理大訂單下所有 `pending`、`interrupted`、`mismatch` 項目

#### UI 樣式 (CSS)
**檔案**: `src/style.css`

1. **KEY 錯狀態標籤** (L1670-1685)
   ```css
   .group-status-mismatch {
     color: #ff9800;
     background: rgba(255, 152, 0, 0.2);
     animation: pulse 1.5s infinite;
   }
   ```

2. **重新匹配按鈕** (L1687-1700)
   ```css
   .mismatch-btn-sm {
     background: linear-gradient(135deg, #ff9800, #f57c00);
   }
   ```

3. **訂單高亮** (L1702-1706)
   - KEY 錯訂單左側橘色邊框 + 淺橘背景

#### 模板更新
**檔案**: `src/App.vue` (L866-886)

- 新增 `group-status-mismatch` 狀態顯示 (L869)
- 新增「重新匹配」按鈕 (L876-879)
- 調整「全部取消」按鈕顯示條件 (L880-883)

### 📝 修改的文件
- `src/App.vue` - 狀態邏輯、API 整合、批量處理
- `src/style.css` - 新增 mismatch 相關樣式
- `package.json` - 版本號更新 (1.1.1 → 1.1.2)

---

## v1.1.1 (2025-12-16)

### 🐛 Bug 修復

1. **客人卡片展開連動問題**
   - **檔案**: `src/style.css` (L1480-1500)
   - **修改**: 在 `.guest-cards-list` CSS 規則中添加 `align-items: start`
   - **原因**: grid items 默認會拉伸高度 (stretch)，導致點擊一個卡片展開時，同一列的其他卡片也會被撐開
   - **影響**: 修復了卡片高度連動的顯示異常，確保各自獨立展開

### 🧹 代碼清理

1. **移除調試代碼**
   - **檔案**: `src/App.vue`
   - **修改**: 移除所有 `console.log` 和開發用的 `[NEW VERSION]` 標記
   - **檔案**: `src/components/GuestCard.vue`
   - **修改**: 移除 `onMounted` 中的測試用 log

### 📝 修改的文件
- `src/style.css` (L1480-1500) - CSS Grid 修復
- `src/App.vue` - 清理調試代碼
- `src/components/GuestCard.vue` - 移除 onMounted
- `package.json` - 版本號更新 (1.1.0 → 1.1.1)

---

## v1.1.0 (2025-12-15)

### ✨ 新功能

1. **真實 PMS API 數據整合**
   - **檔案**: `src/App.vue` (L200-250)
   - **修改**: 將四格狀態區塊（今日入住/退房、住房率、空房數）的數據來源從假數據改為 `/api/pms/dashboard` API
   - **實作**: 
     ```javascript
     const pmsStats = await fetch('/api/pms/dashboard').then(res => res.json())
     todayCheckIn.value = pmsStats.today_checkin
     ```

2. **30 秒倒數計時器**
   - **檔案**: `src/App.vue` (L150-180)
   - **實作**: 新增 `countdown` ref 和 `startCountdown()` 函數，每秒遞減顯式下次自動更新時間

### ⚡ 性能優化

1. **差異化更新頻率**
   - **檔案**: `src/App.vue` (L80-90)
   - **策略**: 依據數據重要性設定不同的輪詢間隔
   - **配置**:
     ```javascript
     const REFRESH_INTERVALS = {
       serviceStatus: 5000,    // 5秒 (最重要)
       pmsStats: 15000,        // 15秒
       guestList: 30000,       // 30秒 (最耗資源)
       roomStatus: 15000       // 15秒
     }
     ```

### 🎨 UI 改進

1. **佈局修正**
   - **檔案**: `src/style.css` (L800-850)
   - **修改**: 四格統計區塊寬度改為固定 25%，確保並排顯示整齊
   - **修改**: 優化 Tooltip 內的房況瑕疵文字排版

### 📝 修改的文件
- `src/App.vue` (L80-90, L150-180, L200-250) - 核心邏輯
- `src/style.css` (L800-850) - 樣式修正
- `package.json` - 版本號更新

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
