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
            
            # Construct System Instruction (從獨立模組載入)
            from prompts import get_system_prompt
            kb_str = json.dumps(self.knowledge_base, ensure_ascii=False, indent=2)
            self.system_instruction = get_system_prompt(self.persona, kb_str)
            
            
            # Configure safety settings to avoid over-blocking normal hotel conversations
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
            }
            
            # Generation config for Gemini 3 (官方建議維持 temperature=1.0)
            # 參考: https://ai.google.dev/gemini-api/docs/gemini-3
            generation_config_pro = {
                'temperature': 1.0,  # Gemini 3 官方建議值，低於 1.0 可能導致迴圈問題
            }
            
            # Generation config for Flash (快速回應用途)
            generation_config_flash = {
                'temperature': 1.0,  # Gemini 3 官方建議值
            }
            
            # Main model: Gemini 3 Pro (訂單查詢、Function Calling、複雜推理)
            # Pro 版適合「需要跨模態進階推理的複雜工作」
            self.model = genai.GenerativeModel(
                model_name='gemini-3-pro-preview',
                tools=self.tools,
                system_instruction=self.system_instruction,
                safety_settings=safety_settings,
                generation_config=generation_config_pro
            )
            
            # Chat model: Gemini 3 Flash (一般對話、VIP 服務、快速回應)
            self.model_chat = genai.GenerativeModel(
                model_name='gemini-3-flash-preview',
                tools=self.tools,
                system_instruction=self.system_instruction,
                safety_settings=safety_settings,
                generation_config=generation_config_flash
            )
            print("✅ HotelBot initialized (Pro: gemini-3-pro-preview, Flash: gemini-3-flash-preview)")
            
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
            
            # 🔧 方案 C：啟動時自動重試匹配暫存資料
            try:
                from helpers.pending_guest import retry_pending_matches
                matched = retry_pending_matches(self.pms_client, self.logger)
                if matched > 0:
                    print(f"🔄 啟動時自動匹配了 {matched} 筆暫存資料")
            except Exception as e:
                print(f"⚠️ 啟動時重試匹配失敗: {e}")
            
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
        Checks the status of an order (Wrapper - 委派給 OrderQueryHandler)
        
        Args:
            order_id: The order ID provided by the user.
            guest_name: (Optional) Guest name for double-checking.
            phone: (Optional) Contact phone for double-checking.
            user_confirmed: Set to True after user confirms the order.
        
        Returns:
            Dict with order status and details
        """
        print(f"🔧 Tool Called: check_order_status(order_id={order_id}, confirmed={user_confirmed})")
        
        # 委派給 Handler 處理
        return self.order_query_handler.query_for_ai(
            user_id=self.current_user_id,
            order_id=order_id,
            guest_name=guest_name,
            phone=phone,
            user_confirmed=user_confirmed,
            display_name=getattr(self, 'current_display_name', None)
        )

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
        
        # 🆕 漸進式暫存：意圖確認，立刻記錄 LINE 資訊
        if hasattr(self, 'current_user_id') and self.current_user_id:
            from datetime import datetime
            order_id = f"WI{datetime.now().strftime('%m%d%H%M')}"
            try:
                self.pms_client.create_same_day_booking({
                    'order_id': order_id,
                    'line_user_id': self.current_user_id,
                    'line_display_name': getattr(self, 'current_display_name', ''),
                    'status': 'incomplete',
                    'room_type_code': '',
                    'room_count': 0,
                    'guest_name': '',
                    'phone': '',
                    'arrival_time': ''
                })
                # 保存到 context 供後續更新使用
                if not hasattr(self, 'user_context'):
                    self.user_context = {}
                self.user_context[self.current_user_id] = {'pending_order_id': order_id}
                print(f"📝 漸進式暫存：意圖確認，已建立 {order_id}")
            except Exception as e:
                print(f"⚠️ 漸進式暫存失敗: {e}")
        
        result = self.pms_client.get_today_availability()
        
        if not result or not result.get('success'):
            return {
                "status": "error",
                "message": "目前無法查詢房況，請稍後再試"
            }
        
        available_rooms = result.get('data', {}).get('available_room_types', [])
        day_type_name = result.get('data', {}).get('day_type_name', '平日')
        
        # 房型靜態資訊（不含價格，價格由 API 動態回傳）
        standard_rooms = []
        room_info_map = {
            'SD': {'name': '標準雙人房', 'capacity': 2, 'beds': ['一大床', '兩小床']},
            'ST': {'name': '標準三人房', 'capacity': 3, 'beds': ['一大一小', '三小床']},
            'SQ': {'name': '標準四人房', 'capacity': 4, 'beds': ['兩大床', '四小床']}
        }
        
        for room in available_rooms:
            code = room.get('room_type_code')
            if code in room_info_map:
                info = room_info_map[code]
                # 價格使用 API 回傳的動態價格（含當日加價）
                price = room.get('price', 0)
                standard_rooms.append({
                    'code': code,
                    'name': info['name'],
                    'price': price,
                    'base_price': room.get('base_price', price),
                    'surcharge': room.get('surcharge', 0),
                    'available': room.get('available_count', 0),
                    'bed_options': info['beds']
                })
        
        # 動態組裝房價展示文字
        price_lines = []
        for r in standard_rooms:
            price_text = f"NT${r['price']:,}/晚（含早餐）"
            if r['surcharge'] > 0:
                price_text += f"（含{day_type_name}加價 NT${r['surcharge']:,}）"
            price_lines.append(f"• {r['name']} - {price_text}")
        price_display = "\n".join(price_lines) if price_lines else "（查詢中...）"
        # 儲存查詢結果供 same_day_booking 的 _parse_rooms_for_ai 使用
        availability_result = {
            "status": "success",
            "date": result.get('data', {}).get('date'),
            "day_type": result.get('data', {}).get('day_type', 'N'),
            "day_type_name": day_type_name,
            "rooms": standard_rooms,
            "instructions": f"""
