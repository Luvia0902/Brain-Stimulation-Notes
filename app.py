import os
import asyncio
import logging
import threading
import time
from flask import Flask, request, abort
from dotenv import load_dotenv

# 引入 LINE Bot SDK
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 引入 NotebookLM Unofficial API
from notebooklm import NotebookLMClient

# 1. 環境變數設定 (讀取 .env)
# ---------------------------------------------------------
load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
NOTEBOOK_ID = os.getenv('NOTEBOOK_ID')
GOOGLE_AUTH_FILE = os.getenv('GOOGLE_AUTH_FILE', 'storage_state.json')

# 免責聲明：用於回覆訊息時提醒使用者
DISCLAIMER = "\n\n(免責聲明：此資訊僅供輔助參考，臨床決策請依專業判斷)"

# 初始化 Flask
app = Flask(__name__)

# 初始化 LINE Bot API
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 設定 Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. 初始化全域 NotebookLM Client (加速版)
# ---------------------------------------------------------
# 我們將使用一個背景線程來運行 asyncio loop，並保持一個長連線的 client
global_client = None
background_loop = None

async def init_notebook_client():
    """
    非同步初始化 Client 並保持連線 (不呼叫 __aexit__)
    """
    global global_client
    logger.info("正在初始化 NotebookLM Client...")
    try:
        # 建立 Client 實例
        client = await NotebookLMClient.from_storage(path=GOOGLE_AUTH_FILE)
        # 手動呼叫 __aenter__ 來建立 Session 且不關閉
        await client.__aenter__()
        global_client = client
        logger.info("NotebookLM Client 初始化成功！連線已建立。")
    except Exception as e:
        logger.error(f"NotebookLM Client 初始化失敗: {e}")

def start_background_loop(loop):
    """
    在背景線程運行的 Event Loop
    """
    asyncio.set_event_loop(loop)
    # 先初始化 client
    loop.run_until_complete(init_notebook_client())
    # 讓 loop 永遠執行，等待來自 Flask 的任務
    loop.run_forever()

# 啟動背景線程
background_loop = asyncio.new_event_loop()
t = threading.Thread(target=start_background_loop, args=(background_loop,), daemon=True)
t.start()

async def query_notebooklm_async(user_query):
    """
    這是跑在背景 loop 的非同步函式
    """
    if not global_client:
        return "系統啟動中或連線失敗，請稍後再試。"
    
    try:
        prompt = f"{user_query} 請根據論文內容，以繁體中文提供給醫師專業的詳細解答，並附上關鍵數據。"
        logger.info(f"查詢 NotebookLM: {user_query}")
        
        # 使用已建立的長連線進行查詢
        answer_obj = await global_client.chat.ask(NOTEBOOK_ID, prompt)
        return answer_obj.answer
    except Exception as e:
        logger.error(f"查詢錯誤: {e}")
        # 如果是連線過期等問題，這裡可能需要重連機制的邏輯，但暫時先回報錯誤
        return None

# 3. 處理 LINE Webhook
# ---------------------------------------------------------
@app.route("/callback", methods=['POST'])
def callback():
    # 取得 X-Line-Signature 標頭值
    signature = request.headers.get('X-Line-Signature')

    # 取得請求內容作為文字
    body = request.get_data(as_text=True)
    logger.info("Request body: " + body)

    # 處理 Webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 4. 核心問答邏輯
# ---------------------------------------------------------
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """
    當收到文字訊息時觸發
    """
    user_msg = event.message.text.strip()
    user_id = event.source.user_id
    reply_token = event.reply_token
    
    logger.info(f"收到訊息: {user_msg}")

    # 4.1 呼叫 NotebookLM (跨線程呼叫)
    try:
        # 將查詢任務丟進背景的 Loop 執行，並等待結果 (Future)
        #這會暫停目前的 Flask 線程直到取得結果，這是預期的行為
        future = asyncio.run_coroutine_threadsafe(
            query_notebooklm_async(user_msg), 
            background_loop
        )
        
        # 設定超時時間，避免 Line Server Timeout (通常是 60秒內要回，但安全起見設 55)
        answer = future.result(timeout=55)
        
        if answer:
            final_reply = f"{answer}{DISCLAIMER}"
        else:
            final_reply = "系統忙碌中或無法讀取資料，請稍後再試。"

        # 4.2 回覆使用者
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text=final_reply)
        )
        logger.info("回覆成功")

    except TimeoutError:
        logger.error("查詢超時")
        # 超時通常代表 NotebookLM 處理太久，Line 可能已經斷線
        # 我們可以嘗試 push message 補救，但這裡先不做
    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {e}")
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="系統發生錯誤，請稍後再試。")
        )

# 啟動程式入口
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
