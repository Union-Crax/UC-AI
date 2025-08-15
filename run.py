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
import random
import re
import socket
import urllib.parse
import asyncio
import aiohttp
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

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

# Small GIF chance configuration
GIF_URL = 'https://tenor.com/h4GJRQYBqhK.gif'
# Chance to send the GIF per eligible message (e.g. 0.01 = 1%)
GIF_PROB = 0.01

# Define the path for the conversation history files
def get_history_path(channel_id):
    # Create a histories directory if it doesn't exist
    if not os.path.exists("histories"):
        os.makedirs("histories")
    return f"histories/history_{channel_id}.json"

# Load conversation history from a file if it exists
def load_conversation_history(channel_id):
    history_path = get_history_path(channel_id)
    if os.path.exists(history_path):
        with open(history_path, 'r') as file:
            try:
                content = file.read().strip()
                if not content:
                    return []
                return json.loads(content)
            except json.JSONDecodeError:
                return []
    return []

# Save conversation history to a file
def save_conversation_history(channel_id, history):
    history_path = get_history_path(channel_id)
    with open(history_path, 'w') as file:
        json.dump(history, file)

# Store conversation histories in a dictionary
conversation_histories = {}


# set what the bot is allowed to listen to
intents = discord.Intents.default()
intents.message_content = True  # Allow reading message content
client = discord.Client(intents=intents)

# Track bot start time
start_time = time.time()


# Function to send a request to the Ollama API and get a response
def generate_response(prompt, channel_id):
    # Get or create conversation history for this channel
    if channel_id not in conversation_histories:
        conversation_histories[channel_id] = load_conversation_history(channel_id)
    conversation_history = conversation_histories[channel_id]
    
    # Prepend the system prompt if available
    system_prompt = config_data.get('system', {}).get('prompt', "")
    # Add system prompt as the first message if not already present
    if not conversation_history or conversation_history[0].get("role") != "system":
        conversation_history.insert(0, {"role": "system", "content": system_prompt})
    # Add message to history with minimal formatting
    conversation_history.append({
        "role": "user",
        "content": prompt,
        "name": "user"  # This helps maintain context without explicit "user says" prefixes
    })
    
    # Keep conversation history at a reasonable size (last 20 messages)
    if len(conversation_history) > 21:  # 20 messages + 1 system message
        conversation_history = [conversation_history[0]] + conversation_history[-20:]
    
    # Save the updated conversation history to the file
    save_conversation_history(channel_id, conversation_history)

    # If OpenRouter is enabled and configured, use it instead of the local Ollama API
    openrouter_cfg = config_data.get('openrouter', {})
    # Prefer environment variable for the API key (safer than storing in config)
    openrouter_key = os.getenv('OPENROUTER_KEY') or openrouter_cfg.get('key')
    openrouter_enabled = str(openrouter_cfg.get('enabled', False)).lower() == 'true' and openrouter_key
    # Use the official domain but allow overriding via env/config if needed
    openrouter_url = os.getenv('OPENROUTER_URL') or openrouter_cfg.get('url') or 'https://api.openrouter.ai/v1/chat/completions'
    
    print(f"OpenRouter status - enabled: {openrouter_enabled}, key present: {bool(openrouter_key)}, url: {openrouter_url}")

    # If OpenRouter is enabled, use it exclusively (no fallback)
    if openrouter_enabled:
        try:
            assistant_message = openrouter_request(openrouter_key, openrouter_cfg.get('model'), conversation_history)
            if not assistant_message:
                return "Error: OpenRouter request failed to return a response"
        except Exception as e:
            return f"Error: OpenRouter request failed - {str(e)}"
    else:
        # Use Ollama only if OpenRouter is not enabled
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
        except requests.exceptions.JSONDecodeError:
            return "Error: Invalid API response"

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
    # Save the updated history
    save_conversation_history(channel_id, conversation_history)
    
    # Discord message limit is 2000 characters
    if len(assistant_message) > 2000:
        assistant_message = assistant_message[:2000]
    return assistant_message


def openrouter_request(api_key, model, messages, url=None):
    """Send a request to OpenRouter using the OpenAI SDK.
    Returns the assistant's response content.
    """
    print(f"Attempting OpenRouter request with model: {model}")
    
    try:
        # Initialize OpenAI client with OpenRouter base URL
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )

        # Make the request using the OpenAI SDK
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=500,  # Limit response length to save credits
            temperature=0.7,  # Add some randomness
            extra_headers={
                "HTTP-Referer": "https://github.com/Union-Crax/UC-AI",  # Repository URL for rankings
                "X-Title": "UC-AI Discord Bot"  # App name for rankings
            }
        )

        # Extract and return the response content
        if completion.choices and len(completion.choices) > 0:
            return completion.choices[0].message.content

    except Exception as e:
        print(f"OpenRouter request failed: {type(e).__name__}: {e}")
        raise  # Re-raise the exception since we don't want fallbacks

    return None


# When the bot is ready

