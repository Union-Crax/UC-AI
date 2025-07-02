# simple-discord-ai
A self-hostable chatbot for Discord that utilizes ollama.

## Installation
1. [Install Ollama](https://ollama.com/download/)
2. `pip install discord.py ollama requests`
3. Open `config.toml` and enter your model, bot token and optional system prompt
4. Run `run.py` (the script will automatically start the Ollama server if needed and pull your chosen model)

## Usage
To use the bot, ping it via its username (e.g. @bot) or reply to it.

This bot only responds when mentioned (unless NoMention = true), in the server and channel you specify in `config.toml`.

Any contributions to this would be greatly appreciated. 

## TODO
- Clean code up
- Squash some bugs
- add history "cleaning" (cleans past lines to save on storage, ram, and vram)