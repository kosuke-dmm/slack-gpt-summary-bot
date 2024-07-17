import os
import re
import logging
from logging.handlers import RotatingFileHandler
import asyncio
import openai
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler
from aiohttp import web

# 環境変数の読み込み
load_dotenv()

# Slack APIトークンとOpenAI APIキーを環境変数から取得
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
slack_app_token = os.environ.get("SLACK_APP_TOKEN")
openai_api_key = os.environ.get("OPENAI_API_KEY")

# リアクション絵文字の設定（デフォルト値: "gpt-matome"）
REACTION_EMOJI = os.environ.get("REACTION_EMOJI", "gpt-matome")

# ロギングの設定
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "slack_bot.log")

logger = logging.getLogger("slack_bot")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Slack Boltアプリの初期化
app = AsyncApp(token=slack_bot_token)

# Slack WebClientの初期化
client = AsyncWebClient(token=slack_bot_token)

# OpenAI APIクライアントの初期化
openai_client = openai.AsyncClient(api_key=openai_api_key)

# GPT-4用のプロンプト定義
prompt = """
### Slack会話要約プロンプト

**目的:**  
- Slackのスレッドから主要な情報を効率的に抽出し、要約する。

**指示:**  
- スレッドへの参加者を`name`から取り出し、リスト形式で`参加者:`として出力してください。参加者リストは点線(`-`)で始めてください。  
- スレッド内の全てのやりとりを時系列順に要約し、番号付きリスト形式で`要約:`として出力してください。各要約は番号(`1.`, `2.`, `3.` ...)で始めてください。  
- 残タスクがある場合は、点線(`-`)を使って`タスク:`としてリスト形式で示してください。  
- 各セクション（参加者、要約、タスク）の間には空行を入れてください。  
- フォーマットに従って、視認性の高い出力を心がけてください。

**出力フォーマット:**  
\`\`\`
#### 会話要約

**参加者:**  
- 参加者1: [役割や部署（もし関連あれば）]  
- ... (他の参加者も必要に応じて追加)  

**要約:**  
1. 要約文1 - [関連する詳細情報やコンテキスト]  
2. ... (追加の要約文も必要に応じて追加)  

**タスク:**  
- タスク1: [タスクに関連する詳細情報や担当者]  
- ... (追加のタスクも必要に応じて追加)  

**追加情報:**  
- [会話中で生じたその他の重要なポイントや決定事項]  
- ... (追加の情報も必要に応じて追加)
\`\`\`
"""

async def summarize_conversation(messages):
    """
    与えられたメッセージリストを基に会話を要約する。

    :param messages: 要約対象のメッセージリスト
    :return: 要約テキスト、またはエラーメッセージ
    """
    try:
        # メッセージを1つの文字列に結合
        conversation = "\n".join([f"{msg['From']}: {msg['text']}" for msg in messages])

        # GPT-4を使用して要約を生成
        response = await openai_client.chat.completions.create(
            temperature=0,
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}] + 
                    [{"role": "user", "content": message} for message in conversation.split('\n')],
            max_tokens=2000
        )

        summary = response.choices[0].message.content
        return summary
    except Exception as e:
        logger.error(f"要約生成中にエラーが発生しました: {e}")
        return "要約の生成中にエラーが発生しました。"

async def check_ts_type(event):
    """
    イベントからスレッドのタイムスタンプを取得する。

    :param event: Slackイベントオブジェクト
    :return: スレッドのタイムスタンプ、またはNone（エラー時）
    """
    try:
        conversations_replies = await client.conversations_replies(
                channel=event['item']['channel'],
                ts=event['item']['ts']
            )
            
        if conversations_replies["messages"][0].get("thread_ts") is not None:
            ts = conversations_replies["messages"][0]["thread_ts"]
        else:
            ts = conversations_replies["messages"][0]["ts"]
        return ts
    except Exception as e:
        logger.error(f"check_ts_type関数でエラーが発生しました: {e}")
        return None