@client.event
async def on_ready():
    uptime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    openrouter_enabled = str(config_data.get('openrouter', {}).get('enabled', False)).lower() == 'true'
    model = config_data.get('openrouter', {}).get('model') if openrouter_enabled else config_data['ollama']['model']
    backend = 'OpenRouter' if openrouter_enabled else 'Ollama'
    mention_mode = 'FreeWill' if str(config_data['discord'].get('FreeWill', 'false')).lower() == 'true' else 'Mention Only'
    print(f'Logged in as {client.user}')
    print(f'Backend: {backend}')
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
                    f"Backend: `{backend}`\n"
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
    # Only allow messages from the specified server
    if message.guild is None or message.guild.id != SERVER_ID:
        return
    
    # For main channel messages, check channel ID
    # For thread messages, check parent channel ID
    parent_channel_id = message.channel.parent_id if isinstance(message.channel, discord.Thread) else message.channel.id
    if parent_channel_id != CHANNEL_ID:
        return
    # Don't let the bot reply to itself
    if message.author == client.user:
        return
        
    # Chaos mode handling
    chaos_config = config_data.get('chaos', {})
    chaos_enabled = str(chaos_config.get('enabled', 'false')).lower() == 'true'
    other_bot_id = chaos_config.get('bot_id', '')
    
    # If message is from a bot and it's not chaos mode, ignore it
    if message.author.bot and not (chaos_enabled and str(message.author.id) == other_bot_id):
        return
        
    # Chaos mode: Handle bot-to-bot interaction
    if chaos_enabled and message.author.bot and str(message.author.id) == other_bot_id:
        # Get conversation tracking for this channel
        channel_key = f"chaos_{message.channel.id}"
        if channel_key not in conversation_histories:
            conversation_histories[channel_key] = {'volleys': 0}
            
        # Check if we've reached max volleys
        if conversation_histories[channel_key]['volleys'] >= chaos_config.get('max_volleys', 5):
            print(f"Chaos mode: Reached max volleys in channel {message.channel.id}")
            conversation_histories[channel_key]['volleys'] = 0  # Reset for next time
            return
            
        # Random chance to reply
        if random.random() > chaos_config.get('chance', 0.3):
            print(f"Chaos mode: Random chance prevented reply in channel {message.channel.id}")
            conversation_histories[channel_key]['volleys'] = 0  # Reset for next time
            return
            
        # Increment volley counter
        conversation_histories[channel_key]['volleys'] += 1
    # Command handling
    if message.content.strip().lower() == '!test-dns':
        try:
            import socket
            test_hosts = ['api.openrouter.ai', '8.8.8.8', 'google.com']
            results = []
            for host in test_hosts:
                try:
                    ip = socket.gethostbyname(host)
                    results.append(f"✅ {host} -> {ip}")
                except Exception as e:
                    results.append(f"❌ {host} -> {str(e)}")
            await message.reply("DNS Test Results:\n" + "\n".join(results))
        except Exception as e:
            await message.reply(f"Error running DNS test: {e}")
        return

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

    # If someone says the keyword 'feet', send the GIF immediately (case-insensitive)
    try:
        if re.search(r"\bfeet\b", message.content, re.I):
            await message.reply(GIF_URL)
            return
    except Exception:
        # If anything goes wrong (permissions, etc.), just continue to normal handling
        pass

    # Respond to every message if NoMention is true, otherwise only if mentioned
    free_will = str(config_data['discord'].get('FreeWill', 'false')).lower() == 'true'
    should_respond = free_will or client.user.mentioned_in(message)
    if should_respond:
        # Clean the message content
        prompt = message.content
        if not free_will:
            # Remove bot mention from the message
            prompt = prompt.replace(f"<@!{client.user.id}>", "").strip()
            prompt = prompt.replace(f"<@{client.user.id}>", "").strip()
        
        # Get conversation context
        context_id = str(message.channel.id)
        if context_id not in conversation_histories:
            conversation_histories[context_id] = []
            # Add context about the conversation environment
            system_context = {
                "role": "system",
                "content": f"""This is a conversation in a Discord {message.channel.type} named '{message.channel.name}'.
Remember who you're talking to and maintain context naturally without explicitly stating 'user says' or similar prefixes.
Focus on the conversation flow and maintain a natural dialog."""
            }
            conversation_histories[context_id].append(system_context)
        
        try:
            async with message.channel.typing():
                # Small random chance to send the GIF URL directly
                if random.random() < GIF_PROB:
                    # Send only the GIF URL as requested
                    await message.reply(GIF_URL)
                else:
                    if prompt:
                        # Use thread ID if in a thread, otherwise use channel ID
                        context_id = str(message.channel.id)
                        response = generate_response(prompt, context_id)
                        await message.reply(response)
        except discord.errors.Forbidden:
            print(f"Error: Bot does not have permission to type in {message.channel.name}")
            return


# Add reconnection handling
async def start_bot():
    retry_count = 0
    max_retries = 5
    retry_delay = 5  # starting delay in seconds
    
    while True:
        try:
            print("Attempting to connect to Discord...")
            await client.start(TOKEN)
        except (discord.ConnectionClosed, aiohttp.ClientConnectionError) as e:
            if retry_count >= max_retries:
                print(f"Failed to connect after {max_retries} attempts. Exiting.")
                break
            
            retry_count += 1
            wait_time = retry_delay * (2 ** (retry_count - 1))  # exponential backoff
            print(f"Connection error: {e}. Retrying in {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
            await asyncio.sleep(wait_time)
        except KeyboardInterrupt:
            print("Received keyboard interrupt. Shutting down gracefully...")
            await client.close()
            break
        except Exception as e:
            print(f"Unexpected error: {type(e).__name__}: {e}")
            if retry_count >= max_retries:
                print(f"Failed after {max_retries} attempts. Exiting.")
                break
            
            retry_count += 1
            wait_time = retry_delay * (2 ** (retry_count - 1))
            print(f"Retrying in {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
            await asyncio.sleep(wait_time)
        finally:
            if client.is_closed():
                await asyncio.sleep(5)  # Wait a bit before potentially reconnecting

# Run the bot with proper error handling
try:
    asyncio.run(start_bot())
except KeyboardInterrupt:
    print("Bot stopped by user.")
except Exception as e:
    print(f"Fatal error: {type(e).__name__}: {e}")
finally:
    # Ensure we close the bot client
    if not client.is_closed():
        asyncio.run(client.close())