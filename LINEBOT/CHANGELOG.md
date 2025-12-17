# LINE Bot - Changelog

> LINE 客服機器人的詳細變更記錄

---

## [1.2.0] - 2025-12-17

### 當日預訂 AI 邏輯重構

#### 架構優化
**檔案**: `bot.py`

1. **移除舊版路由邏輯** (L1439-1456)
   - 刪除 `_has_order_number()` 方法
   - 刪除 `if self._has_order_number(user_question):` 路由判斷
   - **理由**: 讓 AI 統一判斷數字是電話還是訂單編號

2. **System Prompt 優化** (L100-150)
   - 新增 "Proactive Confirmation Principle" (主動確認原則)
   - **內容**: 當客人輸入模糊時（如單純數字、不明確時間），AI 需主動詢問確認
   - **效果**: 避免將電話號碼誤判為訂單編號

#### 功能增強
**檔案**: `bot.py`

1. **多房型支援** (L1140-1180)
   - **函數**: `create_same_day_booking()`
   - **修改**: 支援解析多房型字串（例: "2間標準雙人, 1間四人房"）
   - **邏輯**:
     ```python
     # 解析房型字串
     room_patterns = [
         r'(\d+)\s*間?\s*([^,，]+)',  # "2間雙人房"
         r'([^,，]+?)\s*[xX×]\s*(\d+)'  # "雙人房 x 2"
     ]
     ```

2. **床型解析** (L1158-1180)
   - **問題**: 多房型時床型資訊混亂
   - **解決**: 從 `bed_type` 字串解析出每個房型對應的床型
   - **實作**:
     ```python
     bed_type_parts = bed_type.split(',')
     for i, room_entry in enumerate(room_entries):
         bed_type_for_room = bed_type_parts[i].split(':')[1].strip()
     ```

### Bug 修復

1. **多房型床型錯誤**
   - **檔案**: `bot.py` (L1171)
   - **問題**: 所有房型共用同一個 `bed_type`
   - **修復**: 解析床型字串，為每個房型分配正確床型

2. **PMS API 錯誤**
   - **檔案**: `pms-api/routes/bookings.js` (L858, L862-865)
   - **問題**: 使用未定義的 `tempOrderId` 變數
   - **修復**: 改用 `itemId` 和 `orderId`

### 📝 修改的文件
- `bot.py` (L1140-1180, L1439-1456) - 多房型解析、移除舊路由
- `pms-api/routes/bookings.js` (L858, L862-865) - 修復變數錯誤

---

## [1.1.6] - 2025-12-17

### 🐛 Bug 修復

1. **天氣查詢功能修復**
   - **檔案**: `.env`
   - **問題**: CWA_API_KEY 環境變數包含引號導致 API 無法正確讀取
   - **修復**: 移除引號，改為 `CWA_API_KEY=your_key` (不加引號)
   - **影響**: 天氣 API 現已正常運作，可成功查詢中央氣象署資料

2. **錯誤處理機制改善**
   - **檔案**: `bot.py` (L1450-1470)
   - **修改**: 
     - 修復錯誤訊息未記錄到對話 LOG 的問題
     - 所有系統錯誤現在都會記錄完整的 traceback 供除錯
   - **檔案**: `app.py` (L180-185)
   - **修改**: 新增空回應檢查機制，避免發送空白訊息
   - **效果**: 移除無幫助的「連線有點問題」錯誤訊息，改為靜默處理

### ✨ 新功能

1. **天氣資訊增強**
   - **檔案**: `helpers/weather_helper.py` (L85-120)
   - **新增**: 
     - 降雨機率顯示 (當 >0% 時)
     - 體感溫度顯示 (當與實際溫度差異 >2°C 時)
   - **效果**: 提供更完整的天氣資訊，幫助客人做好行程規劃

### 📝 修改的文件
- `.env` - 修正 CWA_API_KEY 引號問題
- `bot.py` (L1450-1470) - 改善錯誤處理與 LOG 記錄
- `app.py` (L180-185) - 新增空回應檢查
- `helpers/weather_helper.py` (L85-120) - 新增降雨機率和體感溫度

---

## [1.1.5] - 2025-12-15

### ✨ 新功能：語音訊息辨識 (Voice to Text)

#### 實作細節
**檔案**: `bot.py`

1. **語音處理方法** (L1568-1600)
   - **函數**: `handle_audio(user_id, audio_content, display_name)`
   - **技術**: 使用 Gemini 2.5 Flash 多模態模型進行語音轉文字
   - **流程**: 
     ```python
     # 1. 接收 LINE AudioMessage
     # 2. 傳送給 Gemini API 進行語音辨識
     # 3. 將辨識結果作為文字訊息處理
     # 4. 呼叫 generate_response() 產生回應
     ```

2. **Webhook Handler** 
   - **檔案**: `app.py` (L164-185)
   - **新增**: `@handler.add(MessageEvent, message=AudioMessage)` 事件監聽器
   - **功能**: 接收語音訊息並呼叫 `handle_audio()` 處理

### 技術對比

| 技術 | 優點 | 缺點 | 使用情境 |
|:---|:---|:---|:---|
| **Gemini 2.5 Flash** ✅ 採用 | 速度最快、整合簡單、無額外費用 | 準確度略低於 Whisper | 即時客服互動 |
| **OpenAI Whisper V3** | 純語音辨識最準確 | 需額外 API、延遲較高 | 專業轉錄需求 |
| **Gemini 1.5 Pro** | 語意理解最強 | 速度較慢、成本較高 | 高精度需求 |

