from typing import List, Tuple

from linebot.v3.webhooks import MessageEvent, TextMessageContent

from src.services.line_service import LineService
from src.services.openai_service import OpenAIService


class ChatbotLogic:
    def __init__(self, line_service: LineService, openai_service: OpenAIService):
        self.line = line_service
        self.ai = openai_service

    def process_event(self, event: MessageEvent):
        if not isinstance(event.message, TextMessageContent):
            return

        context_key = self._get_context_key(event)
        raw_text = event.message.text or ""
        mark_as_read_token = getattr(event.message, "mark_as_read_token", None)

        # 既読処理
        try:
            self.line.mark_as_read(mark_as_read_token)
        except Exception:
            # 既読処理に失敗しても、返信処理を継続するためにエラーを握り潰す
            pass

        # group/room ではメンション必須
        mentioned = self._is_mentioned_to_me(event)
        if self._is_group_like(event) and not mentioned:
            return

        ranges = self._self_mention_ranges(event.message)
        clean_text = self._strip_self_mentions(raw_text, ranges)

        # /exit コマンド判定
        if self._is_exit_command(clean_text):
            self.ai.clear_session(context_key)
            if not self._is_group_like(event):
                self.line.reply_message(
                    event.reply_token, "会話セッションをリセットしました。"
                )
            else:
                self.line.reply_message(
                    event.reply_token, "了解。セッションを消去して退出します。"
                )
                self._leave_chat_if_needed(event)
            return

        # 通常会話
        user_message = clean_text if clean_text else raw_text
        try:
            bot_message = self.ai.get_response(context_key, user_message)
            self.line.reply_message(event.reply_token, bot_message)
        except Exception:
            self.line.reply_message(
                event.reply_token,
                "申し訳ございません。エラーが発生しました。しばらくしてからもう一度お試しください。",
            )

    def _get_context_key(self, event: MessageEvent) -> str:
        src = event.source
        if src.type == "group":
            return f"group:{src.group_id}"
        if src.type == "room":
            return f"room:{src.room_id}"
        return f"user:{src.user_id}"

    def _is_group_like(self, event: MessageEvent) -> bool:
        return event.source.type in ("group", "room")

    def _is_mentioned_to_me(self, event: MessageEvent) -> bool:
        return len(self._self_mention_ranges(event.message)) > 0

    def _self_mention_ranges(
        self, message: TextMessageContent
    ) -> List[Tuple[int, int]]:
        mention = getattr(message, "mention", None)
        if not mention:
            return []
        mentionees = getattr(mention, "mentionees", None)
        if not mentionees:
            return []

        ranges: List[Tuple[int, int]] = []
        for m in mentionees:
            if getattr(m, "is_self", False) or getattr(m, "isSelf", False):
                idx = getattr(m, "index", None)
                ln = getattr(m, "length", None)
                if isinstance(idx, int) and isinstance(ln, int):
                    ranges.append((idx, idx + ln))
        return ranges

    def _strip_self_mentions(self, text: str, ranges: List[Tuple[int, int]]) -> str:
        if not ranges:
            return text.strip()
        ranges_sorted = sorted(ranges, key=lambda x: x[0], reverse=True)
        s = text
        for start, end in ranges_sorted:
            if 0 <= start < end <= len(s):
                s = s[:start] + s[end:]
        return s.strip()

    def _is_exit_command(self, clean_text: str) -> bool:
        return clean_text.lower() in ("/exit", "/bye")

    def _leave_chat_if_needed(self, event: MessageEvent) -> None:
        src = event.source
        if src.type == "group":
            self.line.leave_group(src.group_id)
        elif src.type == "room":
            self.line.leave_room(src.room_id)
