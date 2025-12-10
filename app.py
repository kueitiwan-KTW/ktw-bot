import os
import sys
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage, StickerMessage, StickerSendMessage

# Load environment variables from .env file
load_dotenv()

# Import our HotelBot class
# Ensure bot.py is in the same directory
from bot import HotelBot

app = Flask(__name__)

# Load environment variables
# You need to set these in your environment or .env file
CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_ACCESS_TOKEN')
CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET', 'YOUR_CHANNEL_SECRET')

if CHANNEL_ACCESS_TOKEN == 'YOUR_ACCESS_TOKEN' or CHANNEL_SECRET == 'YOUR_CHANNEL_SECRET':
    print("Warning: LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_SECRET is not set.")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# Initialize HotelBot
base_dir = os.path.dirname(os.path.abspath(__file__))
kb_path = os.path.join(base_dir, "knowledge_base.json")
persona_path = os.path.join(base_dir, "persona.md")
hotel_bot = HotelBot(kb_path, persona_path)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers.get('X-Line-Signature')

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text.strip()
    user_id = event.source.user_id
    
    # Get User Profile (Display Name)
    display_name = None
    try:
        profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name
    except Exception as e:
        print(f"Error getting profile: {e}")
    
    # Check for reset command
    if user_msg.lower() in ['重新開始', 'reset', 'restart', '清除對話']:
        # Reset chat session for this user
        hotel_bot.reset_conversation(user_id)
        reply_text = "好的！已為您重新開始對話。有什麼能為您服務的嗎？😊"
    else:
        # Generate response using HotelBot
        reply_text = hotel_bot.generate_response(user_msg, user_id, display_name)
    
    
    # Remove Markdown formatting (LINE doesn't support it)
    import re
    reply_text = re.sub(r'\*\*', '', reply_text)  # Remove **
    reply_text = re.sub(r'__', '', reply_text)    # Remove __
    reply_text = re.sub(r'(?<!\*)\*(?!\*)', '', reply_text)  # Remove single * (but not **)
    reply_text = re.sub(r'_', '', reply_text)     # Remove _
    
    # Reply via LINE Messaging API
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    
    # Get User Profile (Display Name)
    display_name = None
    try:
        profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name
    except Exception as e:
        print(f"Error getting profile: {e}")

    message_content = line_bot_api.get_message_content(event.message.id)
    image_data = message_content.content
    
    # Generate response using HotelBot's image handler
    reply_text = hotel_bot.handle_image(user_id, image_data, display_name)
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    user_id = event.source.user_id
    sticker_id = event.message.sticker_id
    package_id = event.message.package_id
    
    # Get User Profile (Display Name)
    display_name = None
    try:
        profile = line_bot_api.get_profile(user_id)
        display_name = profile.display_name
        hotel_bot.logger.save_profile(user_id, display_name)
    except Exception as e:
        print(f"Error getting profile: {e}")
    
    # Log the sticker message
    hotel_bot.logger.log(user_id, "User", f"[傳送貼圖 Package: {package_id}, Sticker: {sticker_id}]")
    
    # Reply with a friendly sticker (LINE official sticker)
    hotel_bot.logger.log(user_id, "Bot", "[回應貼圖: 微笑揮手]")
    
    line_bot_api.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id='11537',  # LINE 官方「Brown & Cony」貼圖包
            sticker_id='52002735'  # 微笑揮手的貼圖
        )
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
