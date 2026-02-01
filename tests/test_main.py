"""
Tests for with4gent LINE Bot
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# 環境変数のモックを先に行う
@pytest.fixture(autouse=True)
def mock_env():
    with patch.dict(
        os.environ,
        {
            "LINE_CHANNEL_ACCESS_TOKEN": "test_token",
            "LINE_CHANNEL_SECRET": "test_secret",
            "OPENAI_API_KEY": "test_key",
        },
    ):
        yield


class TestHealthEndpoint:
    """ヘルスチェックエンドポイントのテスト"""

    def test_health_returns_ok(self):
        """ヘルスチェックが正常に動作する"""
        from src.main import app

        client = app.test_client()
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json == {"status": "ok"}


class TestWebhookEndpoint:
    """Webhookエンドポイントのテスト"""

    def test_webhook_missing_signature_returns_400(self):
        """署名がない場合は400を返す"""
        from src.main import app

        client = app.test_client()
        response = client.post("/webhook", data="{}")
        assert response.status_code == 400


class TestOpenAIService:
    """OpenAIServiceのテスト"""

    @patch("src.services.openai_service.OpenAI")
    def test_get_response_new_session(self, mock_openai_class):
        from src.services.openai_service import OpenAIService

        mock_client = mock_openai_class.return_value
        mock_response = Mock()
        mock_response.id = "resp_123"
        mock_response.output_text = "Hello!"
        mock_client.responses.create.return_value = mock_response

        service = OpenAIService("fake_key")
        result = service.get_response("user_123", "Hi")

        assert result == "Hello!"
        assert service.previous_responses["user_123"] == "resp_123"
        mock_client.responses.create.assert_called_once()

    @patch("src.services.openai_service.OpenAI")
    def test_get_response_existing_session(self, mock_openai_class):
        from src.services.openai_service import OpenAIService

        mock_client = mock_openai_class.return_value
        mock_response = Mock()
        mock_response.id = "resp_456"
        mock_response.output_text = "World!"
        mock_client.responses.create.return_value = mock_response

        service = OpenAIService("fake_key")
        service.previous_responses["user_123"] = "prev_id"
        result = service.get_response("user_123", "Hello")

        assert result == "World!"
        call_args = mock_client.responses.create.call_args
        assert call_args.kwargs["previous_response_id"] == "prev_id"


class TestLineService:
    """LineServiceのテスト"""

    @patch("src.services.line_service.ApiClient")
    @patch("src.services.line_service.MessagingApi")
    def test_reply_message(self, mock_msg_api_class, mock_api_client_class):
        from src.services.line_service import LineService

        mock_api = mock_msg_api_class.return_value

        service = LineService("fake_token")
        service.reply_message("token", "hello")

        mock_api.reply_message_with_http_info.assert_called_once()

    @patch("src.services.line_service.ApiClient")
    @patch("src.services.line_service.MessagingApi")
    def test_mark_as_read(self, mock_msg_api_class, mock_api_client_class):
        from src.services.line_service import LineService

        mock_api = mock_msg_api_class.return_value

        service = LineService("fake_token")
        service.mark_as_read("read_token")

        mock_api.mark_messages_as_read_by_token.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
