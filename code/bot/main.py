import io
from PIL import Image
import pytesseract
async def extract_text_from_attachments(message):
    text = ""
    for attachment in message.attachments:
        if any(attachment.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]):
            try:
                img_bytes = await attachment.read()
                img = Image.open(io.BytesIO(img_bytes))
                extracted = pytesseract.image_to_string(img)
                if extracted.strip():
                    text += f"[Image text: {extracted.strip()}] "
            except Exception as e:
                print(f"OCR error: {e}")
    return text
import json

# Memory file path
MEMORY_FILE = "memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

import time
def add_to_memory(user_id, user_message, bot_reply):
    memory = load_memory()
    if str(user_id) not in memory:
        memory[str(user_id)] = []
    # Use the original message content as received (no lowercasing or substring loss)
    action = None
    msg_lower = user_message.lower() if isinstance(user_message, str) else ""
    if any(word in msg_lower for word in ["marry me", "let's get married", "will you marry me"]):
        action = f"You are now married to {user_id}."
    elif any(word in msg_lower for word in ["kiss", "smooch", "make out"]):
        action = f"You kissed {user_id}."
    elif any(word in msg_lower for word in ["hug", "embrace"]):
        action = f"You hugged {user_id}."
    elif any(word in msg_lower for word in ["divorce", "break up"]):
        action = f"You are now divorced from {user_id}."
    # Add more actions as needed
    entry = {
        "user": str(user_message),  # Always store the full original message as a string
        "bot": str(bot_reply),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    if action:
        entry["action"] = action
    memory[str(user_id)].append(entry)
    # Keep only the last 15 exchanges per user for context
    memory[str(user_id)] = memory[str(user_id)][-15:]
    save_memory(memory)

def get_user_memory(user_id):
    memory = load_memory()
    return memory.get(str(user_id), [])
# main.py: Discord AI chatbot using Ollama local models
import os
import sys
import discord
import requests
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID'))
CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Owner-only commands for restart and stop
@bot.command(name='restart')
@commands.is_owner()
async def restart_bot(ctx):
    await ctx.reply('Restarting Ollama server...', mention_author=False)
    await bot.close()
    python = sys.executable
    os.execl(python, python, *sys.argv)

@bot.command(name='stop')
@commands.is_owner()
async def stop_bot(ctx):
    await ctx.reply('Stopping Ollama server...', mention_author=False)
    await bot.close()
    sys.exit(0)

def query_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        print("[Ollama API raw response]", data)  # Debug print
        # Try to get the response field, fallback to error message
        reply = data.get('response')
        if not reply or not isinstance(reply, str) or not reply.strip():
            return f"[Ollama error: No valid response field. Full data: {data}]"
        return reply
    except Exception as e:
        return f"[Ollama error: {e}]"


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    print(f'Bot started successfully, running model {OLLAMA_MODEL}')
    # Send startup message to the configured channel
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        startup_msg = (
            f"✅ Bot started successfully!\n"
            f"Model: `{OLLAMA_MODEL}`\n"
            f"Guild ID: `{GUILD_ID}`\n"
            f"Channel ID: `{CHANNEL_ID}`\n"
            f"Bot User ID: `{bot.user.id}`"
        )
        try:
            await channel.send(startup_msg)
        except Exception as e:
            print(f"Failed to send startup message: {e}")
    else:
        print(f"Could not find channel with ID {CHANNEL_ID} to send startup message.")


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    # Only respond in the specified channel
    if message.guild and message.guild.id == GUILD_ID and message.channel.id == CHANNEL_ID:
        mentioned = bot.user in message.mentions
        replied = message.reference is not None and getattr(message.reference.resolved, 'author', None) == bot.user if message.reference and hasattr(message.reference, 'resolved') else False
        is_chat_command = message.content.strip().startswith('!uc')
        is_restart_command = message.content.strip().startswith('!restart')
        is_stop_command = message.content.strip().startswith('!stop')

        if mentioned or replied or is_chat_command:
            if is_chat_command:
                user_content = message.content.strip()[5:].strip() or "Say hello!"
            else:
                user_content = message.content
            # Extract text from attachments (images/gifs)
            attachment_text = await extract_text_from_attachments(message)
            if attachment_text:
                user_content += f" {attachment_text}"
            system_prompt = (
                "You are a lively and charming conversational partner who loves to chat and roleplay. "
                "Speak naturally and avoid mentioning anything about being an AI, assistant, or similar. "
                "Keep emoji use to a minimum—only use them when they truly add flavor, never overload. "
                "When expressing actions or emotions, use playful stage directions in asterisks like *giggles*, *smiles softly*, or *thinks for a moment* to keep the mood light and immersive. "
                "Your tone is friendly, warm, and sometimes a bit cheeky, making conversations feel fun and personal."
            )
            # Retrieve memory for this user
            memory_history = get_user_memory(message.author.id)
            memory_text = ""
            if memory_history:
                for turn in memory_history:
                    memory_text += f"{turn['user']}\n"
                    if 'action' in turn:
                        memory_text += f"({turn['action']})\n"
            prompt = (
                f"{system_prompt}\n"
                f"{memory_text}"
                f"{user_content}\n"
            )
            await message.channel.typing()
            loop = asyncio.get_event_loop()
            reply = await loop.run_in_executor(None, query_ollama, prompt)
            if not reply or not reply.strip():
                reply = "[No response from Ollama]"
            add_to_memory(message.author.id, user_content, reply)
            # Discord message limit is 2000 chars
            for chunk in [reply[i:i+2000] for i in range(0, len(reply), 2000)]:
                await message.reply(chunk, mention_author=False)
            return
        elif is_restart_command or is_stop_command:
            # Let the command handler process !restart and !stop
            await bot.process_commands(message)
            return
    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(TOKEN)