async def get_username(user_id):
    """
    ユーザーIDからユーザー名を取得する。

    :param user_id: SlackユーザーID
    :return: ユーザー名、または"不明なユーザー"（エラー時）
    """
    try:
        user_info = await client.users_info(user=user_id)
        return user_info['user']['profile']['real_name']
    except Exception as e:
        logger.error(f"ユーザー名の取得中にエラーが発生しました: {e}")
        return "不明なユーザー"

async def replace_user_ids_with_usernames(text):
    """
    テキスト内のユーザーIDをユーザー名に置換する。

    :param text: 置換対象のテキスト
    :return: ユーザー名に置換されたテキスト
    """
    user_ids = re.findall('<@(\w+)>', text)
    
    for user_id in user_ids:
        username = await get_username(user_id)
        text = text.replace(f'<@{user_id}>', 'To'+username)
    
    return text

@app.event("reaction_added")
async def handle_reaction(event, say):
    """
    リアクション追加イベントを処理し、必要に応じて会話を要約する。

    :param event: リアクション追加イベント
    :param say: Slackメッセージ送信用の関数
    """
    try:
        reaction = event["reaction"]
        user_id = event["user"]
        if reaction == REACTION_EMOJI:
            channel_id = event["item"]["channel"]
            thread_ts = event["item"]["ts"]

            team_name = os.environ.get("SLACK_WORKSPACE")  # TODO: 環境変数から取得するように変更する
            message_url = f"https://{team_name}.slack.com/archives/{channel_id}/p{thread_ts.replace('.', '')}"

            # ユーザーに処理開始を通知
            response = await say(text=f"お疲れ様です！スレッドのURL: {message_url}\nの要約リクエストを受け付けました。しばらくお待ちください。", channel=user_id)
            dm_ts = response['ts']

            # スレッドのタイムスタンプを取得
            cs_thread_ts = await check_ts_type(event)

            # スレッドのメッセージを取得
            response = await client.conversations_replies(
                channel=channel_id,
                ts=cs_thread_ts
            )
            messages = response["messages"]

            # メッセージを処理用の形式に変換
            user_text_dicts = [{'From': await get_username(msg["user"]), 'text': await replace_user_ids_with_usernames(msg["text"])} for msg in messages if "user" in msg]

            # 会話を要約
            summary = await summarize_conversation(user_text_dicts)

            # 要約をユーザーに送信
            await say(text=f"要約: {summary}", channel=user_id, thread_ts=dm_ts)

    except Exception as e:
        error_message = f"エラーが発生しました: {e}"
        logger.error(error_message)
        await say(text=error_message, channel=user_id)

@app.event("message")
async def handle_message_events(event, logger):
    """
    メッセージイベントを処理し、ログに記録する。

    :param event: メッセージイベント
    :param logger: ロガーオブジェクト
    """
    subtype = event.get('subtype', '')

    if subtype == '':
        logger.info("通常のメッセージを受信しました。")
    elif subtype == 'message_changed':
        logger.info("編集されたメッセージを受信しました。")
    else:
        logger.info(f"その他のサブタイプ '{subtype}' のメッセージを受信しました。")

async def health_check(request):
    """
    ヘルスチェックエンドポイント

    :param request: リクエストオブジェクト
    :return: "OK"レスポンス
    """
    return web.Response(text="OK")

async def start_server():
    """
    ヘルスチェック用のWebサーバーを起動する。
    """
    app_server = web.Application()
    app_server.add_routes([web.get('/health', health_check)])
    runner = web.AppRunner(app_server)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()

async def start_bot():
    """
    Slackボットを起動する。
    """
    handler = AsyncSocketModeHandler(app, slack_app_token)
    await handler.start_async()

if __name__ == "__main__":
    # メインの実行部分
    loop = asyncio.get_event_loop()
    loop.create_task(start_server())
    loop.run_until_complete(start_bot())