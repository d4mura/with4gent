import unittest
from unittest.mock import Mock

from linebot.v3.webhooks import (
    GroupSource,
    MessageEvent,
    TextMessageContent,
    UserSource,
)

from src.logic import ChatbotLogic


class TestChatbotLogic(unittest.TestCase):
    def setUp(self):
        self.mock_line = Mock()
        self.mock_ai = Mock()
        self.logic = ChatbotLogic(self.mock_line, self.mock_ai)

    def test_process_event_ignore_non_text(self):
        event = Mock(spec=MessageEvent)
        event.message = Mock()  # Not TextMessageContent
        self.logic.process_event(event)
        self.mock_ai.get_response.assert_not_called()

    def test_exit_command_user_chat(self):
        # ユーザーチャットでの /exit
        event = Mock(spec=MessageEvent)
        event.source = UserSource(user_id="user_123")
        event.message = Mock(spec=TextMessageContent)
        event.message.text = "/exit"
        event.reply_token = "reply_token_123"

        self.logic.process_event(event)

        self.mock_ai.clear_session.assert_called_with("user:user_123")
        self.mock_line.reply_message.assert_called_with(
            "reply_token_123", "会話セッションをリセットしました。"
        )
        self.mock_line.leave_group.assert_not_called()

    def test_exit_command_group_chat(self):
        # グループチャットでの /exit (メンションあり)
        event = Mock(spec=MessageEvent)
        event.source = GroupSource(group_id="group_123")
        # メンション情報をシミュレート
        mention = Mock()
        mentionees = [Mock(is_self=True, index=0, length=4)]
        mention.mentionees = mentionees

        event.message = Mock(spec=TextMessageContent)
        event.message.text = "@bot /exit"
        event.message.mention = mention
        event.reply_token = "reply_token_456"

        self.logic.process_event(event)

        self.mock_ai.clear_session.assert_called_with("group:group_123")
        self.mock_line.reply_message.assert_called_with(
            "reply_token_456", "了解。セッションを消去して退出します。"
        )
        self.mock_line.leave_group.assert_called_with("group_123")

    def test_ignore_group_message_without_mention(self):
        # グループチャットでの通常メッセージ (メンションなし) -> 無視されるべき
        event = Mock(spec=MessageEvent)
        event.source = GroupSource(group_id="group_123")
        event.message = Mock(spec=TextMessageContent)
        event.message.text = "こんにちは"
        # mention属性がない、またはmentioneesが空
        event.message.mention = None

        self.logic.process_event(event)

        self.mock_ai.get_response.assert_not_called()
        self.mock_line.reply_message.assert_not_called()

    def test_normal_conversation_user_chat(self):
        # ユーザーチャットでの通常会話
        event = Mock(spec=MessageEvent)
        event.source = UserSource(user_id="user_123")
        event.message = Mock(spec=TextMessageContent)
        event.message.text = "こんにちは"
        event.reply_token = "reply_token_789"

        self.mock_ai.get_response.return_value = (
            "こんにちは！何かお手伝いしましょうか？"
        )

        self.logic.process_event(event)

        self.mock_ai.get_response.assert_called_with("user:user_123", "こんにちは")
        self.mock_line.reply_message.assert_called_with(
            "reply_token_789", "こんにちは！何かお手伝いしましょうか？"
        )

    def test_mark_as_read_failure_does_not_stop_execution(self):
        # 既読処理が失敗しても続行されること
        event = Mock(spec=MessageEvent)
        event.source = UserSource(user_id="user_123")
        event.message = Mock(spec=TextMessageContent)
        event.message.text = "テスト"
        event.message.mark_as_read_token = "dummy_token"
        event.reply_token = "reply_token"

        self.mock_line.mark_as_read.side_effect = Exception("Read error")
        self.mock_ai.get_response.return_value = "OK"

        self.logic.process_event(event)

        self.mock_line.mark_as_read.assert_called_once()
        self.mock_line.reply_message.assert_called_with("reply_token", "OK")

    def test_strip_self_mentions(self):
        # メンション除去のテスト
        event = Mock(spec=MessageEvent)
        event.message = Mock(spec=TextMessageContent)
        event.message.text = "@bot こんにちは"
        # 手動で ranges を作成
        ranges = [(0, 4)]
        clean = self.logic._strip_self_mentions("@bot こんにちは", ranges)
        assert clean == "こんにちは"
