import os
import threading
import time
import requests
from flask import Flask
import discord
from discord.ext import commands

# 1. 建立 Flask 網頁伺服器（滿足 Render 的健康檢查）
app = Flask('')

@app.route('/')
def home():
    return "dd is alive and watching you!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# 2. 核心防休眠機制：每 10 分鐘對自己的外部 URL 發送請求
def self_ping():
    time.sleep(30) # 等待網頁伺服器初始化
    
    # Render 會自動注入 RENDER_EXTERNAL_URL 變數
    url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not url:
        print("[防休眠] 警告：未偵測到 RENDER_EXTERNAL_URL。")
        return
        
    print(f"[防休眠] 自我喚醒機制已啟動！目標網址：{url}")
    while True:
        try:
            res = requests.get(url)
            print(f"[防休眠] 喚醒波段發送成功！狀態碼：{res.status_code}")
        except Exception as e:
            print(f"[防休眠] 喚醒失敗：{str(e)}")
        
        time.sleep(600) # 每 10 分鐘 (600秒) 自我敲打一次

# 3. Discord 機器人設定與 Dify 連接
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
DIFY_API_URL = os.environ.get("DIFY_API_URL", "https://api.dify.ai/v1")

conversations = {} # 用來記錄每個頻道的對話長久記憶 ID

@bot.event
async def on_ready():
    print(f'成功登入 Discord 機器人：{bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # 當有人在 Discord 頻道中 @dd 時觸發
    if bot.user.mentioned_in(message):
        query = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        if not query:
            await message.reply("唷，叫我有事？沒事快去寫功課。")
            return

        async with message.channel.typing():
            try:
                channel_id = str(message.channel.id)
                conv_id = conversations.get(channel_id, "")

                headers = {
                    "Authorization": f"Bearer {DIFY_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "inputs": {},
                    "query": query,
                    "response_mode": "blocking",
                    "user": str(message.author.id),
                    "conversation_id": conv_id
                }
                
                response = requests.post(f"{DIFY_API_URL}/chat-messages", json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    reply = data.get("answer", "（dd突然放空了...）")
                    
                    if data.get("conversation_id"):
                        conversations[channel_id] = data.get("conversation_id")
                        
                    await message.reply(reply)
                else:
                    await message.reply(f"（dd的大腦怪怪的，錯誤碼：{response.status_code}）")
            except Exception as e:
                await message.reply(f"（dd發生異常：{str(e)}）")

if __name__ == "__main__":
    t_flask = threading.Thread(target=run_flask, daemon=True)
    t_flask.start()
    
    t_ping = threading.Thread(target=self_ping, daemon=True)
    t_ping.start()
    
    TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
    bot.run(TOKEN)