### 📝 修改的文件
- `bot.py` (L1568-1600) - 新增 handle_audio 方法
- `app.py` (L164-185) - 新增 AudioMessage 事件處理

---

## [1.1.5] - 2025-12-15

### 新增功能
- **語音訊息辨識 (Voice to Text)**:
  - 使用者可直接發送語音訊息給 Bot
  - Bot 會自動將語音轉換為文字並回應
  - 採用 Gemini 2.5 Flash 多模態模型進行聽打
  - 支援繁體中文辨識
  - 語音指令效果等同於打字輸入

### 技術實作
- 新增 `handle_audio` 方法:在 `bot.py` 中處理 LINE `AudioMessage`
- 新增 Webhook Handler:在 `app.py` 中註冊 `AudioMessage` 事件監聽器

### AI 語音辨識技術對比

| 技術 | 優點 | 缺點 | 使用情境 |
|:---|:---|:---|:---|
| **Gemini 2.5 Flash** ✅ 採用 | 速度最快、整合簡單、無額外費用 | 準確度略低於 Whisper | 即時客服互動 |
| **OpenAI Whisper V3** | 純語音辨識最準確 | 需額外 API、延遲較高 | 專業轉錄需求 |
| **Gemini 1.5 Pro** | 語意理解最強 | 速度較慢、成本較高 | 高精度需求 |

---

## [1.1.1] - 2025-12-12

### ✨ 新增功能

1. **知識庫擴充**
   - **檔案**: `../data/knowledge_base.json`
   - **新增**: 4 筆常見問題
     - 寵物政策說明 (寵物友善，清潔費 800 元/房)
     - 嬰兒用品租借服務 (嬰兒床、圍欄、消毒鍋、澡盆)
     - 早餐服務說明 (自助式/套餐式)
     - 櫃檯服務時間 (15:00-23:00)

### 🐛 Bug 修復與改進

1. **對話歷史自動重置機制**
   - **檔案**: `bot.py` (L1420-1440)
   - **問題**: 對話歷史過長導致 AI token 超限 (finish_reason=1)
   - **修復**: 
     ```python
     except ValueError as e:
         if "finish_reason" in str(e):
             # 自動清除對話歷史
             self.clear_history(user_id)
             return "對話歷史已自動清除，請再次提供訂單編號"
     ```
   - **效果**: 解決長期用戶無法獲得回應的問題

2. **錯誤訊息日誌完善**
   - **檔案**: `bot.py` (L1450-1460)
   - **修復**: 錯誤訊息未記錄到 chat log 的問題
   - **修改**: 所有 Bot 回應 (包括錯誤訊息) 現在都會正確記錄

### 📝 修改的文件
- `../data/knowledge_base.json` - 新增 4 筆常見問題
- `bot.py` (L1420-1440) - 對話歷史自動重置
- `bot.py` (L1450-1460) - 錯誤日誌完善

---

## [1.1.0] - 2025-12-11

### 新增功能
- **重新開始對話功能**:用戶可輸入「重新開始」、「reset」、「restart」或「清除對話」來重置對話歷史
- **早餐資訊自動判斷**:系統會從備註和房型名稱中檢查「不含早」關鍵字,自動判斷是否包含早餐
- **房型對照表獨立管理**:將房型對照表從代碼中抽離到 `room_types.json`,便於維護和更新

### 改進優化
- **訂單來源判斷邏輯優化**:
  - 優先檢查 `remarks` 中的關鍵字(「官網」、「agoda」、「booking.com」)
  - 其次才使用 OTA ID 前綴判斷(RMAG、RMPGP)
  - 修正了誤將官網訂單判定為 Booking.com 的問題

- **PMS API 數據處理增強**:
  - 支援大寫鍵名(`ROOM_TYPE_CODE`、`ROOM_COUNT`、`ROOM_TYPE_NAME`)
  - 同時兼容小寫鍵名,提高容錯性
  - 修復房型顯示「無」的問題

- **AI 模型升級**:
  - 主對話模型:Gemini 2.0 Flash Exp → Gemini 2.5 Flash
  - 提供更好的理解能力和回應品質

- **系統指令優化**:
  - 加強訂單詳情顯示要求,確保 Bot 不會跳過顯示步驟
  - 添加正確/錯誤流程示例,提高 AI 遵守指令的準確性

### 錯誤修復
- **修復 KeyError 問題**:
  - 修復 `room_type_name` KeyError(當值為 `null` 時)
  - 修復 `room_count` KeyError(使用 `.get()` 方法並設置默認值)
  - 所有字典訪問都改用安全的 `.get()` 方法

- **修復隱私檢查邏輯**:
  - 修正 Gmail 隱私檢查的 AI validator 提示詞
  - 明確處理未來訂單(DAYS_AGO < 0)的情況
  - 確保近期訂單和未來訂單都能正常顯示

### 代碼品質
- 移除 17 行硬編碼的房型字典,改為 3 行 JSON 載入
- 改善代碼可維護性和可讀性
- 統一錯誤處理方式

---

## [1.0.1] - 2025-12-10

### 初始版本
- LINE Bot 基本功能
- 訂單查詢系統(3-Step 協議)
- Gmail API 整合(備用訂單來源)
- Google Gemini AI 整合
- 天氣預報功能
- 客人資訊收集與更新
- 對話歷史記錄
