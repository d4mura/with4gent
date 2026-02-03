# with4gent

LINE上で動作するOpenAI搭載のチャットボット

## 概要

with4gentは、LINE Messaging APIとOpenAI Responses APIを統合したチャットボットです。ユーザーからのメッセージに対してAIが応答し、必要に応じてWeb検索を行い、最新の情報を提供します。

## 機能

- **AIチャット**: OpenAI GPT-4o-mini による自然な会話
- **Web検索**: 最新情報が必要な質問には自動でWeb検索を実行
- **会話の継続**: ユーザーごとに会話履歴を保持し、文脈を理解した応答
- **既読機能**: メッセージ受信時に自動で既読をつける

## 技術スタック

- **言語**: Python 3.13
- **フレームワーク**: Flask
- **インフラ**: Google Cloud Run
- **API**:
  - LINE Messaging API
  - OpenAI Responses API

## セットアップ

### 必要な環境変数

```bash
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
OPENAI_API_KEY=your_openai_api_key
```

### ローカル開発

```bash
# 依存関係のインストール
uv sync

# 環境変数の設定
cp .env.example .env
# .envファイルを編集して各キーを設定

# 開発サーバーの起動
python src/main.py
```

### デプロイ

#### 手動デプロイ

```bash
gcloud run deploy with4gent \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars LINE_CHANNEL_ACCESS_TOKEN=xxx,LINE_CHANNEL_SECRET=xxx,OPENAI_API_KEY=xxx
```

#### CI/CD（GitHub Actions）

`main`ブランチへのプッシュで自動デプロイされます。

必要なGitHub Secrets:
- `GCP_PROJECT_ID`: GCPプロジェクトID
- `GCP_SA_KEY`: サービスアカウントキー（JSON）
- `LINE_CHANNEL_ACCESS_TOKEN`: LINEチャネルアクセストークン
- `LINE_CHANNEL_SECRET`: LINEチャネルシークレット
- `OPENAI_API_KEY`: OpenAI APIキー

## LINE Developersの設定

1. [LINE Developers Console](https://developers.line.biz/)でMessaging APIチャネルを作成
2. Webhook URLを設定: `https://your-cloud-run-url/webhook`
3. Webhookの利用をONにする
4. 応答メッセージをOFFにする（Botの応答と重複するため）

## API エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|---------|------|
| `/health` | GET | ヘルスチェック |
| `/webhook` | POST | LINE Webhook受信 |

## テスト

```bash
# テストの実行
pytest tests/ -v

# カバレッジ付き
pytest tests/ -v --cov=src
```

## ライセンス

MIT

## 作者

d4mura Lab.
