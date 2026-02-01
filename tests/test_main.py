"""
Tests for with4gent LINE Bot
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestHealthEndpoint:
    """ヘルスチェックエンドポイントのテスト"""
    
    def test_health_returns_ok(self):
        """ヘルスチェックが正常に動作する"""
        with patch.dict(os.environ, {
            'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
            'LINE_CHANNEL_SECRET': 'test_secret',
            'OPENAI_API_KEY': 'test_key'
        }):
            from main import app
            
            client = app.test_client()
            response = client.get('/health')
            
            assert response.status_code == 200
            assert response.json == {'status': 'ok'}


class TestWebhookEndpoint:
    """Webhookエンドポイントのテスト"""
    
    def test_webhook_missing_signature_returns_400(self):
        """署名がない場合は400を返す"""
        with patch.dict(os.environ, {
            'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
            'LINE_CHANNEL_SECRET': 'test_secret',
            'OPENAI_API_KEY': 'test_key'
        }):
            from main import app
            
            client = app.test_client()
            response = client.post('/webhook', data='{}')
            
            assert response.status_code == 400


class TestGetOpenAIResponse:
    """OpenAIレスポンス取得のテスト"""
    
    @patch('main.openai_client')
    def test_new_user_creates_new_conversation(self, mock_openai):
        """新規ユーザーの場合は新しい会話を作成する"""
        with patch.dict(os.environ, {
            'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
            'LINE_CHANNEL_SECRET': 'test_secret',
            'OPENAI_API_KEY': 'test_key'
        }):
            # モックの設定
            mock_response = Mock()
            mock_response.id = 'resp_123'
            mock_response.output_text = 'Hello!'
            mock_openai.responses.create.return_value = mock_response
            
            from main import get_openai_response, previous_responses
            
            # テスト前にクリア
            previous_responses.clear()
            
            result = get_openai_response('user_123', 'こんにちは')
            
            assert result == 'Hello!'
            assert 'user_123' in previous_responses
            assert previous_responses['user_123'] == 'resp_123'
    
    @patch('main.openai_client')
    def test_existing_user_continues_conversation(self, mock_openai):
        """既存ユーザーの場合は会話を継続する"""
        with patch.dict(os.environ, {
            'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
            'LINE_CHANNEL_SECRET': 'test_secret',
            'OPENAI_API_KEY': 'test_key'
        }):
            mock_response = Mock()
            mock_response.id = 'resp_456'
            mock_response.output_text = 'Nice to meet you!'
            mock_openai.responses.create.return_value = mock_response
            
            from main import get_openai_response, previous_responses
            
            # 既存の会話を設定
            previous_responses['user_456'] = 'resp_previous'
            
            result = get_openai_response('user_456', '私の名前は？')
            
            assert result == 'Nice to meet you!'
            # previous_response_idが使われたことを確認
            call_kwargs = mock_openai.responses.create.call_args.kwargs
            assert call_kwargs.get('previous_response_id') == 'resp_previous'
    
    @patch('main.openai_client')
    def test_api_error_returns_error_message(self, mock_openai):
        """APIエラー時はエラーメッセージを返す"""
        with patch.dict(os.environ, {
            'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
            'LINE_CHANNEL_SECRET': 'test_secret',
            'OPENAI_API_KEY': 'test_key'
        }):
            mock_openai.responses.create.side_effect = Exception('API Error')
            
            from main import get_openai_response, previous_responses
            
            previous_responses.clear()
            result = get_openai_response('user_789', 'test')
            
            assert 'エラーが発生しました' in result


class TestMarkAsRead:
    """既読機能のテスト"""
    
    def test_mark_as_read_with_valid_token(self):
        """有効なトークンで既読処理が実行される"""
        with patch.dict(os.environ, {
            'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
            'LINE_CHANNEL_SECRET': 'test_secret',
            'OPENAI_API_KEY': 'test_key'
        }):
            from main import mark_as_read
            
            mock_api_client = MagicMock()
            mock_messaging_api = MagicMock()
            
            with patch('main.MessagingApi', return_value=mock_messaging_api):
                mark_as_read(mock_api_client, 'valid_token')
                
                mock_messaging_api.mark_messages_as_read_by_token.assert_called_once()
    
    def test_mark_as_read_with_none_token(self):
        """トークンがNoneの場合は何もしない"""
        with patch.dict(os.environ, {
            'LINE_CHANNEL_ACCESS_TOKEN': 'test_token',
            'LINE_CHANNEL_SECRET': 'test_secret',
            'OPENAI_API_KEY': 'test_key'
        }):
            from main import mark_as_read
            
            mock_api_client = MagicMock()
            
            with patch('main.MessagingApi') as mock_class:
                mark_as_read(mock_api_client, None)
                
                # MessagingApiが呼ばれていないことを確認
                mock_class.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
