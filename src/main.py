"""
with4gent - LINE Bot with OpenAI Integration
Version: 1.0.0
"""

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    MarkMessagesAsReadByTokenRequest
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from openai import OpenAI
import os

app = Flask(__name__)

# LINE設定
line_config = Configuration(access_token=os.environ.get('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET'))

# OpenAI設定
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# セッションごとの前回レスポンスID
previous_responses = {}


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック用エンドポイント"""
    return {'status': 'ok'}


@app.route('/webhook', methods=['POST'])
def webhook():
    """LINE Webhook エンドポイント"""
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'


def mark_as_read(api_client: ApiClient, mark_as_read_token: str):
    """メッセージを既読にする"""
    if not mark_as_read_token:
        return
    
    try:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.mark_messages_as_read_by_token(
            MarkMessagesAsReadByTokenRequest(
                mark_as_read_token=mark_as_read_token
            )
        )
    except Exception as e:
        # 既読処理の失敗はログのみ、処理は継続
        app.logger.warning(f"Failed to mark as read: {e}")


def get_openai_response(user_id: str, user_message: str) -> str:
    """OpenAI APIからレスポンスを取得"""
    try:
        if user_id not in previous_responses:
            response = openai_client.responses.create(
                model="gpt-4o-mini",
                input=user_message,
                store=True,
                tools=[{"type": "web_search"}]
            )
        else:
            response = openai_client.responses.create(
                model="gpt-4o-mini",
                input=user_message,
                previous_response_id=previous_responses[user_id],
                tools=[{"type": "web_search"}]
            )
        
        previous_responses[user_id] = response.id
        return response.output_text
    
    except Exception as e:
        app.logger.error(f"OpenAI API error: {e}")
        return "申し訳ございません。エラーが発生しました。しばらくしてからもう一度お試しください。"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """テキストメッセージを処理"""
    user_id = event.source.user_id
    user_message = event.message.text
    mark_as_read_token = getattr(event.message, 'mark_as_read_token', None)
    
    with ApiClient(line_config) as api_client:
        # 既読をつける
        mark_as_read(api_client, mark_as_read_token)
        
        # OpenAIからレスポンスを取得
        bot_message = get_openai_response(user_id, user_message)
        
        # LINE返信
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=bot_message)]
            )
        )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
