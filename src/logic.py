from collections import deque
from typing import Deque, Dict, List, Tuple

from linebot.v3.webhooks import JoinEvent, MessageEvent, TextMessageContent

from src.services.line_service import LineService
from src.services.openai_service import OpenAIService
from src.utils.anonymizer import anonymize_text


class ChatbotLogic:
    def __init__(self, line_service: LineService, openai_service: OpenAIService):
        self.line = line_service
        self.ai = openai_service
        # メッセージIDからテキスト内容を引くためのキャッシュ（引用解決用）
        self._message_cache: Dict[str, str] = {}  # {message_id: text}
        # コンテキストごとの会話履歴（メンションなしメッセージも含む）
        self._context_history: Dict[str, Deque[Tuple[str, str]]] = {}
        # コンテキストごとのメッセージ受信累計（サマライズ用）
        self._message_counts: Dict[str, int] = {}
        # コンテキストごとのサマリー履歴
        self._context_summaries: Dict[str, Deque[str]] = {}

    def process_event(self, event: MessageEvent):
        if not isinstance(event.message, TextMessageContent):
            return

        context_key = self._get_context_key(event)
        raw_text = event.message.text or ""
        self._update_caches(event, context_key, raw_text)

        # 既読処理
        mark_as_read_token = getattr(event.message, "mark_as_read_token", None)
        try:
            self.line.mark_as_read(mark_as_read_token)
        except Exception:
            pass

        # group/room ではメンション必須
        mentioned = self._is_mentioned_to_me(event)
        if self._is_group_like(event) and not mentioned:
            return

        clean_text = self._get_clean_text(event.message, raw_text)

        # /exit コマンド判定
        if self._is_exit_command(clean_text):
            self._handle_exit_command(event, context_key)
            return

        # 通常会話
        user_message = self._prepare_ai_input(context_key, clean_text, raw_text)
        self._send_ai_response(event, context_key, user_message)

    def _update_caches(self, event: MessageEvent, context_key: str, raw_text: str):
        message_id = getattr(event.message, "id", None)
        user_id = event.source.user_id if event.source.user_id else "unknown"

        # キャッシュに保存（引用解決用）
        if message_id:
            self._message_cache[message_id] = raw_text
            if len(self._message_cache) > 100:
                oldest_key = next(iter(self._message_cache))
                self._message_cache.pop(oldest_key)

        # コンテキスト履歴に保存
        if context_key not in self._context_history:
            self._context_history[context_key] = deque(maxlen=10)
        self._context_history[context_key].append((user_id, raw_text))

        # メッセージカウントの更新とサマライズ判定
        self._message_counts[context_key] = self._message_counts.get(context_key, 0) + 1
        if self._message_counts[context_key] % 10 == 0:
            summary = self.ai.summarize(context_key)
            if summary:
                if context_key not in self._context_summaries:
                    self._context_summaries[context_key] = deque(maxlen=10)
                self._context_summaries[context_key].append(summary)

    def _get_clean_text(self, message: TextMessageContent, raw_text: str) -> str:
        ranges = self._self_mention_ranges(message)
        clean_text = self._strip_self_mentions(raw_text, ranges)

        # 引用（リプライ）情報の取得
        quote_text = self._get_quote_text(message)
        if quote_text:
            clean_text = f'引用メッセージ: "{quote_text}"\n質問: {clean_text}'
        return clean_text

    def _handle_exit_command(self, event: MessageEvent, context_key: str):
        self.ai.clear_session(context_key)
        self._message_counts.pop(context_key, None)
        self._context_summaries.pop(context_key, None)
        if not self._is_group_like(event):
            self.line.reply_message(
                event.reply_token, "会話セッションをリセットしました。"
            )
        else:
            self.line.reply_message(
                event.reply_token, "了解。セッションを消去して退出します。"
            )
            self._leave_chat_if_needed(event)

    def _prepare_ai_input(
        self, context_key: str, clean_text: str, raw_text: str
    ) -> str:
        user_message = clean_text if clean_text else raw_text

        # 1. これまでの会話のサマリー（コンテキスト圧縮）
        summaries = self._context_summaries.get(context_key, [])
        summary_lines = []
        if summaries:
            for i, s in enumerate(summaries):
                summary_lines.append(f"要約{i + 1}: {s}")

        # 2. 直近の会話履歴
        history = self._context_history.get(context_key, [])
        context_lines = []
        for h_user_id, h_text in list(history)[:-1]:  # 最新（自分）以外
            h_text_anon = anonymize_text(h_text)
            context_lines.append(f"ユーザー({h_user_id[-4:]}): {h_text_anon}")

        # プロンプトの組み立て
        prompt_parts = []
        if summary_lines:
            prompt_parts.append("---これまでの会話の要約---")
            prompt_parts.extend(summary_lines)
            prompt_parts.append("------------------------")

        if context_lines:
            prompt_parts.append("---直近の会話内容---")
            prompt_parts.extend(context_lines)
            prompt_parts.append("------------------")

        if prompt_parts:
            prompt_parts.append(user_message)
            user_message = "\n".join(prompt_parts)

        return anonymize_text(user_message)

    def _send_ai_response(
        self, event: MessageEvent, context_key: str, user_message: str
    ):
        try:
            bot_message = self.ai.get_response(context_key, user_message)
            bot_message = anonymize_text(bot_message)
            self.line.reply_message(event.reply_token, bot_message)
        except Exception:
            self.line.reply_message(
                event.reply_token,
                "申し訳ございません。エラーが発生しました。しばらくしてからもう一度お試しください。",
            )

    def handle_join(self, event: JoinEvent):
        """グループ/ルーム参加時の処理"""
        bot_name = self.line.get_bot_info()
        help_message = (
            f"招待ありがとうございます！{bot_name}です。\n"
            "私をメンションして話しかけてください。\n"
            "「/exit」もしくは「/bye」でセッションをリセットして退出します。\n\n"
            "よろしくお願いします！"
        )
        self.line.reply_message(event.reply_token, help_message)

    def _get_quote_text(self, message: TextMessageContent) -> str:
        """リプライ元のテキストを取得（キャッシュまたはAPIから）"""
        # SDK v3 では TextMessageContent に quote 属性はない。
        # quoted_message_id (quotedMessageId) が存在する。
        quoted_id = getattr(message, "quoted_message_id", None)
        if quoted_id:
            # 1. まずは自前キャッシュから探す
            if quoted_id in self._message_cache:
                return self._message_cache[quoted_id]
            # 2. キャッシュになければAPIを試みる
            # (画像等の可能性もあるが現状はTextのみ想定)
            return self.line.get_message_content(quoted_id)
        return ""

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