請用以下格式向客人展示房況，並詢問想預訂的房型：

📋 今日可預訂房型（{day_type_name}）：
{price_display}

客人可以說：
- 直接說房型：「雙人房」、「四人房」
- 說數量：「兩間雙人」、「1間四人1間雙人」
"""
        }
        self.last_availability = availability_result
        return availability_result

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
        建立當日入住預訂 (Wrapper - 委派給 SameDayBookingHandler)
        """
        print(f"🔧 Tool Called: create_same_day_booking(rooms={rooms}, name={guest_name})")
        
        # 取得之前暫存的 order_id（如果有）
        pending_order_id = None
        if hasattr(self, 'user_context') and self.current_user_id in self.user_context:
            pending_order_id = self.user_context[self.current_user_id].get('pending_order_id')
            print(f"📝 沿用之前的 order_id: {pending_order_id}")
        
        return self.same_day_handler.create_booking_for_ai(
            user_id=self.current_user_id,
            rooms=rooms,
            guest_name=guest_name,
            phone=phone,
            arrival_time=arrival_time,
            bed_type=bed_type,
            special_requests=special_requests,
            display_name=getattr(self, 'current_display_name', None),
            pending_order_id=pending_order_id  # 沿用之前的 order_id
        )

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
            
            # 只提取訂單編號，不回傳其他圖片分析內容
            match = re.search(r'(\d{5,})', text)
            if match:
                found_id = match.group(1)
                # Store this ID in context for the next turn
                self.user_context[user_id] = {"pending_order_id": found_id}
                return f"我從圖片中看到了訂單編號 {found_id}。請問您是要查詢這筆訂單嗎？"
            else:
                # 找不到訂單編號 → 不分析圖片內容，引導客人用文字溝通
                return "感謝您傳送圖片！如果您想查詢訂單，請提供訂單編號或傳送含有訂單編號的截圖。若有其他需求，歡迎直接用文字告訴我 😊"

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
        2. 使用 OpenAI Whisper API 轉文字（比 Gemini 更準確，無幻覺問題）
        3. 將文字送入 generate_response 處理
        """
        import tempfile
        from openai import OpenAI
        
        print(f"🎤 收到來自 {display_name} ({user_id}) 的語音訊息")
        
        # 1. Save audio to temporary file
        # LINE audio is usually m4a
        with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp_file:
            for chunk in audio_content.iter_content():
                tmp_file.write(chunk)
            tmp_path = tmp_file.name
            
        try:
            # 2. 使用 OpenAI Whisper API 轉文字
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                print("❌ OPENAI_API_KEY 未設定")
                return "抱歉，語音服務暫時無法使用，請用文字輸入。"
            
            client = OpenAI(api_key=openai_key)
            
            print(f"📤 上傳音訊到 OpenAI Whisper: {tmp_path}")
            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="zh",  # 指定繁體中文
                    response_format="text"
                )
            
            transcribed_text = transcript.strip() if isinstance(transcript, str) else transcript.text.strip()
            
            print(f"📝 語音轉文字結果 (Whisper): {transcribed_text}")
            
            if not transcribed_text:
                return "抱歉，我聽不太清楚您的語音訊息，可以請您用文字再說一次嗎？"
                
            # 3. Log the voice message
            self.logger.log(user_id, "User (Voice)", transcribed_text)
            
            # 4. Process as Text
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


