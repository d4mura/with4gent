FROM python:3.13-slim

WORKDIR /app

# 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY src/ ./src/

# 環境変数
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# ポート設定
EXPOSE 8080

# アプリケーション起動
CMD ["python", "src/main.py"]
