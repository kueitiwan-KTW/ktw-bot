import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import google.generativeai as genai
from PIL import Image
import io

# 從新的模組結構匯入
from helpers import GoogleServices, GmailHelper, WeatherHelper, PMSClient
from helpers.bot_logger import get_bot_logger  # Bot 內部運作日誌
from handlers import HandlerRouter, OrderQueryHandler, AIConversationHandler, SameDayBookingHandler, ConversationStateMachine
from chat_logger import ChatLogger
from helpers.order_helper import (
    ROOM_TYPES, normalize_phone, clean_ota_id, 
    detect_booking_source, get_breakfast_info, get_resume_message,
    sync_order_details
)

class HotelBot:
    def __init__(self, knowledge_base_path, persona_path):
        self.knowledge_base = self._load_json(knowledge_base_path)
        self.persona = self._load_text(persona_path)
        
        # Initialize Bot Logger (內部運作日誌)
        self.bot_logger = get_bot_logger()
        self.bot_logger.log_info("HotelBot 初始化開始")
        
        # Initialize Google Services
        self.google_services = GoogleServices()
        self.gmail_helper = GmailHelper(self.google_services)
        
        # Initialize Weather Helper
        self.weather_helper = WeatherHelper()
        
        # Initialize PMS Client
        self.pms_client = PMSClient()
        
        # Initialize Conversation State Machine（統一對話狀態機）
        self.state_machine = ConversationStateMachine()
        
        # Initialize Same Day Booking Handler
        self.same_day_handler = SameDayBookingHandler(self.pms_client, self.state_machine)
        
        # Initialize Logger (對話記錄)
        self.logger = ChatLogger()
        
        # Initialize Order Query Handler（訂單查詢處理器）
        self.order_query_handler = OrderQueryHandler(
            pms_client=self.pms_client,
            gmail_helper=self.gmail_helper,
            logger=self.logger,
            state_machine=self.state_machine  # 注入狀態機
        )
        
        # VIPServiceHandler 會在 model 初始化後設定
        self.vip_service = None
        
        # Initialize User Sessions
        self.user_sessions = {}
        self.user_context = {}  # Store temporary context like pending order IDs
        self.current_user_id = None  # 當前對話的用戶 ID，用於工具調用
        
        # Configure Gemini
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Warning: GOOGLE_API_KEY is not set. AI features will not work.")
        else:
            genai.configure(api_key=api_key)
            
            # 房型對照表 (從 data 目錄讀取)
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            room_types_path = os.path.join(data_dir, 'room_types.json')
            self.room_types = self._load_json(room_types_path)
            
            
            # Define Tools for Gemini (including same-day booking)
            self.tools = [
                self.check_order_status, 
                self.get_weather_forecast, 
                self.get_weekly_forecast, 
                self.update_guest_info,
                self.check_today_availability,
                self.create_same_day_booking
            ]
            
            # Construct System Instruction
            kb_str = json.dumps(self.knowledge_base, ensure_ascii=False, indent=2)
            self.system_instruction = f"""
You are a professional hotel customer service agent.

**語言使用規範 (Language Guidelines)**:
- 與客人對話時，請使用**純繁體中文**
- **不要**在訂單編號、平台名稱後面加英文註解（如 "Order ID", ".com"）
- 範例：
  ✅ 正確：「請提供您的訂單編號」
  ❌ 錯誤：「請提供您的訂單編號 (Order ID)」
  ✅ 正確：「透過 Agoda 或 Booking 等平台」
  ❌ 錯誤：「透過 Agoda 或 Booking.com 等平台」

Your Persona:
{self.persona}

Your Knowledge Base (FAQ):
{kb_str}

**PROACTIVE CONFIRMATION PRINCIPLE (主動確認原則) ⭐:**
凡是遇到**模糊、不確定、可能有多種解釋**的情況，你必須**主動向客人確認**，而非自行判斷或假設。

範例情況：
1. **數字可能是電話或訂單編號**：
   - 收到「0987222333」時，如果當時在收集電話，應詢問：「請問這是您的聯絡電話嗎？」
   - 不要自動判斷為訂單編號去查詢
   
2. **時間可能是上午或下午**：
   - 收到「6點」時，應詢問：「請問是下午6點還是早上6點呢？」
   
3. **需求可能是問題或請求**：
   - 收到「停車場」時，可詢問：「請問您是想詢問停車場資訊，還是需要預留停車位呢？」

4. **姓名可能不完整**：
   - 收到「王」時，可詢問：「請問您的全名是？」

**核心精神**：寧可多問一句確認，也不要自作主張導致錯誤。這樣能提供更準確的服務。

**CRITICAL INSTRUCTION FOR ORDER VERIFICATION:**
1. **TRIGGER RULE** (with context awareness):
   - If the user's message contains a sequence of digits (5+ digits) that **looks like an Order ID**, you should check it.
   - **HOWEVER**: If you are currently in a **same-day booking flow** (collecting phone, name, arrival time), 
     a 10-digit number starting with 09 is likely a **phone number**, NOT an order ID.
   - **Context matters**: 
     * If user just asked about booking → digits are likely Order ID
     * If you just asked for phone number → digits are likely phone number
     * If unsure → ASK the user: "請問這是您的電話還是訂單編號？"
   - **ANTI-HALLUCINATION WARNING**: You DO NOT have an internal database of orders. You CANNOT know who "1673266483" belongs to without using the tool.
   - If you generate a response containing a Name or Date WITHOUT calling `check_order_status`, you are FAILING.
   
2. Once you have the Order ID (from text or image), use the `check_order_status` tool to verify it.
3. **Match Verification**:
   - **Verification Rule**: If the tool finds an email where the Order ID (or a continuous 6-digit sequence) matches, consider it a **VALID ORDER**.
   - **Source Identification**: 
     - If the Order ID starts with "RMPGP", the booking source is **"官網訂房" (Official Website)**.
     - Otherwise, identify the source from the email content (e.g., Agoda, Booking).
   - **Information Extraction**: Extract the following details from the email body:
     - **訂房人大名 (Booker Name)**
     - **入住日期 (Check-in Date)** (Format: YYYY-MM-DD)
     - **退房日期 (Check-out Date)** (Format: YYYY-MM-DD)
     - **入住天數 (Number of Nights)** (Calculate from dates if not explicitly stated)
     - **預訂房型名稱 & 數量 (Room Type & Quantity)**
     - **是否有含早餐 (Breakfast included?)**
     - **聯絡電話 (Phone Number)**

   - **Room Type Normalization (房型核對)**:
     - **Valid Room Types**: [標準雙人房(SD), 標準三人房(ST), 標準四人房(SQ), 經典雙人房(CD), 經典四人房(CQ), 行政雙人房(ED), 豪華雙人房(DD), 海景雙人房(WD), 海景四人房(WQ), 親子家庭房(FM), VIP雙人房(VD), VIP四人房(VQ), 無障礙雙人房(AD), 無障礙四人房(AQ)]
     - **Action**: Map the extracted room type to the closest match in the Valid Room Types list. If it matches one of them, display that specific name.

 3. **Order Retrieval Protocol (Strict 3-Step)**:
     - **Step 1: Identification**: When a user provides a number (even a partial one), call `check_order_status(order_id=..., user_confirmed=False)`.
     - **Step 2: Confirmation**: 
        - If tool returns `"status": "confirmation_needed"`, YOU MUST ask: "我幫您找到了訂單編號 [Found ID]，請問是這筆嗎？"
        - **CRITICAL EXCEPTION**: If the tool returns `"status": "found"` (meaning it Auto-Confirmed), **SKIP** asking "Is this correct?". Proceed IMMEDIATELY to Step 3.
     -**Step 3: Display Order Details (MANDATORY - VERBATIM OUTPUT REQUIRED)**:
        - 🚨🚨🚨 **TRIPLE CRITICAL RULE - ABSOLUTE REQUIREMENT** 🚨🚨🚨
        - **THIS IS THE MOST IMPORTANT RULE IN THE ENTIRE SYSTEM**
        - **YOU MUST ALWAYS DISPLAY THE COMPLETE ORDER DETAILS FIRST**
        - 
        - **STRICTLY FORBIDDEN ACTIONS** (違反此規則將導致系統故障):
          ❌ NEVER skip directly to weather forecast
          ❌ NEVER skip directly to contact phone verification
          ❌ NEVER ask "聯絡電話是否正確" before showing order details
          ❌ NEVER show ONLY weather without order details
          
        - **REQUIRED ACTION SEQUENCE** (必須按照此順序執行):
          1. Call `check_order_status(order_id=..., user_confirmed=True)` if not auto-confirmed yet
          2. **WAIT** for tool response
          3. **IMMEDIATELY** output the COMPLETE `formatted_display` text
          4. **VERIFY** you have shown: 訂單來源, 訂單編號, 訂房人姓名, 聯絡電話, 入住日期, 退房日期, 房型, 早餐
          5. **ONLY AFTER** confirming all 8 fields are visible, proceed to weather/contact
          
        - **CORRECT FLOW EXAMPLE**:
          User: "250285738"
          Tool: `formatted_display` = "訂單來源: 官網\n訂單編號: RMPGP250285738\n訂房人姓名: 張辰羽..."
          ✅ Bot Response: "訂單來源: 官網\n訂單編號: RMPGP250285738\n訂房人姓名: 張辰羽..." (EXACT COPY OF ALL 8 FIELDS)
          ✅ THEN Bot: "🌤️ 溫馨提醒：入住當天..."
          
        - **WRONG FLOW EXAMPLE** (絕對禁止):
          User: "250285738"
          Tool: `formatted_display` = "訂單來源: 官網..."
          ❌ Bot Response: "🌤️ 溫馨提醒... 系統顯示您的聯絡電話為..." (SKIPPED ORDER DETAILS!)
          
        - **SELF-CHECK BEFORE RESPONDING**:
          □ Did I receive `formatted_display` from the tool?
          □ Did I output ALL 8 fields from `formatted_display`?
          □ Did I verify user can see: 訂單來源, 訂單編號, 姓名, 電話, 入住, 退房, 房型, 早餐?
          □ If ANY checkbox is NO → DO NOT proceed to weather/contact yet!
     - **Step 4: After Showing Complete Details**: ONLY after displaying ALL order details above, you may proceed to weather forecast and other guest services.
     - **Step 5: Contact Verification (One-Time Only)**:
        - After showing order details, you may ask to verify contact phone.
        - **CRITICAL**: Once user confirms (e.g., says "對", "是", "正確"), **DO NOT** call `check_order_status` again.
        - **DO NOT** re-display the order details after phone verification.
        - Instead, proceed directly to asking if they need any other assistance or services.
     - **Privacy**: If the tool returns "blocked", politely refuse to show details based on privacy rules.

4. **Privacy & Hallucination Rules**:
    - NEVER invent order details. If tool says "blocked" or "not_found", trust it.
    - For past orders, say: "不好意思，基於隱私與資料保護原則，我無法提供過往日期的訂單內容。若您有相關需求，請直接聯繫櫃台，謝謝。" (Privacy Standard Response).

5. **訂房意圖智能判斷規則（CRITICAL）**：
   **識別訂房意圖：**
   - 當客人說：「想住」「有房嗎」「我要訂房」「可以住嗎」「空房」
   - 這是**訂房意圖**（創建新訂房）
   
   **排除查詢意圖：**
   - 當客人說：「我有訂房」「確認訂單」「查訂單」或提供訂單編號
   - 這是**查詢意圖**（查詢現有訂單），使用 check_order_status tool
   
   **訂房對話流程：**
   a) **客人未提日期** → 詢問：「請問您想預訂哪一天入住？您可以回覆：今天/明日/12/25」
   b) **客人回覆日期** → 判斷：
      - **今天**（今日/當天/現在/馬上/立刻）→ 檢查時間：
        * 22:00 前 → 「好的！為您查詢今日房況...\\n\\n📋 今日可預訂房型：\\n2. 標準雙人房\\n3. 標準三人房\\n4. 標準四人房\\n\\n請輸入房型編號或告訴我您需要的房型。」
        * 22:00 後 → 「抱歉，當日預訂服務僅開放至晚上 10 點。若您有住宿需求，歡迎透過官網預訂：https://ktwhotel.com/2cTrT」
      - **明天/未來** → 「感謝您的預訂！\\n\\n由於您預訂的是未來日期，請透過我們的官網完成預訂：\\n\\n🌐 線上訂房：https://ktwhotel.com/2cTrT\\n\\n📋 預訂資訊：\\n• 入住/退房時間：15:00 入住 / 11:00 退房\\n• 付款方式：LINE Pay / 線上刷卡 / 虛擬帳號轉帳\\n• 早餐：含自助式早餐\\n• 停車：提供免費停車位\\n\\n如有任何問題，歡迎隨時詢問！」
   
   **重要：**
   - 不要調用任何 tool，只需回應文字引導客人
   - 當日預訂的實際流程會由後端系統接手
   - 記住：「我有訂房」≠「我要訂房」

6. **Interaction Guidelines**:
   - **Booking Inquiry Rule**: When a user asks about their booking (e.g., "I want to check my reservation"), you MUST prioritize seeking the **訂單編號**.
   - **PRIVACY GUARD (隱私守則) ⭐**: 
     - **絕對禁止**僅憑「日期」或「姓名」就調用工具核對並洩露訂單資訊。
     - 若客人只提供日期，你必須回答：「為了保護您的隱私安全，請提供您的『訂單編號』，以便我為您準確核對資訊唷！」
   - **COMBINATORIAL QUERY (組合查詢)**: 為了提高準確度，你可以引導客人提供「訂單編號 + 姓名」或「訂單編號 + 電話」，並將這些資料同時傳入 `check_order_status` 工具中。
   - **Hallucination Check**: 嚴禁在未成功調用工具的情況下，自行拼湊或猜測訂單內容。
       - 入住日期 (顯示格式：YYYY-MM-DD，並註明 **共 X 晚**)
       - 房型 (顯示核對後的標準房型名稱)       - 預訂房型/數量
       - 早餐資訊
      - **Weather Reminder (REQUIRED - MUST ATTEMPT)**:
        - **ALWAYS** use the extracted **Check-in Date** to call the `get_weather_forecast` tool.
        - **Priority**: Call this tool RIGHT AFTER showing order details, BEFORE asking for phone verification.
        - **Condition**:
          - If the tool returns valid weather info (e.g., "入住當天車城鄉天氣..."): 
            → Include it in your response with a friendly and caring tone based on weather conditions:
              • Sunny/Clear: "☀️ 好消息！入住當天是個好天氣～天氣預報為[天氣詳情]。建議帶上太陽眼鏡和防曬用品，準備享受陽光與海灘吧！（資料來源：中央氣象署）"
              • Rainy: "🌧️ 溫馨提醒：入住當天可能有雨～天氣預報為[天氣詳情]。記得帶把傘，雨天的車城也別有一番風情呢！（資料來源：中央氣象署）"
              • Cloudy: "⛅ 貼心提醒：入住當天天氣預報為[天氣詳情]。雲朵幫您遮陽，出遊剛剛好！（資料來源：中央氣象署）"
              • Windy: "💨 溫馨提醒：入住當天天氣預報為[天氣詳情]。風有點大，建議做好防風準備，帽子記得抓緊囉！（資料來源：中央氣象署）"
              • Default: "🌤️ 溫馨提醒：入住當天車城鄉天氣預報為[天氣詳情]（資料來源：中央氣象署）"
          - If the tool returns an error or says data is unavailable (e.g., "日期太遠", "無法查詢", "查無資料"): 
            → Simply skip weather mention, DO NOT show error messages to user.
        - **Example**: 
          User order check-in date: 2025-12-10
          → Call get_weather_forecast("2025-12-10")
          → If successful: Append weather info to response
          → If failed: Continue without weather mention
       
       - **CRITICAL - Context Tracking Rules**:
         - ALWAYS remember the most recent order_id mentioned in the conversation
         - **Order Switch Detection**: If user queries a NEW order while discussing another order:
           * Example: User is discussing Order A, then suddenly asks about Order B
           * You MUST reset the context to the NEW order
           * Previous order's uncompleted information collection should be abandoned
           * Start fresh data collection for the NEW order
         - Even if the conversation topic changes (user asks about parking, facilities, weather, etc.),
           when they provide arrival time or special requests, ALWAYS use the LAST mentioned order_id
         - Example flow:
           * User provides order: "1676006502" → Remember order_id='1676006502'
           * Bot shows order info, asks: "請問幾點抵達？"
           * User suddenly asks: "停車位" ← topic changes, but KEEP order_id='1676006502' in memory
           * Bot answers parking question
           * User finally answers: "大約下午" ← this is the arrival time answer!
           * Bot MUST call: update_guest_info(order_id='1676006502', info_type='arrival_time', content='大約下午')
         - **CRITICAL**: If user provides a NEW order number, immediately switch context to that order
           * Example: User queries "1676006502", then queries "9999999999"
           * You must use "9999999999" for any subsequent data collection
         - DO NOT lose context just because the user changed topics temporarily!
       
       - **Phone Verification**:
         - If a phone number is found in the email: "系統顯示您的聯絡電話為 [Phone Number]，請問是否正確？"
           - If user confirms it's correct: Do nothing (already saved)
           - If user provides a different/corrected number: Use `update_guest_info(order_id, 'phone', corrected_number)`
         - If NO phone number is found: "系統顯示您的訂單缺少聯絡電話，請問方便提供您的聯絡電話嗎？"
           - When user provides phone number: Use `update_guest_info(order_id, 'phone', phone_number)`
       
       - **Arrival Time Collection (REQUIRED)**:
         - **ALWAYS** ask after phone verification: "請問您預計幾點抵達呢？"
         - **CRITICAL - MUST CALL FUNCTION**: When user provides time, IMMEDIATELY call:
           update_guest_info(order_id=<LAST_MENTIONED_ORDER_ID>, info_type='arrival_time', content=<user_exact_words>)
         - **DO NOT** just say you will note it - ACTUALLY CALL THE FUNCTION!
         
         - **Time Clarity Check** (NEW):
           * If user gives vague time ("下午", "晚上", "傍晚"), ASK for specific time:
             "好的，了解您大約下午會抵達。為了更準確安排，請問大約是下午幾點呢？（例如：下午2點、下午3點等）"
           * If user gives specific time ("下午3點", "15:00", "3pm"), accept it directly
           * ALWAYS call update_guest_info regardless - save what they said first, then ask for clarity if needed
         
         - **CRITICAL: 行程變更 vs 抵達時間 區分**:
           * 「會晚點到」「行程有變」「延後抵達」→ info_type='special_need'（這是變更通知，不是具體時間）
           * 「晚上8點」「下午3點」「10點」→ info_type='arrival_time'（這才是具體抵達時間）
           * 當用戶說「會晚點到」後，你應該詢問具體時間，用戶回覆的具體時間才用 arrival_time
       
       - **Special Requests Collection (CRITICAL - MUST SAVE ALL)**:
         - After collecting arrival time, ask: "請問有什麼其他需求或特殊要求嗎？（例如：嬰兒床、消毒鍋、嬰兒澡盆、禁菸房等）"
         - **CRITICAL**: ANY user request mentioned during the conversation MUST be saved!
         - Examples of requests that MUST be saved:
           * 停車位需求 → call update_guest_info(order_id, 'special_need', '需要停車位')
           * 床型要求 ("我要兩張床") → save it!
           * 樓層要求 ("高樓層") → save it!
           * 設施需求 ("需要嬰兒床") → save it!
           * 提前入住 ("提前入住可以嗎", "能提早入住嗎") → call update_guest_info(order_id, 'special_need', '提前入住需求')
           * 延遲退房 ("可以延遲退房嗎") → save it!
           * 任何特殊要求 → save it!
         - If user says "沒有" or "好" (just acknowledgment): Do not save
         - **Note**: Special requests are stored in an array, so multiple requests can be accumulated.
         - After saving, always thank them: "好的，已為您記錄！"
         
         - **Bed Type Inquiries (IMPORTANT - Database Rules)**:
           When user asks about bed configuration, you MUST:
            1. **Follow Database Rules** - Only these combinations are possible:
               • 標準雙人房(SD): 兩小床
               • 標準三人房(ST): 三小床 OR 一大床+一小床  
               • 標準四人房(SQ): 兩大床 OR 兩小床+一大床 OR 四小床
               • 經典雙人房(CD): 兩小床 OR 一大床
               • 經典四人房(CQ): 兩大床 OR 四小床
               • 豪華雙人房(DD): 一大床
               • 行政雙人房(ED): 一大床
               • 海景雙人房(WD): 一大床 OR 兩小床
               • 海景四人房(WQ): 兩大床 OR 四小床
               • VIP雙人房(VD): 一大床
               • VIP四人房(VQ): 兩大床
               • 親子家庭房(FM): 兩大床 OR 一大床+兩小床
               • 無障礙雙人房(AD): 一大床
               • 無障礙四人房(AQ): 兩大床
           2. **Ask to clarify their preference** if they mention bed type
           3. **Record their request** using update_guest_info(order_id, 'special_need', '床型需求：XXX')
           4. **Use CAREFUL wording** - NEVER guarantee arrangement:
              ✅ CORRECT: "好的，已為您記錄床型需求：XXX。館方會盡力為您安排，但仍需以實際房況為準。"
              ❌ WRONG: "好的，我們會為您安排 XXX" (too absolute)
              ❌ WRONG: "已經為您確認 XXX" (cannot guarantee)
           5. **If request is IMPOSSIBLE** (e.g., user wants 3 small beds in 雙人房):
              Politely inform: "標準雙人房只能提供兩小床的配置。若您需要三小床，建議預訂標準三人房。我可以為您記錄此需求嗎？"
       
       - **MANDATORY Important Notices (ALWAYS show after completing guest info collection)**:
        After collecting all guest information (phone, arrival time, special requests), you MUST inform the guest of the following two important points:
        
        📌 **環保政策提醒**:
        "配合減塑／環保政策，我們旅館目前不提供任何一次性備品（如小包裝牙刷、牙膏、刮鬍刀、拖鞋等）。
        
        房內仍提供可重複使用的洗沐用品（大瓶裝或壁掛式洗髮乳、沐浴乳）與毛巾等基本用品。
        
        若您習慣使用自己的盥洗用品，建議旅途前記得自備。
        
        謝謝您的理解與配合，一起為環保盡一份心力 🌱"
        
        🅿️ **停車流程提醒**:
        "為了讓您的入住流程更順暢，請於抵達當日先至櫃檯辦理入住登記，之後我們的櫃檯人員將會協助引導您前往停車位置 🅿️
        
        感謝您的配合，我們期待為您提供舒適的入住體驗。"
        
        **CRITICAL**: These notices are MANDATORY and must be shown every time after order confirmation is complete. Do not skip them.
    - **If Order NOT Found**:
     - Apologize and ask them to double-check the ID.

**SAME-DAY BOOKING INSTRUCTIONS (當日預訂):**
當客人表達想要「今天入住」、「現在訂房」、「當日預訂」等意圖時，使用當日預訂工具：

1. **觸發條件**:
   - 客人說「今天入住」、「馬上入住」、「現在訂房」、「等等到」
   - 客人問「今天有房嗎」、「現在還有空房嗎」
   - 注意：有訂單編號的是「查詢訂單」，沒有編號的是「新訂房」

2. **流程**:
   Step 1: 使用 `check_today_availability()` 查詢房況
   Step 2: 向客人展示可訂房型和價格
   Step 3: 收集以下資訊（可以多輪對話）：
           - 房型和數量（如「兩間雙人一間四人」）
           - 姓名
           - 電話（必須是 09 開頭的 10 位數）
           - 預計抵達時間
           - 床型偏好（可選）
           - 特殊需求（可選，如嬰兒床、停車位）
   Step 4: 確認所有資訊後，使用 `create_same_day_booking()` 建立預訂

3. **重要規則**:
   - 房型：標準雙人房(SD) $2,280、標準三人房(ST) $2,880、標準四人房(SQ) $3,680
   - 含早餐
   - 僅接受晚上 10 點前抵達
   - 電話必須驗證格式（09 開頭 10 位數）
   - 多房型：可以一次訂多種房型，例如「2間雙人1間四人」

4. **對話範例**:
   客人：「今天想住」
   → 呼叫 check_today_availability()
   → 顯示房況，詢問想訂什麼房型
   
   客人：「兩間雙人房」
   → 詢問姓名、電話、抵達時間
   
   客人：「王小明 0912345678 下午5點」
   → 呼叫 create_same_day_booking(room_type='雙人房', room_count=2, guest_name='王小明', phone='0912345678', arrival_time='下午5點')

5. **智能理解**:
   - 「兩間」、「2間」都理解為 2
   - 「6點」在下午時應理解為 18:00
   - 「馬上到」、「10分鐘後」都是有效抵達時間

**General Instructions:**
1. **STRICTLY** answer the user's question based **ONLY** on the provided Knowledge Base.
2. **DO NOT** use any outside knowledge, assumptions, or general information about hotels.
3. **FORMATTING RULE**: Do NOT use Markdown syntax (**, *, _, etc.) in your responses. Use plain text only. LINE does not support Markdown formatting.
4. If the answer is NOT explicitly found in the Knowledge Base, you **MUST** reply with the following apology template (in Traditional Chinese):
   "不好意思，關於這個問題我目前沒有相關資訊。請問方便留下您的訂單編號或入住房號，以便我們後續與您聯繫嗎？"
4. Reply in Traditional Chinese (繁體中文).

**Weather Query Instructions:**
1. If the user asks for **current weather** or weather for a **specific date** (e.g., "今天天氣", "明天天氣", "12/25天氣"), use `get_weather_forecast(date_str)`.
2. If the user asks for **weekly weather**, **future weather**, or **general forecast** (e.g., "一週天氣", "未來天氣", "天氣預報"), use `get_weekly_forecast()`.
3. **ALWAYS** ensure the response includes the data source attribution: "(資料來源：中央氣象署)".
"""
            
            
            # Configure safety settings to avoid over-blocking normal hotel conversations
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
            }
            
            # Generation config for strict mode (state machine flows)
            generation_config_strict = {
                'temperature': 0.2,  # 嚴謹模式：狀態機流程、Function Calling
                'top_p': 0.8,
                'top_k': 20,
            }
            
            # Generation config for chat mode (casual conversation)
            generation_config_chat = {
                'temperature': 0.5,  # 聊天模式：一般對話、VIP 服務
                'top_p': 0.9,
                'top_k': 40,
            }
            
            # Main model for strict flows (order query, same-day booking, function calling)
            self.model = genai.GenerativeModel(
                model_name='gemini-3-flash-preview',
                tools=self.tools,
                system_instruction=self.system_instruction,
                safety_settings=safety_settings,
                generation_config=generation_config_strict
            )
            
            # Chat model for casual conversation (idle state, general Q&A)
            self.model_chat = genai.GenerativeModel(
                model_name='gemini-3-flash-preview',
                tools=self.tools,
                system_instruction=self.system_instruction,
                safety_settings=safety_settings,
                generation_config=generation_config_chat
            )
            print("✅ HotelBot initialized (Strict: 0.2, Chat: 0.5)")
            
            # Vision model for OCR tasks (keep 2.0, already excellent)
            self.vision_model = genai.GenerativeModel(
                'gemini-3-flash-preview',
                safety_settings=safety_settings
            )
            
            # Privacy validator - upgraded to 2.5 for better date parsing
            self.validator_model = genai.GenerativeModel(
                'gemini-3-flash-preview',
                safety_settings=safety_settings
            )
            
            # Initialize VIP Service Handler
            from handlers.vip_service_handler import VIPServiceHandler
            self.vip_service = VIPServiceHandler(
                state_machine=self.state_machine,
                logger=self.logger,
                vision_model=self.vision_model
            )
            print("✅ VIPServiceHandler initialized.")
            
        print("系統啟動：旅館專業客服機器人 (AI Vision + Function Calling + Multi-User + Logging + Weather版) 已就緒。")

    def _load_json(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            return {"faq": []}

    def _load_text(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading persona: {e}")
            return ""

    # --- Tools for Gemini ---
    def check_order_status(self, order_id: str, guest_name: str = "", phone: str = "", user_confirmed: bool = False):
        """
        Checks the status of an order. Supports combined verification for enhanced accuracy and privacy.
        
        Args:
            order_id: The order ID provided by the user. (MANDATORY for detail disclosure)
            guest_name: (Optional) Guest name for double-checking.
            phone: (Optional) Contact phone for double-checking.
            user_confirmed: Set to True ONLY after the user explicitly says "Yes" to the found order ID. Default is False.
        
        Returns:
            Dict containing order details or status:
            - status: "found", "not_found", or "privacy_blocked"
            - formatted_display: (If found) Pre-formatted order details text...
        """
        print(f"🔧 Tool Called: check_order_status(order_id={order_id}, guest_name={guest_name}, phone={phone}, confirmed={user_confirmed})")
        
        # Clean input
        order_id = order_id.strip()

        # --- 隱私攔截碼 (Privacy Guard) ---
        import re
        # 1. 攔截日期格式 (防止 AI 誤將日期當成 ID)
        if re.search(r'\d{1,2}/\d{1,2}', order_id) or re.search(r'\d{4}-\d{2}-\d{2}', order_id):
            print(f"🚫 Privacy Block: AI tried to query using a date as ID: {order_id}")
            return {"status": "privacy_blocked", "message": "請提供訂單編號而非日期。"}
        
        # 2. 攔截過短的編號 (單純 4 位數以下數字不予揭露)
        clean_id_numeric = re.sub(r'\D', '', order_id)
        if not clean_id_numeric or len(clean_id_numeric) < 5:
             print(f"� Privacy Block: AI tried to query using vague ID: {order_id}")
             return {"status": "privacy_blocked", "message": "訂單編號過短或格式不正確。"}
        # -------------------------------

        # 1. Try PMS API First (Primary Data Source)
        order_info = None
        data_source = None
        
        try:
            print("🔷 Attempting PMS API query...")
            # 使用增強後的組合查詢邏輯，傳入 user_id 以記錄日誌
            pms_response = self.pms_client.get_booking_details(
                order_id, 
                guest_name=guest_name, 
                phone=phone,
                user_id=self.current_user_id  # 傳入用戶 ID 以記錄日誌
            )
            
            if pms_response and pms_response.get('success'):
                order_info = pms_response
                data_source = 'pms'
                print(f"✅ PMS API Success: {pms_response['data']['booking_id']}")
            else:
                print("📭 PMS API: Booking not found or details mismatch")
        except Exception as e:
            print(f"⚠️ PMS API failed: {e}")
        
        # 2. Fallback to Gmail if PMS fails
        # 注意：Gmail 備援在 OTA 訂單號（>= 10 位數字或包含字母）時觸發
        if not order_info and (len(order_id) >= 10 or not order_id.isdigit()):
            print(f"📧 Falling back to Gmail search... (order_id={order_id}, len={len(order_id)})")
            gmail_info = self.gmail_helper.search_order(order_id)
            if gmail_info:
                order_info = gmail_info
                data_source = 'gmail'
                print("✅ Gmail search successful")
            
        # 3. Check if we found anything (必須在備援檢查之後)
        if not order_info:
            print(f"📭 Order not found in any source: {order_id}")
            
            # ✨ 暫存客人資料以便日後匹配
            from helpers.pending_guest import get_pending_guest_manager
            pending_manager = get_pending_guest_manager()
            pending_manager.save_pending(
                user_id=self.current_user_id,
                order_id=order_id,
                guest_name=guest_name,
                phone=phone
            )
            
            return {"status": "not_found", "order_id": order_id}

        # 4. Extract Order ID (different logic for PMS vs Gmail)
        if data_source == 'pms':
            # PMS data is already clean and structured
            pms_id = order_info['data']['booking_id']
            ota_id = order_info['data'].get('ota_booking_id', '')
            
            # ✨ 檢查是否有待匹配的暫存資料
            from helpers.pending_guest import get_pending_guest_manager
            pending_manager = get_pending_guest_manager()
            pending_data = pending_manager.find_pending(self.current_user_id, ota_id or pms_id)
            
            if pending_data:
                print(f"🔗 找到待匹配的暫存資料: {pending_data}")
                
                # ✨ 正式同步資料至 SQLite 與 JSON 日誌
                sync_order_details(
                    order_id=pms_id, # 正式同步時使用 PMS ID
                    data={
                        "guest_name": pending_data.get('guest_name'),
                        "phone": pending_data.get('phone'),
                        "arrival_time": pending_data.get('arrival_time'),
                        "line_user_id": self.current_user_id,
                        "line_display_name": pending_data.get('line_display_name') or getattr(self, 'current_display_name', None)
                    },
                    logger=self.logger,
                    pms_client=self.pms_client
                )
                
                # 標記為已匹配
                pending_manager.mark_matched(self.current_user_id, pending_data['provided_order_id'])
                # 將暫存資料加入返回結果
                order_info['pending_matched'] = pending_data
            
            # DEBUG: 輸出完整的 API 返回資料
            print(f"🔍 DEBUG - API Response Data: {order_info['data']}")
            print(f"🔍 DEBUG - pms_id: {pms_id}, ota_id: '{ota_id}', order_id: {order_id}")
            
            # 优先使用客人输入的号码来确认（如果匹配 OTA 订单号）
            if ota_id and (order_id in ota_id or ota_id in order_id):
                found_id = ota_id  # 使用 OTA 订单号确认
                found_subject = f"OTA Order: {ota_id}"
                print(f"📋 Using OTA Order ID for confirmation: {found_id}")
            else:
                found_id = pms_id  # 使用 PMS 订单号
                found_subject = f"PMS Order: {pms_id}"
                print(f"📋 Using PMS Order ID: {pms_id}")
        else:
            # Gmail data needs extraction (original logic)
            found_subject = order_info.get('subject', 'Unknown')
            found_id = order_info.get('order_id', 'Unknown')
            
            # Always try to extract the most complete NUMERIC order ID from subject
            import re
            # Look for long numeric sequences (10+ digits preferred, min 6 digits)
            patterns = [
                r'訂單編號[：:]?\s*(?:[A-Z]+)?(\d{6,})',  # Optional colon
                r'編號[：:]?\s*(?:[A-Z]+)?(\d{6,})',
                r'Booking\s+ID[：:]?\s*(?:[A-Z]+)?(\d{6,})',
                r'\b(?:RM[A-Z]{2})?(\d{10,})\b',  # Optional RMAG prefix
                r'\b(\d{10,})\b'  # Pure long number
            ]
            
            extracted_id = None
            for pattern in patterns:
                match = re.search(pattern, found_subject)
                if match:
                    extracted = match.group(1)  # Get ONLY the digits
                    # Verify this contains the user's query
                    if order_id in extracted or extracted in order_id:
                        extracted_id = extracted
                        print(f"📋 Extracted numeric order ID: {extracted_id}")
                        break
            
            # Use extracted numeric ID if it's longer/more complete
            if extracted_id:
                # Remove any non-digit characters from extracted_id
                extracted_id = re.sub(r'\D', '', extracted_id)
                if found_id == 'Unknown' or len(extracted_id) > len(re.sub(r'\D', '', found_id)):
                    found_id = extracted_id
            elif found_id == 'Unknown':
                # Final fallback: extract digits from order_id or subject
                numeric_only = re.sub(r'\D', '', order_id)
                if numeric_only:
                    found_id = numeric_only
                else:
                    found_id = order_id
        
        # 2. Confirmation Step (Safety + Correctness)
        if not user_confirmed:
            # 總是要求用戶確認訂單，確保訂單狀態最新且正確
            # 即使是強匹配也需要確認，因為訂單可能已取消或修改
            print(f"🔍 Found Order: ID={order_id}, Found={found_id}, Subject={found_subject}")
            
            # 總是返回 confirmation_needed，讓 AI 詢問客人確認
            result = {
                "status": "confirmation_needed",
                "found_order_id": found_id,
                "found_subject": found_subject,
                "message": f"I found an order with ID {found_id}. Please ask the user if this is correct."
            }
            
            # ✨ 如有匹配的暫存資料，加入提示
            if order_info.get('pending_matched'):
                pending = order_info['pending_matched']
                result['pending_matched'] = {
                    "phone": pending.get('phone', ''),
                    "arrival_time": pending.get('arrival_time', ''),
                    "special_requests": pending.get('special_requests', ''),
                    "note": f"您之前查詢時已提供的資料：電話 {pending.get('phone', '無')}、抵達時間 {pending.get('arrival_time', '無')}。訂單確認後將自動補上。"
                }
            
            return result

        # 3. Privacy & Detail Step (Only if Confirmed)
        from datetime import datetime, timedelta
        today_str = datetime.now().strftime("%Y-%m-%d")
            
        if data_source == 'pms':
            # PMS data: Simple privacy check based on check-in date
            try:
                check_in_date = order_info['data']['check_in_date']
                check_in = datetime.strptime(check_in_date, '%Y-%m-%d')
                today = datetime.strptime(today_str, '%Y-%m-%d')
                days_ago = (today - check_in).days
                
                if days_ago > 5:
                    print(f"🚫 Blocking Old PMS Order (Over 5 days): {found_id}")
                    return {
                        "status": "blocked",
                        "reason": "privacy_protection",
                        "message": "System Alert: This order is historical (Check-in > 5 days ago). Access Denied."
                    }
                
                print(f"✅ Privacy Check Passed for PMS Order: {found_id}")
                    
                # Build response from PMS structured data
                order_data = order_info['data']
                
                # 构建房号信息
                room_numbers = order_data.get('room_numbers', [])
                room_no_text = ', '.join(room_numbers) if room_numbers else '尚未安排'
                
                # 构建房型信息（不含人数）
                rooms_info = []
                for room in order_data.get('rooms', []):
                    room_name = room.get('room_type_name') or room.get('room_type_code', '').strip()
                    room_count = room.get('room_count', 1)
                    room_text = f"{room_name} x{room_count}"
                    rooms_info.append(room_text)
                rooms_text = '\n                    '.join(rooms_info) if rooms_info else '無'
                
                # 订金信息（只显示已付订金）
                deposit_paid = order_data.get('deposit_paid', 0)
                deposit_text = ""
                if deposit_paid and deposit_paid > 0:
                    deposit_text = f"\n                    已付訂金: NT${deposit_paid:,.0f}"
                
                # OTA 訂單號 (套用清理邏輯)
                ota_id = order_data.get('ota_booking_id', '')
                display_ota = clean_ota_id(ota_id)
                display_order_id = display_ota if display_ota else order_data['booking_id']
                
                # 訂房來源 (套用共用辨識邏輯)
                booking_source = detect_booking_source(
                    remarks=order_data.get('remarks', ''),
                    ota_id=ota_id
                )
                
                # 組合姓名：優先使用 Last Name + First Name
                last_name = order_data.get('guest_last_name', '').strip()
                first_name = order_data.get('guest_first_name', '').strip()
                if last_name and first_name:
                    full_name = f"{last_name}{first_name}"
                else:
                    full_name = order_data.get('guest_name', '')
                
                # 訂單狀態檢查
                status_name = order_data.get('status_name', '未知')
                status_code = order_data.get('status_code', '')
                
                # 如果訂單已取消，只顯示取消訊息並立即返回
                if status_code.strip() == 'D' or '取消' in status_name:
                    return {
                        "status": "cancelled",
                        "order_id": display_id if 'display_id' in locals() else order_data.get('booking_id'),
                        "message": """⚠️ 訂單狀態：已取消

此訂單已經取消，無法辦理入住。
如有疑問，請聯繫櫃檯：(03) 832-5700"""
                    }
                else:
                    # 正常訂單：顯示核對資訊
                    
                    # 构建房型信息（只显示中文名稱）
                    rooms_info = []
                    for room in order_data.get('rooms', []):
                        room_code = (room.get('ROOM_TYPE_CODE') or room.get('room_type_code') or '').strip()
                        
                        # 優先從 SSOT 獲取中文名稱
                        room_meta = ROOM_TYPES.get(room_code, {})
                        room_name = room_meta.get('zh', room.get('ROOM_TYPE_NAME') or room.get('room_type_name') or room_code)
                        
                        room_count = room.get('ROOM_COUNT') or room.get('room_count', 1)
                        room_text = f"{room_name} x{room_count}"
                        rooms_info.append(room_text)
                    
                    # 如果 rooms 為空，嘗試從 remarks 解析房型
                    if not rooms_info and remarks:
                        import re
                        # 匹配「產品名稱: 官網優惠價SD」或類似格式
                        room_match = re.search(r'產品名稱[：:]\s*[^/]*?([A-Z]{2,3})(?:\s|/|$)', remarks)
                        if room_match:
                            room_code = room_match.group(1).strip()
                            if room_code in ROOM_TYPES:
                                room_name = ROOM_TYPES[room_code]['zh']
                                rooms_info.append(f"{room_name} x1")
                    
                    rooms_text = '\n                    '.join(rooms_info) if rooms_info else '無'
                    
                    # 早餐資訊 (套用共用邏輯)
                    breakfast = get_breakfast_info(
                        remarks=order_data.get('remarks', ''),
                        rooms=order_data.get('rooms', [])
                    )
                    
                    # 組合顯示訊息
                    # 只顯示 OTA 編號 (去掉前綴)，如果沒有則回退到 booking_id
                    display_id = clean_ota_id if clean_ota_id else order_data.get('booking_id', '未知')
                    
                    # 電話格式化 (套用共用邏輯)
                    formatted_phone = normalize_phone(order_data.get('contact_phone', ''))
                    
                    clean_body = f"""
                訂單來源: {booking_source}
                預約編號: {display_id}
                訂房人姓名: {full_name}
                聯絡電話: {formatted_phone}
                入住日期: {order_data['check_in_date']}
                退房日期: {order_data['check_out_date']} (共 {order_data['nights']} 晚)
                房型: {rooms_text}
                早餐: {breakfast}
                """
                
            except Exception as e:
                print(f"❌ PMS Privacy check error: {e}")
                return {
                    "status": "blocked",
                    "reason": "system_error",
                    "message": "Privacy verification system encountered an error."
                }
                
        else:
            # Gmail data: Original LLM-based privacy check
            body = order_info.get('body', '')

            # Remove sensitive blocks first (CSS/Script)
            clean_body = re.sub(r'<style.*?>.*?</style>', '', body, flags=re.DOTALL | re.IGNORECASE)
            clean_body = re.sub(r'<script.*?>.*?</script>', '', clean_body, flags=re.DOTALL | re.IGNORECASE)
            # Remove remaining tags
            clean_body = re.sub(r'<[^>]+>', ' ', clean_body)
            # Collapse whitespace
            clean_body = re.sub(r'\s+', ' ', clean_body).strip()
            
            print(f"📧 Cleaned Email Body Preview (First 500 chars):\n{clean_body[:500]}") # Debug Log

            validation_prompt = f"""
            Task: Check-in Date Privacy Verification.
            
            Current Date: {today_str}
            Email Text Content:
            {clean_body[:3000]}
            
            Instructions:
            1. Search for "Check-in" or "入住日期" in the content.
            2. Extract the date text (e.g., "Dec 14, 2025" or "2025-12-14").
            3. Parse it to YYYY-MM-D.
            4. Calculate DAYS_AGO = Current Date - Check-in Date.
            5. Logic:
               - If Check-in Date is in the FUTURE (DAYS_AGO < 0): ALLOW (Result: YES)
               - If DAYS_AGO >= 0 and DAYS_AGO <= 5: ALLOW (Result: YES)
               - If DAYS_AGO > 5: BLOCK (Result: NO)
               - If Date Not Found: BLOCK (Result: NO)
            
            Examples:
            - Today: 2025-12-11, Check-in: 2025-12-14 → DAYS_AGO = -3 → ALLOW (Future booking)
            - Today: 2025-12-11, Check-in: 2025-12-10 → DAYS_AGO = 1 → ALLOW (Recent)
            - Today: 2025-12-11, Check-in: 2025-12-05 → DAYS_AGO = 6 → BLOCK (Too old)
            
            Output Required Format:
            REASON: [Found Date: X, Days Ago: Y, Decision: Valid/Invalid because...]
            RESULT: [YES/NO]
            """
            
            try:
                # Use the Validator Model
                validator_response = self.validator_model.generate_content(validation_prompt)
                full_response = validator_response.text.strip()
                print(f"🤔 Validator Thought Process:\n{full_response}")
                
                # Parse Result (handle both "RESULT: YES" and "RESULT: [YES]")
                match = re.search(r'RESULT:\s*\[?(YES|NO)\]?', full_response, re.IGNORECASE)
                result = match.group(1).upper() if match else 'NO'
                
                print(f"🔒 Privacy Validator Final Decision: {result} (Today: {today_str})")
                    
                if result != 'YES':
                    # Block it
                    print(f"🚫 Blocking Old Order (Over 5 days): {found_id}")
                    return {
                        "status": "blocked",
                        "reason": "privacy_protection",
                        "message": "System Alert: This order is historical (Check-in > 5 days ago). Access Denied."
                    }
                    
            except Exception as e:
                # FAIL SAFE: If validation fails, BLOCK access rather than allowing.
                return {
                    "status": "blocked",
                    "reason": "system_error",
                    "message": "System Alert: Privacy verification system encountered an error. Access temporarily denied to prevent data leak."
                }

        # PASSED! User is allowed to see the order details.
        print(f"✅ Privacy Check Passed for Order: {found_id}")
        
        # 儲存訂單資料到 JSON
        order_data = {
            'order_id': found_id,
            'line_user_id': self.current_user_id,
            'subject': found_subject,
            'body': clean_body if clean_body else 'N/A',
            'check_in': None,
            'check_out': None,
            'room_type': None,
            'guest_name': None,
            'booking_source': None
        }
        
        # 從 body 提取基本資訊 (If search from Gmail)
        if data_source == 'gmail':
            import re as regex_lib
            from datetime import datetime as dt
            
            # 提取入住日期
            checkin_match = regex_lib.search(r'Check-in.*?(\d{1,2}-[A-Za-z]{3}-\d{4})', clean_body)
            if checkin_match:
                try:
                    date_obj = dt.strptime(checkin_match.group(1), '%d-%b-%Y')
                    order_data['check_in'] = date_obj.strftime('%Y-%m-%d')
                except:
                    pass
            
            if not order_data['check_in']:
                checkin_match2 = regex_lib.search(r'Check-in.*?(\d{4}-\d{2}-\d{2})', clean_body)
                if checkin_match2:
                    order_data['check_in'] = checkin_match2.group(1)
            
            # 提取退房日期
            checkout_match = regex_lib.search(r'Check-out.*?(\d{1,2}-[A-Za-z]{3}-\d{4})', clean_body)
            if checkout_match:
                try:
                    date_obj = dt.strptime(checkout_match.group(1), '%d-%b-%Y')
                    order_data['check_out'] = date_obj.strftime('%Y-%m-%d')
                except:
                    pass
            
            if not order_data['check_out']:
                checkout_match2 = regex_lib.search(r'Check-out.*?(\d{4}-\d{2}-\d{2})', clean_body)
                if checkout_match2:
                    order_data['check_out'] = checkout_match2.group(1)
            
            # 提取客人姓名
            name_match = regex_lib.search(r'Customer First Name.*?[：:]\s*([A-Za-z\s]+?)(?:\s+Customer|$)', clean_body)
            if name_match:
                order_data['guest_name'] = name_match.group(1).strip()
            else:
                name_match2 = regex_lib.search(r'姓名[：:]\s*([^\n,]+?)(?:\s*,|\s*電話|$)', clean_body)
                if name_match2:
                    order_data['guest_name'] = name_match2.group(1).strip()

            # 提取電話號碼
            phone_match = regex_lib.search(r'電話[：:]\s*(09\d{8})', clean_body)
            if not phone_match:
                phone_match = regex_lib.search(r'\b(09\d{8})\b', clean_body)
            if phone_match:
                order_data['phone'] = phone_match.group(1)
            
            # 提取房型
            room_match = regex_lib.search(r'\b((?:Standard|Deluxe|Superior|Executive|Family|VIP|Premium|Classic|Ocean View|Sea View|Economy|Accessible|Disability Access)\s+(?:Single|Double|Twin|Triple|Quadruple|Family|Suite|Queen Room)?\s*(?:Room|Suite)?[^,\n]*?(?:Non-Smoking|Smoking|with.*?View|with.*?Balcony)?)', clean_body, regex_lib.IGNORECASE)
            if not room_match:
                room_match = regex_lib.search(r'\b(Quadruple Room - Disability Access|Double Room - Disability Access|Double Room with Balcony and Sea View|Quadruple Room with Sea View|Superior Queen Room with Two Queen Beds)', clean_body, regex_lib.IGNORECASE)
            
            if room_match:
                raw_room_type = room_match.group(1).strip()
                raw_room_type = regex_lib.sub(r'\s+\d+\s*$', '', raw_room_type)
                raw_room_type = regex_lib.sub(r'\s+No\..*$', '', raw_room_type)
                raw_room_type = regex_lib.sub(r'\s+', ' ', raw_room_type).strip()
                order_data['room_type'] = raw_room_type
            
            # 提取訂房來源
            if 'agoda' in clean_body.lower():
                order_data['booking_source'] = 'Agoda'
            elif 'booking.com' in clean_body.lower():
                order_data['booking_source'] = 'Booking'
        
        # 儲存訂單
        try:
            self.logger.save_order(order_data)
            if self.current_user_id:
                self.logger.link_order_to_user(found_id, self.current_user_id)
        except Exception as e:
            print(f"⚠️ Failed to save order: {e}")
        
        return {
            "status": "found",
            "order_id": found_id,
            "subject": found_subject,
            "body": clean_body,
            "formatted_display": clean_body,
            "NEXT_RESPONSE_INSTRUCTION": f"""
🚨🚨🚨 IMMEDIATE ACTION REQUIRED 🚨🚨🚨

YOU MUST FOLLOW THIS EXACT OUTPUT SEQUENCE:

STEP 1: Output the following EXACT TEXT (訂單詳情):
{clean_body}

STEP 2: ONLY AFTER showing all above details, then add weather and contact.

❌ DO NOT skip Step 1
❌ DO NOT go directly to "🌤️ 溫馨提醒"
❌ DO NOT go directly to "系統顯示您的聯絡電話"

✅ You MUST output Step 1 FIRST, then Step 2
"""
        }


    def update_guest_info(self, order_id: str, info_type: str, content: str):
        """
        Updates guest information for an existing order.
        
        Args:
            order_id: The order ID
            info_type: Type of information ('phone', 'arrival_time', 'special_need')
            content: The content to update
        
        Returns:
            Dict with success status
        """
        print(f"🔧 Tool Called: update_guest_info(order_id={order_id}, type={info_type}, content={content})")
        
        # 驗證訂單是否存在
        if order_id not in self.logger.orders:
            return {
                "status": "error",
                "message": f"Order {order_id} not found in database. Please check the order first."
            }
        
        # 確保訂單有 line_user_id（從當前用戶獲取）
        if hasattr(self, 'current_user_id') and self.current_user_id:
            if 'line_user_id' not in self.logger.orders[order_id] or not self.logger.orders[order_id]['line_user_id']:
                self.logger.orders[order_id]['line_user_id'] = self.current_user_id
                print(f"📝 已記錄 line_user_id: {self.current_user_id}")
        
        # 更新資料
        success = self.logger.update_guest_request(order_id, info_type, content)
        
        if success:
            print(f"✅ Successfully updated {info_type} for order {order_id}")
            return {
                "status": "success",
                "message": f"Successfully saved {info_type}"
            }
        else:
            print(f"❌ Failed to update {info_type} for order {order_id}")
            return {
                "status": "error",
                "message": "Failed to save information. Please try again."
            }

    # ============================================
    # 當日預訂 Functions (Same-Day Booking)
    # ============================================

    def check_today_availability(self):
        """
        查詢今日可預訂的房型和數量。
        當客人表達想要預訂當日入住時，使用此工具查詢房況。
        
        Returns:
            Dict containing available room types and their counts
        """
        print(f"🔧 Tool Called: check_today_availability()")
        
        result = self.pms_client.get_today_availability()
        
        if not result or not result.get('success'):
            return {
                "status": "error",
                "message": "目前無法查詢房況，請稍後再試"
            }
        
        available_rooms = result.get('data', {}).get('available_room_types', [])
        
        # 只顯示標準房型
        standard_rooms = []
        room_mapping = {
            'SD': {'name': '標準雙人房', 'price': 2280, 'capacity': 2, 'beds': ['一大床', '兩小床']},
            'ST': {'name': '標準三人房', 'price': 2880, 'capacity': 3, 'beds': ['一大一小', '三小床']},
            'SQ': {'name': '標準四人房', 'price': 3680, 'capacity': 4, 'beds': ['兩大床', '四小床']}
        }
        
        for room in available_rooms:
            code = room.get('room_type_code')
            if code in room_mapping:
                info = room_mapping[code]
                standard_rooms.append({
                    'code': code,
                    'name': info['name'],
                    'price': info['price'],
                    'available': room.get('available_count', 0),
                    'bed_options': info['beds']
                })
        
        return {
            "status": "success",
            "date": result.get('data', {}).get('date'),
            "rooms": standard_rooms,
            "instructions": """
請用以下格式向客人展示房況，並詢問想預訂的房型：

📋 今日可預訂房型：
• 標準雙人房 - NT$2,280/晚（含早餐）
• 標準三人房 - NT$2,880/晚（含早餐）
• 標準四人房 - NT$3,680/晚（含早餐）

客人可以說：
- 直接說房型：「雙人房」、「四人房」
- 說數量：「兩間雙人」、「1間四人1間雙人」
"""
        }

    def create_same_day_booking(
        self,
        rooms: str,
        guest_name: str,
        phone: str,
        arrival_time: str,
        bed_type: str = None,
        special_requests: str = None
    ):
        """
        建立當日入住預訂。收集完所有必要資訊後使用此工具。
        
        Args:
            rooms: 房型和數量，支援多種格式：
                   - 單一房型：「雙人房」、「2間雙人房」
                   - 多房型：「標準雙人房 x 2, 標準四人房 x 1」或「2間雙人1間四人」
            guest_name: 客人姓名
            phone: 聯絡電話（台灣手機格式 09xxxxxxxx）
            arrival_time: 預計抵達時間
            bed_type: 床型偏好（可選）
            special_requests: 特殊需求（可選，如嬰兒床、停車位）
            
        Returns:
            Dict with booking result
        """
        import re
        from datetime import datetime
        
        print(f"🔧 Tool Called: create_same_day_booking(rooms={rooms}, name={guest_name}, phone={phone}, time={arrival_time})")
        
        # 驗證電話格式
        phone_clean = re.sub(r'[-\s]', '', phone)
        if not re.match(r'^09\d{8}$', phone_clean):
            return {
                "status": "error",
                "message": f"電話格式不正確：{phone}。台灣手機應為 09 開頭的 10 位數字。請請客人確認電話。"
            }
        
        # 房型代碼轉換
        room_codes = {
            '雙人': 'SD', '雙人房': 'SD', 'SD': 'SD', '標準雙人房': 'SD',
            '三人': 'ST', '三人房': 'ST', 'ST': 'ST', '標準三人房': 'ST',
            '四人': 'SQ', '四人房': 'SQ', 'SQ': 'SQ', '標準四人房': 'SQ'
        }
        room_names = {'SD': '標準雙人房', 'ST': '標準三人房', 'SQ': '標準四人房'}
        prices = {'SD': 2280, 'ST': 2880, 'SQ': 3680}
        
        # 解析房型字串（支援多種格式）
        parsed_rooms = []
        
        # 嘗試解析「標準雙人房 x 2, 標準四人房 x 1」格式
        pattern1 = r'(標準?[雙三四]人房?)\s*[xX×]\s*(\d+)'
        matches1 = re.findall(pattern1, rooms)
        
        if matches1:
            for room_type, count in matches1:
                room_code = room_codes.get(room_type)
                if room_code:
                    parsed_rooms.append({'code': room_code, 'name': room_names[room_code], 'count': int(count)})
        else:
            # 嘗試解析「2間雙人1間四人」格式
            pattern2 = r'(\d+)\s*間?\s*(雙人房?|三人房?|四人房?)'
            matches2 = re.findall(pattern2, rooms)
            
            if matches2:
                for count, room_type in matches2:
                    room_code = room_codes.get(room_type)
                    if room_code:
                        parsed_rooms.append({'code': room_code, 'name': room_names[room_code], 'count': int(count)})
            else:
                # 單一房型格式
                room_code = room_codes.get(rooms.strip())
                if room_code:
                    parsed_rooms.append({'code': room_code, 'name': room_names[room_code], 'count': 1})
        
        print(f"   解析結果: {parsed_rooms}")
        
        if not parsed_rooms:
            return {
                "status": "error",
                "message": f"無法識別房型：{rooms}。請指定：標準雙人房、標準三人房或標準四人房"
            }
        
        # 建立訂單
        now = datetime.now()
        order_id = f"WI{now.strftime('%m%d%H%M')}"
        
        total_price = 0
        room_summary = []
        all_success = True
        
        # 解析 bed_type 字串（格式如：「標準三人房: 三小床, 標準四人房: 兩大床」）
        bed_type_map = {}
        if bed_type:
            # 嘗試解析 "房型: 床型, 房型: 床型" 格式
            parts = re.split(r',\s*', bed_type)
            for part in parts:
                if ':' in part or '：' in part:
                    # 分割房型和床型
                    room_bed = re.split(r'[:：]\s*', part.strip())
                    if len(room_bed) >= 2:
                        room_name_key = room_bed[0].strip()
                        bed_value = room_bed[1].strip()
                        # 轉換為房型代碼
                        room_code_key = room_codes.get(room_name_key)
                        if room_code_key:
                            bed_type_map[room_code_key] = bed_value
            print(f"   床型解析: {bed_type_map}")
        
        for i, room in enumerate(parsed_rooms):
            item_id = f"{order_id}-{i+1}"
            
            # 為每個房型找到對應的床型
            room_bed_type = bed_type_map.get(room['code'], bed_type if not bed_type_map else None)
            
            booking_data = {
                'order_id': order_id,
                'item_id': item_id,
                'room_type_code': room['code'],
                'room_type_name': room['name'],
                'room_count': room['count'],
                'bed_type': room_bed_type,
                'special_requests': special_requests,
                'nights': 1,
                'guest_name': guest_name,
                'phone': phone_clean,
                'arrival_time': arrival_time,
                'line_user_id': self.current_user_id,
                'line_display_name': None
            }

            
            result = self.pms_client.create_same_day_booking(booking_data)
            
            if result and result.get('success'):
                total_price += prices.get(room['code'], 0) * room['count']
                room_summary.append(f"{room['name']} x {room['count']} 間")
            else:
                all_success = False
        
        if all_success and room_summary:
            return {
                "status": "success",
                "order_id": order_id,
                "message": f"""
🎉 預訂成功！

📋 訂單編號：{order_id}
🏨 房型：
{chr(10).join('   • ' + r for r in room_summary)}
💰 總計：NT${total_price:,}（含早餐）
📅 入住日期：{now.strftime('%Y-%m-%d')}（今日）
👤 姓名：{guest_name}
📞 電話：{phone_clean}
🕐 抵達時間：{arrival_time}
{f"📝 特殊需求：{special_requests}" if special_requests else ""}

⚠️ 提醒：當日預訂免收訂金，請務必準時抵達！
"""
            }
        else:
            return {
                "status": "error",
                "message": "預訂失敗，請稍後再試或聯繫櫃檯。"
            }

    def get_weather_forecast(self, date_str: str):
        """
        Gets the weather forecast for Checheng Township on a specific date.
        :param date_str: Date in 'YYYY-MM-DD' format.
        """
        print(f"🔧 Tool Called: get_weather_forecast(date_str={date_str})")
        return self.weather_helper.get_weather_forecast(date_str)

    def get_weekly_forecast(self):
        """
        Gets the weekly weather forecast for Checheng Township.
        Returns a formatted string with 7-day forecast.
        """
        print(f"🔧 Tool Called: get_weekly_forecast()")
        return self.weather_helper.get_weekly_forecast()

    def handle_image(self, user_id, image_data, display_name=None):
        """Handles image input using Gemini Vision."""
        if display_name:
            self.logger.save_profile(user_id, display_name)

        if not hasattr(self, 'model'):
            return "【系統錯誤】尚未設定 GOOGLE_API_KEY，無法辨識圖片。"

        try:
            # 檢查是否為內部 VIP，委託給 VIPServiceHandler 處理
            if self.vip_service and self.vip_service.is_internal(user_id):
                vip_response = self.vip_service.handle_image(user_id, image_data, display_name)
                if vip_response:
                    return vip_response
            
            # 一般客人：只找訂單編號
            image = Image.open(io.BytesIO(image_data))
            prompt = """請分析這張圖片。
1. 如果圖片中包含「訂單編號」或「Order ID」，請提取出來。
2. 告訴我你找到了什麼編號。"""
            
            # For vision, we use the separate vision model to avoid tool calling interference
            response = self.vision_model.generate_content([prompt, image])
            text = response.text.strip()
            print(f"Gemini Vision Result: {text}")
            
            # Log the image interaction
            self.logger.log(user_id, "User", "[傳送了一張圖片]")
            self.logger.log(user_id, "Bot (Vision)", text)
            
            # If we found a number, we can suggest the user to check it
            match = re.search(r'(\d{5,})', text)
            if match:
                found_id = match.group(1)
                # Store this ID in context for the next turn
                self.user_context[user_id] = {"pending_order_id": found_id}
                return f"我從圖片中看到了訂單編號 {found_id}。請問您是要查詢這筆訂單嗎？"
            else:
                return text

        except ValueError as ve:
            # Gemini API returned finish_reason != STOP (usually due to token limit or safety filter)
            error_msg = str(ve)
            print(f"❌ Gemini ValueError: {error_msg}")
            
            # Check if it's a finish_reason=1 error (token limit exceeded)
            if "finish_reason" in error_msg or "The candidate's" in error_msg:
                print(f"⚠️ Token limit likely exceeded for user {user_id}. Auto-resetting conversation...")
                
                # Automatically reset the user's conversation
                self.reset_conversation(user_id)
                
                # Return a friendly message explaining what happened
                reply = """對話歷史已自動清除，以確保系統正常運作。

請再次提供您的訂單編號，我將為您重新查詢。謝謝！😊"""
                self.logger.log(user_id, "Bot", reply)
                return reply
            
            # Other ValueError
            reply = f"【受邀回覆】不好意思，剛才連線有點問題，請您再說一次好嗎？😊"
            self.logger.log(user_id, "Bot", reply)
            return reply

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Vision Error: {e}")
            return "【客服回覆】\n圖片處理發生錯誤，請稍後再試。"

    def _get_recent_conversation_summary(self, user_id, max_turns=20):
        """
        讀取用戶最近的對話記錄並生成摘要
        
        Args:
            user_id: 用戶 ID
            max_turns: 讀取最近幾輪對話（預設 20 輪）
        
        Returns:
            str: 對話摘要，None 表示無歷史記錄
        """
        try:
            # 讀取日誌
            logs = self.logger.get_logs(user_id)
            
            if logs == "尚無對話紀錄 (No logs found).":
                return None
            
            # 解析日誌格式: [時間] 【發送者】\n訊息\n-----
            import re
            pattern = r'\[([^\]]+)\] 【([^】]+)】\n(.*?)(?=\n-{5,}|\Z)'
            matches = re.findall(pattern, logs, re.DOTALL)
            
            if not matches:
                return None
            
            # 只取最近的對話（max_turns 輪 = max_turns*2 則訊息，因為每輪包含用戶+Bot）
            recent_messages = matches[-(max_turns * 2):]
            
            # 提取關鍵資訊
            conversation_lines = []
            found_order_ids = []  # 改為列表，記錄所有訂單號（客人可能訂過多次）
            
            for timestamp, sender, message in recent_messages:
                # 清理訊息內容
                clean_message = message.strip()
                
                # 限制每則訊息長度（避免 token 過多）
                if len(clean_message) > 200:
                    clean_message = clean_message[:200] + "..."
                
                # 提取訂單號（可能有多筆）
                order_matches = re.findall(r'\b(16\d{8}|25\d{8})\b', clean_message)
                for order_id in order_matches:
                    if order_id not in found_order_ids:  # 避免重複
                        found_order_ids.append(order_id)
                
                # 記錄對話
                conversation_lines.append(f"[{sender}]: {clean_message}")
            
            # 生成摘要
            summary = "Recent conversation history (last {} turns):\n".format(len(conversation_lines) // 2)
            summary += "\n".join(conversation_lines[-40:])  # 最多顯示最近 40 則訊息
            
            # 如果找到訂單號，特別標註（可能有多筆）
            if found_order_ids:
                if len(found_order_ids) == 1:
                    summary += f"\n\n**Important Context**: User's current order ID is {found_order_ids[0]}"
                else:
                    summary += f"\n\n**Important Context**: User has multiple orders: {', '.join(found_order_ids)} (most recent: {found_order_ids[-1]})"
            
            print(f"📖 Loaded {len(recent_messages)} messages from chat history for user {user_id}")
            if found_order_ids:
                print(f"📌 Found {len(found_order_ids)} order ID(s) in history: {', '.join(found_order_ids)}")
            
            return summary
            
        except Exception as e:
            print(f"⚠️ Error reading conversation history: {e}")
            return None

    def get_user_session(self, user_id, use_chat_mode: bool = None):
        """
        Retrieves or creates a chat session for the given user.
        
        Args:
            user_id: LINE User ID
            use_chat_mode: 
                - True: 使用聊天版 model (temperature 0.5)
                - False: 使用嚴謹版 model (temperature 0.2)
                - None: 根據狀態機自動判斷
        """
        # 自動判斷模式
        if use_chat_mode is None:
            state = self.state_machine.get_state(user_id)
            # 閒置狀態 = 聊天模式，其他狀態 = 嚴謹模式
            use_chat_mode = (state == 'idle')
        
        # 選擇對應的 model
        model = self.model_chat if use_chat_mode else self.model
        mode_name = "Chat(0.5)" if use_chat_mode else "Strict(0.2)"
        
        # Session key 包含模式，確保切換模式時重建 session
        session_key = f"{user_id}_{mode_name}"
        
        if session_key not in self.user_sessions:
            print(f"Creating new {mode_name} session for user: {user_id}")
            self.user_sessions[session_key] = model.start_chat(enable_automatic_function_calling=True)
        
        return self.user_sessions[session_key]

    def reset_conversation(self, user_id):
        """重置用戶對話：清除 chat session 和對話歷史"""
        # 刪除 chat session（下次會重新創建）
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            print(f"✅ Reset chat session for user: {user_id}")
        
        # 清除用戶上下文
        if user_id in self.user_context:
            del self.user_context[user_id]
            print(f"✅ Cleared context for user: {user_id}")
        
        # 清除對話日誌（保留歷史記錄但標記為新對話）
        self.logger.log(user_id, "System", "=== 對話已重新開始 ===")
        print(f"🔄 User {user_id} conversation resetted")

    def _is_booking_intent_without_order(self, message: str, user_id: str) -> bool:
        """
        判斷是否為訂房意圖但沒有訂單編號
        
        Args:
            message: 用戶訊息
            user_id: 用戶 ID
            
        Returns:
            True 如果是訂房意圖且沒有訂單編號
        """
        # 檢查是否包含訂單編號 (5位數以上)
        if re.search(r'\b\d{5,}\b', message):
            return False  # 有訂單編號，走一般查詢流程
        
        # 排除：查詢訂單相關
        exclude_keywords = ['我有訂', '已經訂', '查訂單', '我的訂單', '確認訂單']
        if any(kw in message for kw in exclude_keywords):
            return False
        
        # 檢查是否有訂房關鍵字
        booking_keywords = [
            '訂房', '預訂', '今天住', '今日住', '有房', '還有房',
            '空房', '想住', '要住', '可以住', '今天訂', '今日訂',
            '今天', '今日'  # 單獨說「今天」也視為訂房意圖
        ]
        return any(kw in message for kw in booking_keywords)
    
    # 注意：VIP 相關函數已遷移至 handlers/vip_service_handler.py

    def _has_order_number(self, message: str) -> bool:
        """檢查訊息中是否包含訂單編號（排除電話號碼）"""
        from helpers import IntentDetector
        return IntentDetector.has_order_number(message)

    def generate_response(self, user_question, user_id="default_user", display_name=None):
        # 設定當前用戶 ID 與名稱，供工具函數使用
        self.current_user_id = user_id
        self.current_display_name = display_name
        
        # 記錄收到訊息 (Bot 內部 LOG)
        self.bot_logger.log_receive(user_id, "text", user_question)
        
        # Save profile if provided
        if display_name:
            self.logger.save_profile(user_id, display_name)

        # Log User Input (對話記錄)
        self.logger.log(user_id, "User", user_question)

        # ============================================
        # 路由邏輯 - 決定使用哪個處理器
        # ============================================
        
        # 優先檢查 1: 訂單查詢處理器 (處理進行中流程 或 新的訂單編號)
        has_order = self._has_order_number(user_question)
        # 優先檢查是否在訂單查詢流程中
        if self.order_query_handler.is_active(user_id) or has_order:
            order_response = self.order_query_handler.handle_message(user_id, user_question, display_name)
            if order_response:
                self.logger.log(user_id, "Bot", order_response)
                return order_response
        
        # 檢查是否在當日預訂流程中
        if self.state_machine.get_active_handler_type(user_id) == 'same_day_booking':
            booking_response = self.same_day_handler.handle_message(user_id, user_question, display_name)
            if booking_response:
                self.logger.log(user_id, "Bot", booking_response)
                return booking_response

        # 注意：雖然 AI 可以處理部分情境，但狀態機處理器在「進行中流程」具有最高優先權
        
        # ============================================
        # 內部 VIP 專屬功能 (Internal VIP Functions)
        # ============================================
        # 使用 VIPServiceHandler 統一處理 VIP 功能
        if self.vip_service and self.vip_service.is_internal(user_id):
            # 優先檢查 VIP 服務是否有待處理狀態
            if self.vip_service.is_active(user_id):
                vip_response = self.vip_service.handle_message(user_id, user_question, display_name)
                if vip_response:
                    self.logger.log(user_id, "Bot", vip_response)
                    return vip_response
            
            # 檢查是否為內部 VIP 指令
            vip_response = self.vip_service.handle_message(user_id, user_question, display_name)
            if vip_response:
                self.logger.log(user_id, "Bot", vip_response)
                return vip_response
        # ============================================

        # Check for pending context (e.g. Order ID from previous image)
        context = self.user_context.get(user_id, {})
        pending_id = context.get("pending_order_id")
        
        # Inject Current Date to help Gemini understand "Today", "Tomorrow"
        today_str = datetime.now().strftime("%Y-%m-%d")
        weekday_map = {0: '一', 1: '二', 2: '三', 3: '四', 4: '五', 5: '六', 6: '日'}
        weekday_str = weekday_map[datetime.now().weekday()]
        system_time_context = f"\n(System Info: Current Date is {today_str} 星期{weekday_str})"
        
        # Append context to user question (invisible to user in chat, but visible to LLM)
        user_question_with_context = user_question + system_time_context
        
        if pending_id:
            # Inject context into the prompt so the AI knows what "Yes" refers to
            print(f"Injecting pending Order ID: {pending_id}")
            user_question_with_context += f"\n(System Note: The user previously uploaded an image containing Order ID {pending_id}. If the user is confirming or saying 'yes', please use this ID to call check_order_status.)"
            # Clear only the pending_id to avoid stuck state, but keep current_order_id
            if user_id in self.user_context and 'pending_order_id' in self.user_context[user_id]:
                del self.user_context[user_id]['pending_order_id']
        
        # Inject current order_id if exists (for context tracking across topic changes)
        current_order_id = context.get("current_order_id")
        if current_order_id:
            print(f"📌 Current active Order ID: {current_order_id}")
            user_question_with_context += f"\n(System Note: The current active Order ID is {current_order_id}. If the user provides arrival time, special requests, or any guest information, use this Order ID when calling update_guest_info.)"

        if not hasattr(self, 'model'):
            return "【系統錯誤】尚未設定 GOOGLE_API_KEY，無法使用 AI 回覆。"

        try:
            # Get user-specific session
            chat_session = self.get_user_session(user_id)
            
            # **NEW**: 讀取歷史對話記錄（即使重啟也能恢復記憶）
            # 如果是新建立的 session（剛重啟或新用戶），嘗試載入歷史
            conversation_summary = self._get_recent_conversation_summary(user_id)
            if conversation_summary:
                user_question_with_context += f"\n\n(System Context - {conversation_summary})"
            
            # Send message to Gemini
            print(f"🤖 Sending to Gemini (Tools Enabled: True)...") # Assuming tools are always enabled for chat sessions
            response = chat_session.send_message(user_question_with_context)
            print("🤖 Gemini Response Received.")

            # Check if order was queried - if yes, save it as current_order_id
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        # 記錄工具調用 (Bot 內部 LOG)
                        tool_name = part.function_call.name
                        tool_args = dict(part.function_call.args) if part.function_call.args else {}
                        self.bot_logger.log_tool_call(tool_name, tool_args)
                        
                        if part.function_call.name == 'check_order_status':
                            # Extract order_id from function call
                            order_id_arg = part.function_call.args.get('order_id', '')
                            if order_id_arg:
                                # Check if this is a NEW order (different from current)
                                old_order_id = self.user_context.get(user_id, {}).get('current_order_id')
                                if old_order_id and old_order_id != order_id_arg:
                                    print(f"🔄 Order Switch Detected: {old_order_id} → {order_id_arg}")
                                    # Clear any pending collection state for the old order
                                    # This prevents mixing data between different orders
                                
                                print(f"🔖 Saving current_order_id: {order_id_arg}")
                                if user_id not in self.user_context:
                                    self.user_context[user_id] = {}
                                self.user_context[user_id]['current_order_id'] = order_id_arg
                                # Mark when this order was queried (for staleness detection)
                                self.user_context[user_id]['order_query_time'] = datetime.now()
            
            reply_text = response.text
            
            # 記錄 Bot 回應 (Bot 內部 LOG)
            self.bot_logger.log_response(user_id, reply_text)
            
            # Log Bot Response (對話記錄)
            self.logger.log(user_id, "Bot", reply_text)
            
            return reply_text
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Gemini API Error: {e}")
            print(f"📋 Full Error Traceback:\n{error_details}")
            
            # 記錄錯誤 (Bot 內部 LOG)
            self.bot_logger.log_error("GEMINI_API", str(e)[:200], user_id)
            
            # 記錄錯誤到對話 LOG (供管理員除錯,但不發送給客戶)
            error_log = f"[系統錯誤] Gemini API 異常: {str(e)[:200]}"
            self.logger.log(user_id, "System Error", error_log)
            
            # Reset session for this user to recover from error state
            print(f"🔄 Resetting session for user: {user_id} due to error")
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            
            # 不回覆任何訊息,讓客戶重新發送
            # 這樣可以避免客戶看到「連線有點問題」這種不專業的訊息
            # 返回空字串,由 app.py 判斷是否要發送訊息
            return ""  # 返回空字串,app.py 需要檢查並跳過發送

    def handle_audio(self, user_id, audio_content, display_name):
        """
        處理語音訊息：
        1. 儲存音訊檔案
        2. 使用 Gemini 聽打 (Transcribe)
        3. 將文字送入 generate_response 處理
        """
        import tempfile
        
        print(f"🎤 收到來自 {display_name} ({user_id}) 的語音訊息")
        
        # 1. Save audio to temporary file
        # LINE audio is usually m4a
        with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp_file:
            for chunk in audio_content.iter_content():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
            
        try:
            # 2. Upload to Gemini
            print(f"📤 上傳音訊到 Gemini: {tmp_path}")
            audio_file = genai.upload_file(path=tmp_path)
            
            # 3. Transcribe
            # Note: We use the Flash model because it's fast and multimodal
            prompt = "請仔細聆聽這段音訊，並將其精確轉寫為繁體中文（台灣用語）。只需輸出純文字，不要加入任何說明、標點符號以外的額外內容。"
            
            response = self.model.generate_content([prompt, audio_file])
            transcribed_text = response.text.strip()
            
            print(f"📝 語音轉文字結果: {transcribed_text}")
            
            if not transcribed_text:
                return "抱歉，我聽不太清楚您的語音訊息，可以請您用文字再說一次嗎？"
                
            # 4. Log the voice message
            self.logger.log(user_id, "User (Voice)", transcribed_text)
            
            # 5. Process as Text
            return self.generate_response(transcribed_text, user_id, display_name)
            
        except Exception as e:
            print(f"❌ Audio processing error: {e}")
            return "抱歉，語音處理發生錯誤，請稍後再試或直接輸入文字。"
        finally:
            # Cleanup local file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                print("🧹 暫存音訊檔案已清理")

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "..", "data")
    kb_path = os.path.join(data_dir, "knowledge_base.json")
    persona_path = os.path.join(base_dir, "persona.md")

    bot = HotelBot(kb_path, persona_path)

    print("\n--- 模擬 LINE@ 對話視窗 (輸入 'exit' 離開) ---")
    print("Agent: 您好！我是您的專屬客服，請問有什麼我可以幫您的嗎？")
    
    # Simulate a user ID for local testing
    user_id = "local_test_user"

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ['exit', 'quit', '離開']:
            print("Agent: 謝謝您的來訊，期待再次為您服務！")
            break
        
        response = bot.generate_response(user_input, user_id)
        print(f"Agent: {response}")

if __name__ == "__main__":
    main()


