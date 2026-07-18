import os
import threading
import time
import requests
import json
from flask import Flask
import discord
from discord.ext import commands

# 1. Flask 網頁伺服器
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. 防休眠機制
def self_ping():
    time.sleep(30)
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if url:
        while True:
            try:
                requests.get(url)
            except:
                pass
            time.sleep(600)

# 3. Discord 機器人設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
DIFY_API_URL = os.environ.get("DIFY_API_URL", "https://api.dify.ai/v1")
conversations = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        # 為了讓 AI 知道是誰在跟它說話，我們把發言者的暱稱加進問題裡
        author_name = message.author.display_name
        raw_query = message.content.replace(f'<@{bot.user.id}>', '').strip()
        if not raw_query:
            return
            
        # 組合後的 query 會變成像是： "范某的主人 廢物18號 說： 67"
        query = f"{author_name} 說： {raw_query}"

        async with message.channel.typing():
            try:
                channel_id = str(message.channel.id)
                bot_id = str(bot.user.id)
                
                payload = {
                    "inputs": {},
                    "query": query,
                    "response_mode": "streaming",
                    # 關鍵修改：將 user 固定為機器人自己的 Discord ID 
                    # 這樣不管誰呼叫，Dify 都視為同一個人在這頻道對話，完美共用紀錄！
                    "user": f"discord_bot_{bot_id}",
                    "conversation_id": conversations.get(channel_id, "")
                }
                
                headers = {"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"}
                response = requests.post(f"{DIFY_API_URL}/chat-messages", json=payload, headers=headers, stream=True)
                
                bot_name = bot.user.name if bot.user else "Bot"

                if response.status_code == 200:
                    full_answer = ""
                    for line in response.iter_lines():
                        if line:
                            decoded_line = line.decode('utf-8')
                            if decoded_line.startswith("data:"):
                                data = json.loads(decoded_line[5:])
                                if "answer" in data:
                                    full_answer += data["answer"]
                                if "conversation_id" in data:
                                    # 依然只用頻道 ID 鎖定對話紀錄
                                    conversations[channel_id] = data["conversation_id"]
                    
                    await message.reply(full_answer if full_answer else f"（{bot_name} 沒說話）")
                else:
                    await message.reply(f"【{bot_name}】Dify 錯誤 {response.status_code}: {response.text}")
            except Exception as e:
                await message.reply(f"解析發生錯誤: {str(e)}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    bot.run(os.environ.get("DISCORD_BOT_TOKEN"))
