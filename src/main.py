"""
with4gent - LINE Bot with OpenAI Integration
Version: 2.1.0
"""

from flask import Flask, abort, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from src.config import config
from src.logic import ChatbotLogic
from src.services.line_service import LineService
from src.services.openai_service import OpenAIService

app = Flask(__name__)

# サービスの初期化
line_service = LineService(config.line_channel_access_token)
openai_service = OpenAIService(config.openai_api_key)
chatbot_logic = ChatbotLogic(line_service, openai_service)

handler = WebhookHandler(config.line_channel_secret)


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック用エンドポイント"""
    return {"status": "ok"}


@app.route("/webhook", methods=["POST"])
def webhook():
    """LINE Webhook エンドポイント"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """テキストメッセージを処理"""
    chatbot_logic.process_event(event)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.port)
