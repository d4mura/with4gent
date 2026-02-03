from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MarkMessagesAsReadByTokenRequest,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)


class LineService:
    def __init__(self, access_token: str):
        self.configuration = Configuration(access_token=access_token)

    def reply_message(self, reply_token: str, text: str):
        # 300文字を超える場合は分割、最大500文字に制限
        messages_to_send = self._split_message(text)

        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=m) for m in messages_to_send],
                )
            )

    def _split_message(self, text: str) -> list[str]:
        if not text:
            return [""]

        # 160文字ごとに分割（20文字×8行相当の視認性を考慮）
        limit = 160
        chunks = []
        for i in range(0, len(text), limit):
            chunk = text[i : i + limit].strip()
            if chunk:
                chunks.append(chunk)

        return chunks if chunks else [""]

    def mark_as_read(self, mark_as_read_token: str):
        if not mark_as_read_token:
            return
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.mark_messages_as_read_by_token(
                MarkMessagesAsReadByTokenRequest(mark_as_read_token=mark_as_read_token)
            )

    def get_message_content(self, message_id: str) -> str:
        """メッセージIDからテキスト内容を取得（テキストメッセージのみ）"""
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            try:
                # 注: get_message_content はバイナリデータを返すが、
                # テキストメッセージの場合はAPIの制限で取得できない場合がある。
                # ただし、ドキュメントによっては取得可能とされていることもある。
                # 実際には、Webhookで受信したメッセージのみが対象。
                response = line_bot_api.get_message_content(message_id)
                # もしバイナリとして返ってくるならデコードを試みる
                if hasattr(response, "data"):
                    return response.data.decode("utf-8")
                return str(response)
            except Exception:
                return ""

    def leave_group(self, group_id: str):
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.leave_group(group_id)

    def leave_room(self, room_id: str):
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.leave_room(room_id)

    def get_bot_info(self) -> str:
        """ボットの情報を取得し、表示名を返す"""
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            try:
                response = line_bot_api.get_bot_info()
                return response.display_name
            except Exception:
                return "with4gent"
