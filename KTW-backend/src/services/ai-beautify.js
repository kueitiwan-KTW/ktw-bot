import { GoogleGenerativeAI } from '@google/generative-ai';

// 延遲初始化（確保 .env 已載入）
let model = null;
function getModel() {
    if (!model) {
        const genai = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY || '');
        model = genai.getGenerativeModel({ model: 'gemini-2.5-flash' });
    }
    return model;
}

// 快取儲存（簡單記憶體快取）
const cache = new Map();
const CACHE_TTL = 15 * 60 * 1000; // 15 分鐘

/**
 * 美化訂單資料（整合 Bot 收集的資訊）
 * @param {Object} booking - 原始訂單資料
 * @param {Object} botInfo - Bot 收集的客戶資訊（LINE 姓名、電話、特殊需求等）
 * @returns {Promise<Object>} - 美化後的訂單資料
 */
export async function beautifyBooking(booking, botInfo = null) {
    // 檢查快取
    const cacheKey = `booking_${booking.booking_id}`;
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
        return cached.data;
    }

    try {
        const prompt = `你是飯店訂單資料處理專家。請優化以下訂單資料：

**PMS 原始資料：**
${JSON.stringify(booking, null, 2)}

**Bot 收集的客戶資訊：**
${botInfo ? JSON.stringify(botInfo, null, 2) : '無'}

---

**處理規則：**
1. 從 remarks 提取 OTA 訂單號（純數字，通常10位數）
2. 判斷訂房來源（Agoda/Booking.com/官網等）
3. 提取真實客人姓名
4. 判斷早餐（預設有，remarks 有"不含早"則無）
5. 格式化電話號碼
6. 整合 Bot 資料

---

**🚨 JSON 結構要求（必須嚴格遵守）：**
\`\`\`json
{
  "booking_id": "原始PMS編號",
  "display_order_id": "OTA訂單號或PMS編號",
  "booking_source": "訂房來源",
  "guest_name": "客人真實姓名",
  "contact_phone": "格式化電話",
  "check_in_date": "入住日期",
  "check_out_date": "退房日期", 
  "nights": 晚數,
  "status_code": "狀態碼",
  "status_name": "狀態名稱",
  "breakfast": "有早餐" 或 "不含早餐",
  "remarks": "原始備註",
  "line_name": "LINE名稱或null",
  "arrival_time": "抵達時間或null",
  "special_needs": "特殊需求或null"
}
\`\`\`

**⚠️ 嚴格規定：**
- 必須使用以上欄位名稱（不可自創）
- 不可建立巢狀物件
- 保持扁平結構
- 所有欄位都必須存在`;

        const result = await getModel().generateContent(prompt);
        const response = result.response.text();

        // 解析 JSON（移除可能的 markdown 標記）
        const jsonMatch = response.match(/\{[\s\S]*\}/);
        if (!jsonMatch) {
            throw new Error('AI 回傳格式錯誤');
        }

        const beautified = JSON.parse(jsonMatch[0]);

        // 存入快取
        cache.set(cacheKey, {
            data: beautified,
            timestamp: Date.now()
        });

        return beautified;

    } catch (error) {
        console.error('AI 美化失敗，使用原始資料:', error.message);
        return booking; // Fallback: 回傳原始資料
    }
}

/**
 * 批量美化多筆訂單（整合 Bot 資料）
 * @param {Array} bookings - 訂單陣列
 * @param {Object} botDataMap - Bot 資料映射 { booking_id: botInfo }
 */
export async function beautifyBookings(bookings, botDataMap = {}) {
    return Promise.all(bookings.map(b => beautifyBooking(b, botDataMap[b.booking_id])));
}
