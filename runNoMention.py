# import everything
import requests
import json
import discord
import tomllib
import ollama
import os # Don't panic!!! This is used to save the history file to the computer!

# LOAD VARIABLES FROM config.toml
with open("config.toml", 'rb') as f: # load config as f (f is short for file im just using slang, chat)
  config_data = tomllib.load(f)


# api info for ollama
TOKEN = config_data['discord']['token'] # Load token from config file
SERVER_ID = int(config_data['discord'].get('server_id', 0))
CHANNEL_ID = int(config_data['discord'].get('channel_id', 0))
API_URL = 'http://localhost:11434/api/chat'



# Define the path for the conversation history file
HISTORY_FILE_PATH = "history.json"

# Load conversation history from a file if it exists
def load_conversation_history():
	if os.path.exists(HISTORY_FILE_PATH):
		with open(HISTORY_FILE_PATH, 'r') as file:
			return json.load(file)
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

# Function to send a request to the Ollama API and get a response
def generate_response(prompt):
	# add user message to history
	conversation_history.append({
		"role": "user",
		"content": prompt
	})

	# Save the updated conversation history to the file
	save_conversation_history()

	data = {
		"model": config_data['ollama']['model'],  # Use model from config
		"messages": conversation_history, # Send the entire conversation history
		"stream": False
	}

	response = requests.post(API_URL, json=data)
	print("Raw Response Content:", response.text)  # This will print out the raw response for debug purposes.

	# try and except used for error catching
	try:
		# Attempt to parse the response as JSON
		response_data = response.json()
		assistant_message = response_data['message']['content']

		# Add the assistant's reply to the conversation history
		conversation_history.append({
			"role": "assistant",
			"content": assistant_message
		})

		return assistant_message
	except requests.exceptions.JSONDecodeError:
		return "Error: Invalid API response"

# When the bot is ready
@client.event
async def on_ready():
	print(f'Logged in as {client.user}')

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
	# Process every message
	prompt = message.content  # Get the message content as the prompt
	prompt = f"{message.author.display_name} says: " + prompt
	try:
		async with message.channel.typing():
			if prompt:
				response = generate_response(prompt)
				await message.channel.send(response)
			else:
				response = generate_response(prompt)
				await message.channel.send(response)
	except discord.errors.Forbidden:
		print(f"Error: Bot does not have permission to type in {message.channel.name}")
		return

# Run the bot
client.run(TOKEN)