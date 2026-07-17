import os
import threading
import time
import requests
from flask import Flask
import discord
from discord.ext import commands

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

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
        query = message.content.replace(f'<@{bot.user.id}>', '').strip()
        if not query:
            return

        async with message.channel.typing():
            try:
                channel_id = str(message.channel.id)
                payload = {
                    "inputs": {},
                    "query": query,
                    "response_mode": "blocking",
                    "user": str(message.author.id),
                    "conversation_id": conversations.get(channel_id, "")
                }
                
                headers = {"Authorization": f"Bearer {DIFY_API_KEY}", "Content-Type": "application/json"}
                response = requests.post(f"{DIFY_API_URL}/chat-messages", json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    await message.reply(data.get("answer", "（沒料）"))
                    if data.get("conversation_id"):
                        conversations[channel_id] = data.get("conversation_id")
                else:
                    # 這一行會直接把錯誤訊息秀出來，讓你抓錯！
                    await message.reply(f"錯誤 {response.status_code}: {response.text}")
            except Exception as e:
                await message.reply(f"程式崩潰: {str(e)}")

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    bot.run(os.environ.get("DISCORD_BOT_TOKEN"))
