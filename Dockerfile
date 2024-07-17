# ビルドステージ
FROM python:3.9-slim as builder
WORKDIR /app

# ビルド用の依存関係をインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user -r requirements.txt

# 実行ステージ
FROM python:3.9-slim
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ユーザーを作成
RUN useradd -m myuser

# ビルドステージからPythonパッケージをコピー
COPY --from=builder /root/.local /home/myuser/.local

# アプリケーションコードをコピー
COPY . .

# 所有権を変更
RUN chown -R myuser:myuser /app /home/myuser/.local

# ユーザーを切り替え
USER myuser

# 環境変数を設定
ENV PATH=/home/myuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 実行コマンド
CMD ["python", "./app/main.py"]