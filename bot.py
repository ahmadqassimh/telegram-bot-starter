import os
import asyncio
import logging
from telethon import TelegramClient, events
import google.generativeai as genai
from flask import Flask
from threading import Thread

# ====== Keep Alive ======
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running."

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# ====== Config from environment ======
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
SESSION_NAME = 'user'

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PRIVATE_CHANNEL = int(os.getenv("PRIVATE_CHANNEL"))

SOURCE_CHANNELS = [
    'aeeeioo',
    -1001878871385,
    -1001609322224,
    -1001941966833,
]

# ====== Logging ======
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== Gemini + Telethon Init ======
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def authenticate():
    await client.connect()
    if await client.is_user_authorized():
        logger.info("✅ Logged in via saved session.")
        return
    try:
        await client.send_code_request(PHONE_NUMBER)
        code = input("🔢 Enter the code sent to your Telegram: ").strip()
        await client.sign_in(PHONE_NUMBER, code)
        logger.info("✅ Authentication successful.")
    except Exception as e:
        logger.error(f"❌ Login failed: {e}")
        await client.disconnect()
        exit(1)

async def format_signal(text):
    prompt = f"""
تنسيق هذه التوصية بشكل احترافي ضمن القالب التالي:

🔔 <الزوج> <BUY أو SELL>

📊 AT: <سعر الدخول>
❌ SL: <سعر وقف الخسارة>
✅ TP1: <الهدف الأول>

⚠️ الصفقة عالية المخاطر، عليك بإدارة رأس المال.

---

التوصية:
{text}

أعد تنسيقها ضمن القالب أعلاه فقط، بدون أي شرح إضافي. إذا كانت التوصية غير مفهومة لا ترد.
"""
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        if result.startswith("🔔") and "SL" in result:
            return result
    except Exception as e:
        logger.error(f"⚠️ Gemini error: {e}")
    return None

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handle_source_message(event):
    text = event.message.text
    if not text:
        return

    logger.info(f"📩 Message from {event.chat_id}")
    formatted = await format_signal(text)
    if formatted:
        await client.send_message(PRIVATE_CHANNEL, formatted)
        logger.info("📤 Sent formatted signal.")
    else:
        logger.info("⚠️ Skipped: Could not format message.")

async def main():
    print("🤖 Bot starting...")
    await authenticate()
    await client.run_until_disconnected()

if __name__ == "__main__":
    keep_alive()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped.")
