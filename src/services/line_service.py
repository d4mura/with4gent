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
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=reply_token, messages=[TextMessage(text=text)]
                )
            )

    def mark_as_read(self, mark_as_read_token: str):
        if not mark_as_read_token:
            return
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.mark_messages_as_read_by_token(
                MarkMessagesAsReadByTokenRequest(mark_as_read_token=mark_as_read_token)
            )

    def leave_group(self, group_id: str):
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.leave_group(group_id)

    def leave_room(self, room_id: str):
        with ApiClient(self.configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.leave_room(room_id)
