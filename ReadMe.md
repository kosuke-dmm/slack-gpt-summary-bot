# Slack GPT-4 要約ボット

## 概要
このプロジェクトは、Slackのスレッドを自動的に要約するボットを実装しています。GPT-4を使用して、長いスレッドの内容を簡潔にまとめ、効率的なコミュニケーションをサポートします。

## 主な機能
- 特定の絵文字リアクションをトリガーとしたスレッド要約
- GPT-4を使用した高度な自然言語処理による要約生成
- Slack API統合によるシームレスな操作
- Docker化されたアプリケーションによる簡単なデプロイと管理

## 前提条件
- Docker
- Docker Compose
- Slackワークスペースの管理者権限
- OpenAI APIキー

## セットアップ

1. リポジトリをクローンします：
   ```
   git clone https://github.com/kosuke-dmm/slack-gpt-summary-bot.git
   cd slack-gpt-summary-bot
   ```

2. 環境変数ファイルを設定します：
   `app/.env` ファイルを作成し、以下の変数を設定します：
   ```
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   OPENAI_API_KEY=your-openai-api-key
   REACTION_EMOJI=gpt-matome
   SLACK_WORKSPACE=your-slack-workspace
   ```

3. Dockerイメージをビルドし、コンテナを起動します：
   ```
   docker-compose up --build
   ```

## 使用方法
1. ボットをSlackチャンネルに招待します。
2. 要約したいスレッドに対して、設定した絵文字（デフォルトは `gpt-matome`）でリアクションします。
3. ボットが自動的にスレッドを要約し、要約結果をDMで送信します。

## 開発

### 依存関係
主な依存関係は以下の通りです：
- slack-bolt
- openai
- python-dotenv
- aiohttp

詳細は `requirements.txt` を参照してください。

### ファイル構造
- `app/main.py`: メインのアプリケーションコード
- `Dockerfile`: Dockerイメージ構築用の設定
- `docker-compose.yml`: Docker Composeの設定
- `requirements.txt`: Pythonの依存関係リスト

### ローカルでの実行
1. 仮想環境を作成し、アクティベートします：
   ```
   python -m venv venv
   source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
   ```
2. 依存関係をインストールします：
   ```
   pip install -r requirements.txt
   ```
3. `app/.env` ファイルを設定します。
4. アプリケーションを実行します：
   ```
   python app/main.py
   ```

## ログ
ログは `./logs` ディレクトリに保存されます。ログローテーションが設定されており、最大ファイルサイズは100MB、最大5ファイルまで保持されます。

## ヘルスチェック
Dockerコンテナのヘルスチェックエンドポイントは `http://localhost:8000/health` です。

## 注意事項
- 本番環境での使用前に、セキュリティ設定を十分に確認してください。
- APIキーやトークンを公開リポジトリにコミットしないよう注意してください。
- 大規模な導入の場合は、パフォーマンスとコスト管理に注意してください。

## ライセンス
[MITライセンス](LICENSE)

## コントリビューション
プルリクエストは歓迎します。大きな変更を加える場合は、まずissueを開いて議論してください。

## サポート
問題や質問がある場合は、GitHubのissueを開いてください。
