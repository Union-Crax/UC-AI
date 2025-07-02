# import everything

import requests
import json
import discord
import tomllib
import ollama
import os # Don't panic!!! This is used to save the history file to the computer!
import subprocess
import sys
import time



# LOAD VARIABLES FROM config.toml
with open("config.toml", 'rb') as f:
    config_data = tomllib.load(f)

# Start Ollama server if not running and pull the model
def ensure_ollama_running_and_model():
    # Start Ollama server (if not already running)
    try:
        # Check if Ollama server is running by making a request
        import requests
        try:
            requests.get('http://localhost:11434')
        except Exception:
            # Start Ollama server in background
            if sys.platform.startswith('win'):
                subprocess.Popen(["ollama", "serve"], creationflags=subprocess.DETACHED_PROCESS)
            else:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"Warning: Could not check/start Ollama server: {e}")

    # Pull the model
    model = config_data.get('ollama', {}).get('model', None)
    if model:
        try:
            subprocess.run(["ollama", "pull", model], check=True)
        except Exception as e:
            print(f"Warning: Could not pull model '{model}': {e}")

ensure_ollama_running_and_model()


# api info for ollama
TOKEN = config_data['discord']['token']  # Load token from config file
SERVER_ID = int(config_data['discord'].get('server_id', 0))
CHANNEL_ID = int(config_data['discord'].get('channel_id', 0))
API_URL = 'http://localhost:11434/api/chat'

# Define the path for the conversation history file
HISTORY_FILE_PATH = "history.json"

# Load conversation history from a file if it exists
def load_conversation_history():
    if os.path.exists(HISTORY_FILE_PATH):
        with open(HISTORY_FILE_PATH, 'r') as file:
            try:
                content = file.read().strip()
                if not content:
                    return []
                return json.loads(content)
            except json.JSONDecodeError:
                return []
    return []

# Save conversation history to a file
def save_conversation_history():
    with open(HISTORY_FILE_PATH, 'w') as file:
        json.dump(conversation_history, file)

# Store conversation history in a list
conversation_history = load_conversation_history()


# set what the bot is allowed to listen to
intents = discord.Intents.default()
intents.message_content = True  # Allow reading message content
client = discord.Client(intents=intents)

# Track bot start time
start_time = time.time()


# Function to send a request to the Ollama API and get a response
def generate_response(prompt):
    # Prepend the system prompt if available
    system_prompt = config_data.get('system', {}).get('prompt', "")
    # Add system prompt as the first message if not already present
    if not conversation_history or conversation_history[0].get("role") != "system":
        conversation_history.insert(0, {"role": "system", "content": system_prompt})
    # add user message to history
    conversation_history.append({
        "role": "user",
        "content": prompt
    })
    # Save the updated conversation history to the file
    save_conversation_history()

    data = {
        "model": config_data['ollama']['model'],
        "messages": conversation_history,
        "stream": False
    }

    response = requests.post(API_URL, json=data)
    print("Raw Response Content:", response.text)

    try:
        response_data = response.json()
        assistant_message = response_data.get('message', {}).get('content', "Sorry, I couldn't generate a response.")
        # Remove any mention of being an AI or assistant
        forbidden_phrases = [
            "as an ai", "as an assistant", "i am an ai", "i am an assistant", "i'm an ai", "i'm an assistant",
            "as a language model", "as a chatbot", "as an artificial intelligence", "as artificial intelligence"
        ]
        for phrase in forbidden_phrases:
            assistant_message = assistant_message.replace(phrase, "")
            assistant_message = assistant_message.replace(phrase.capitalize(), "")
        # Add the assistant's reply to the conversation history
        conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        # Discord message limit is 2000 characters
        if len(assistant_message) > 2000:
            assistant_message = assistant_message[:2000]
        return assistant_message
    except requests.exceptions.JSONDecodeError:
        return "Error: Invalid API response"


# When the bot is ready

@client.event
async def on_ready():
    uptime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    model = config_data['ollama']['model']
    mention_mode = 'FreeWill' if str(config_data['discord'].get('FreeWill', 'false')).lower() == 'true' else 'Mention Only'
    print(f'Logged in as {client.user}')
    print(f'Model: {model}')
    print(f'Started at: {uptime}')
    print(f'Mode: {mention_mode}')
    print(f'Server ID: {SERVER_ID}, Channel ID: {CHANNEL_ID}')
    print('Bot is ready!')

    # Send bot info to the specified channel on startup
    try:
        guild = client.get_guild(SERVER_ID)
        if guild:
            channel = guild.get_channel(CHANNEL_ID)
            if channel:
                info_message = (
                    f"**chatbot started!**\n"
                    f"Model: `{model}`\n"
                    f"Started at: `{uptime}`\n"
                    f"Mode: `{mention_mode}`\n"
                    f"Server: `{guild.name}` (ID: {SERVER_ID})\n"
                    f"Channel: <#{CHANNEL_ID}>"
                )
                # Send the info message
                import asyncio
                asyncio.create_task(channel.send(info_message))
    except Exception as e:
        print(f"Could not send bot info to channel: {e}")



# When the bot detects a new message
@client.event
async def on_message(message):
    # Only allow messages from the specified server and channel
    if message.guild is None or message.guild.id != SERVER_ID or message.channel.id != CHANNEL_ID:
        return
    # Don't let the bot reply to itself
    if message.author == client.user:
        return
    # Returns if the user is a bot
    if message.author.bot:
        return
    # Command handling
    if message.content.strip().lower() == '!restart':
        if message.author.guild_permissions.administrator:
            await message.reply('Restarting bot...')
            print('Restart command received. Restarting...')
            os.execv(sys.executable, [sys.executable] + sys.argv)
        else:
            await message.reply('You do not have permission to restart the bot.')
        return
    if message.content.strip().lower() == '!stop':
        if message.author.guild_permissions.administrator:
            await message.reply('Stopping bot...')
            print('Stop command received. Shutting down...')
            await client.close()
            sys.exit(0)
        else:
            await message.reply('You do not have permission to stop the bot.')
        return

    # Respond to every message if NoMention is true, otherwise only if mentioned
    free_will = str(config_data['discord'].get('FreeWill', 'false')).lower() == 'true'
    should_respond = free_will or client.user.mentioned_in(message)
    if should_respond:
        prompt = message.content
        if not free_will:
            prompt = prompt.replace(f"<@!{client.user.id}>", "").strip()
        prompt = f"{message.author.display_name} says: " + prompt
        try:
            async with message.channel.typing():
                if prompt:
                    response = generate_response(prompt)
                    await message.reply(response)
        except discord.errors.Forbidden:
            print(f"Error: Bot does not have permission to type in {message.channel.name}")
            return


# Run the bot
client.run(TOKEN)