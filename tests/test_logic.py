import unittest
from unittest.mock import Mock

from linebot.v3.webhooks import (
    GroupSource,
    JoinEvent,
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

    def test_handle_join(self):
        # 参加イベントのテスト
        event = Mock(spec=JoinEvent)
        event.reply_token = "join_reply_token"
        self.mock_line.get_bot_info.return_value = "TestBot"

        self.logic.handle_join(event)

        self.mock_line.get_bot_info.assert_called_once()
        expected_message = (
            "招待ありがとうございます！TestBotです。\n"
            "私をメンションして話しかけてください。\n"
            "「/exit」もしくは「/bye」でセッションをリセットして退出します。\n\n"
            "よろしくお願いします！"
        )
        self.mock_line.reply_message.assert_called_with(
            "join_reply_token", expected_message
        )

    def test_anonymization_applied(self):
        # 匿名化が適用されることの確認
        event = Mock(spec=MessageEvent)
        event.source = UserSource(user_id="user_123")
        event.message = Mock(spec=TextMessageContent)
        # 32桁の16進数ID
        user_id = "U" + "a" * 32
        event.message.text = f"私のIDは {user_id} です"
        event.reply_token = "reply_token"

        self.mock_ai.get_response.return_value = "了解"
        self.logic.process_event(event)

        call_args = self.mock_ai.get_response.call_args
        input_text = call_args[0][1]
        self.assertIn("[ID]", input_text)

    def test_context_summarization_trigger(self):
        # 10件ごとにサマライズが呼ばれることの確認
        context_key = "user:user_123"
        self.mock_ai.summarize.return_value = "これまでのまとめ"
        self.mock_ai.get_response.return_value = "OK"

        for i in range(1, 11):
            event = Mock(spec=MessageEvent)
            event.source = UserSource(user_id="user_123")
            event.message = Mock(spec=TextMessageContent)
            event.message.id = f"msg_{i}"
            event.message.text = f"メッセージ{i}"
            event.reply_token = f"reply_{i}"
            self.logic.process_event(event)

        # 10件目で summarize が呼ばれる
        self.mock_ai.summarize.assert_called_once_with(context_key)
        assert len(self.logic._context_summaries[context_key]) == 1
        assert self.logic._context_summaries[context_key][0] == "これまでのまとめ"

        # 11件目の入力にサマリーが含まれることの確認
        event = Mock(spec=MessageEvent)
        event.source = UserSource(user_id="user_123")
        event.message = Mock(spec=TextMessageContent)
        event.message.id = "msg_11"
        event.message.text = "次の質問"
        event.reply_token = "reply_11"
        self.logic.process_event(event)

        call_args = self.mock_ai.get_response.call_args
        input_text = call_args[0][1]
        self.assertIn("---これまでの会話の要約---", input_text)
        self.assertIn("要約1: これまでのまとめ", input_text)
        self.assertIn("次の質問", input_text)

    def test_reply_quote_context_cached(self):
        # リプライ（引用）コンテキストの確認（キャッシュあり）
        # 1. まず引用元のメッセージを処理してキャッシュさせる
        msg1 = Mock(spec=TextMessageContent)
        msg1.id = "msg_001"
        msg1.text = "昨日のニュース見ましたか？"
        event1 = Mock(spec=MessageEvent)
        event1.source = UserSource(user_id="user_123")
        event1.message = msg1
        event1.reply_token = "reply_token_001"
        self.mock_ai.get_response.return_value = "はい"
        self.logic.process_event(event1)

        # 2. そのメッセージに対してリプライする
        msg2 = Mock(spec=TextMessageContent)
        msg2.id = "msg_002"
        msg2.text = "見ました！すごかったですね。"
        msg2.quoted_message_id = "msg_001"
        event2 = Mock(spec=MessageEvent)
        event2.source = UserSource(user_id="user_123")
        event2.message = msg2
        event2.reply_token = "reply_token_002"

        self.mock_ai.get_response.return_value = "確かにすごかったですね"

        self.logic.process_event(event2)

        # キャッシュから取得されているので line.get_message_content は呼ばれない
        # ※ 実際にはフォールバックとして呼ばれる可能性があるが、
        # キャッシュがあればそちらが優先される
        # 履歴が含まれていることを確認
        call_args = self.mock_ai.get_response.call_args
        input_text = call_args[0][1]
        self.assertIn("---直近の会話内容---", input_text)
        self.assertIn("昨日のニュース見ましたか？", input_text)
        self.assertIn('引用メッセージ: "昨日のニュース見ましたか？"', input_text)
        self.assertIn("見ました！すごかったですね。", input_text)

    def test_reply_quote_context_api_fallback(self):
        # リプライ（引用）コンテキストの確認（キャッシュなし、APIフォールバック）
        # 履歴を1つ作っておく
        msg_pre = Mock(spec=TextMessageContent)
        msg_pre.id = "msg_pre"
        msg_pre.text = "事前の会話"
        event_pre = Mock(spec=MessageEvent)
        event_pre.source = UserSource(user_id="user_123")
        event_pre.message = msg_pre
        event_pre.reply_token = "reply_token_pre"
        self.mock_ai.get_response.return_value = "はい"
        self.logic.process_event(event_pre)

        event = Mock(spec=MessageEvent)
        event.source = UserSource(user_id="user_123")
        event.message = Mock(spec=TextMessageContent)
        event.message.id = "msg_004"
        event.message.text = "どう思う？"
        event.reply_token = "reply_token"
        event.message.quoted_message_id = "msg_external"

        self.mock_line.get_message_content.return_value = "外部からのメッセージ内容"
        self.mock_ai.get_response.return_value = "良いと思います"

        self.logic.process_event(event)

        # 履歴が含まれていることを確認
        call_args = self.mock_ai.get_response.call_args
        input_text = call_args[0][1]
        self.assertIn("---直近の会話内容---", input_text)
        self.assertIn("外部からのメッセージ内容", input_text)
        self.assertIn('引用メッセージ: "外部からのメッセージ内容"', input_text)
        self.assertIn("どう思う？", input_text)

    def test_context_history_inclusion(self):
        # 履歴がAIへの入力に含まれるかのテスト
        group_id = "group_context"
        context_key = f"group:{group_id}"

        # 1つ目：メンションなし（履歴にのみ残る）
        event1 = Mock(spec=MessageEvent)
        event1.source = GroupSource(group_id=group_id, user_id="user_A")
        event1.message = Mock(spec=TextMessageContent)
        event1.message.text = "今日のランチ何食べる？"
        event1.message.mention = None
        self.logic.process_event(event1)

        # 2つ目：メンションあり（これに応答する際、event1の内容が含まれるべき）
        event2 = Mock(spec=MessageEvent)
        event2.source = GroupSource(group_id=group_id, user_id="user_B")
        mention = Mock()
        mention.mentionees = [Mock(is_self=True, index=0, length=4)]
        event2.message = Mock(spec=TextMessageContent)
        event2.message.text = "@bot おすすめ教えて"
        event2.message.mention = mention
        event2.reply_token = "reply_token_hist"

        self.mock_ai.get_response.return_value = "カレーがおすすめです"

        self.logic.process_event(event2)

        # AIへの入力に履歴が含まれているか
        call_args = self.mock_ai.get_response.call_args
        self.assertEqual(call_args[0][0], context_key)
        input_text = call_args[0][1]
        self.assertIn("今日のランチ何食べる？", input_text)
        self.assertIn("おすすめ教えて", input_text)
        self.assertIn("---直近の会話内容---", input_text)
        self.assertIn("ユーザー(er_A)", input_text)  # user_A の末尾4文字
