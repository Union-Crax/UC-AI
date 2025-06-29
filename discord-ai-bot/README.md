# Discord AI Bot

This project is a Discord bot that listens to chat messages and responds using an AI model running locally via Ollama. The bot is built using TypeScript and utilizes the Discord.js library for interaction with the Discord API.

## Features

- Listens for messages in Discord channels.
- Sends user messages to a local AI model for processing.
- Responds with AI-generated messages.

## Project Structure

```
discord-ai-bot
├── src
│   ├── bot.ts            # Main entry point for the Discord bot
│   ├── ai
│   │   └── ollamaClient.ts # Client for interacting with the local AI model
│   └── types
│       └── index.ts      # Type definitions for messages and responses
├── package.json           # npm configuration file
├── tsconfig.json          # TypeScript configuration file
└── README.md              # Project documentation
```

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd discord-ai-bot
   ```

2. Install the dependencies:
   ```
   npm install
   ```

## Configuration

Before running the bot, ensure you have set up your Discord bot token and (optionally) restricted the bot to a specific server and channel. Create a `.env` file in the root directory with the following content:

```
DISCORD_TOKEN=your_discord_bot_token
OLLAMA_API_URL=http://localhost:11434/api/generate
# Set these to restrict the bot to a specific server and channel
TARGET_GUILD_ID=your_server_id
TARGET_CHANNEL_ID=your_channel_id
```

- Replace `your_discord_bot_token` with your actual Discord bot token.
- Replace `your_server_id` and `your_channel_id` with the IDs of the server and channel you want the bot to listen to (leave blank to listen everywhere).

## Starting the Ollama Server

Before running the Discord bot, you need to start your local Ollama server. If you have Ollama installed, you can start the server with:

```
ollama serve
```

This will start the Ollama API on `http://localhost:11434` by default. Make sure your desired model (e.g., `llama3`) is available. You can pull a model with:

```
ollama pull llama3
```

Once the server is running and the model is available, you can start the Discord bot as described above.

## Usage

To start the bot, run the following command:

```
npm start
```

The bot will log in to Discord and begin listening for messages. When a message is received, it will send the message to the local AI model and respond with the generated output.

By default, the bot will use the `llama2:7b-chat` model. When you run `npm start`, it will automatically:
- Start the Ollama server
- Pull the `llama2:7b-chat` model (if not already pulled)
- Start the Discord bot

No manual steps are needed to start Ollama separately.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.