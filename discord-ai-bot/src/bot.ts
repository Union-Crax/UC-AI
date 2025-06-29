import { Client, GatewayIntentBits } from 'discord.js';
import OllamaClient from './ai/ollamaClient';
import * as dotenv from 'dotenv';
import { randomInt } from 'crypto';
dotenv.config();

const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent] });
const ollamaClient = new OllamaClient(process.env.OLLAMA_API_URL || 'http://localhost:11434/api/generate');

const TARGET_GUILD_ID = process.env.TARGET_GUILD_ID;
const TARGET_CHANNEL_ID = process.env.TARGET_CHANNEL_ID;

const HUMAN_EMOJIS = ['😀', '😂', '😅', '😎', '👍', '😮', '😜', '🤔', '🙌', '🔥', '🥳', '😇', '😏', '😬', '😃'];
const HUMAN_REPLIES = [
    "Haha, that's funny!",
    "I totally agree!",
    "Interesting point!",
    "Can you tell me more?",
    "Nice!",
    "😂",
    "👍",
    "That's cool!",
    "I hadn't thought of that!",
    "Good one!"
];

// Advanced: context-aware reactions and replies
const KEYWORD_EMOJIS: Record<string, string[]> = {
    'funny': ['😂', '🤣'],
    'cool': ['😎', '🔥'],
    'sad': ['😢', '😞'],
    'happy': ['😃', '🥳'],
    'wow': ['😮', '🤯'],
    'love': ['😍', '❤️'],
    'angry': ['😡', '😤'],
};

function getContextualEmoji(message: string): string | null {
    const lower = message.toLowerCase();
    for (const [keyword, emojis] of Object.entries(KEYWORD_EMOJIS)) {
        if (lower.includes(keyword)) {
            return emojis[randomInt(0, emojis.length)];
        }
    }
    return null;
}

client.on('ready', () => {
    console.log(`Logged in as ${client.user?.tag}`);
});

client.on('messageCreate', async (message) => {
    if (message.author.bot) return;
    if (TARGET_GUILD_ID && message.guild?.id !== TARGET_GUILD_ID) return;
    if (TARGET_CHANNEL_ID && message.channel.id !== TARGET_CHANNEL_ID) return;

    const userMessage = message.content;
    const botUser = client.user;
    const mentioned = message.mentions.has(botUser!);
    const isReplyToBot = message.reference && message.reference.messageId;
    let repliedToBot = false;
    if (isReplyToBot) {
        try {
            const repliedMsg = await message.channel.messages.fetch(message.reference!.messageId!);
            if (repliedMsg.author.id === botUser!.id) repliedToBot = true;
        } catch {}
    }
    const displayName = message.member?.displayName || message.author.username;
    const lowerMsg = userMessage.toLowerCase();
    const triggers = ["uc", "unioncrax", "union crax", "ai"];
    const containsTrigger = triggers.some(t => lowerMsg.includes(t));

    if (!mentioned && !repliedToBot && !containsTrigger) {
        // Context-aware emoji reaction (20% chance)
        if (Math.random() < 0.2) {
            let emoji = getContextualEmoji(userMessage);
            if (!emoji && Math.random() < 0.3) {
                emoji = HUMAN_EMOJIS[randomInt(0, HUMAN_EMOJIS.length)];
            }
            if (emoji) {
                try {
                    await message.react(emoji);
                } catch (e) {
                    console.warn('Could not react to message:', e);
                }
            }
        }
        return;
    }

    // Always reply if mentioned, replied to, or contains trigger
    try {
        let aiResponse = await ollamaClient.sendMessage(userMessage, message.author.id, displayName);
        // 20% chance to add contextual emoji to the AI response
        if (Math.random() < 0.2) {
            let emoji = getContextualEmoji(aiResponse);
            if (!emoji) emoji = HUMAN_EMOJIS[randomInt(0, HUMAN_EMOJIS.length)];
            aiResponse = `${emoji} ${aiResponse} ${emoji}`;
        }
        await message.reply(aiResponse);
    } catch (error) {
        console.error('Error responding to message:', error);
        await message.reply('Sorry, I encountered an error while processing your request.');
    }

    // Check for attachments (images/gifs)
    if (message.attachments.size > 0) {
        for (const attachment of message.attachments.values()) {
            const fileName = attachment.name || 'file';
            const url = attachment.url;
            let prompt = `A user posted a file named: ${fileName}.`;
            // If it's a gif or image link, describe it for the AI
            if (/\.(gif|jpg|jpeg|png|webp)$/i.test(fileName) || /tenor\.com|giphy\.com|imgur\.com|\.gif/i.test(url)) {
                // Extract a readable description from the filename or url
                let desc = fileName.replace(/[-_]/g, ' ').replace(/\.[^/.]+$/, '');
                // Try to extract a meaningful description from the URL (e.g. for Tenor, Giphy, etc.)
                let context = '';
                if (/tenor\.com/i.test(url)) {
                    // Extract the last part after /view/ and before -gif or end
                    const match = url.match(/tenor\.com\/view\/([\w-]+)/i);
                    if (match && match[1]) {
                        context = match[1].replace(/-/g, ' ');
                    }
                } else if (/giphy\.com/i.test(url)) {
                    const match = url.match(/giphy\.com\/gifs\/([\w-]+)/i);
                    if (match && match[1]) {
                        context = match[1].replace(/-/g, ' ');
                    }
                }
                // Prefer context if it's more descriptive
                let fullDesc = context || desc;
                prompt = `A user posted a GIF or image: "${fullDesc}". React with a very short, sassy, human-like comment about what the GIF or image might show, based on this description. Don't mention being an AI or bot. Use the user's display name if needed. Never say you can't see the image. Never just say 'hey there' or 'what's up'.`;
            }
            try {
                let aiResponse = await ollamaClient.sendMessage(prompt, message.author.id, displayName);
                if (Math.random() < 0.2) {
                    let emoji = getContextualEmoji(fileName);
                    if (!emoji) emoji = HUMAN_EMOJIS[randomInt(0, HUMAN_EMOJIS.length)];
                    aiResponse = `${emoji} ${aiResponse} ${emoji}`;
                }
                await message.reply(aiResponse);
            } catch (error) {
                console.error('Error responding to attachment:', error);
            }
        }
        return;
    }
});

client.login(process.env.DISCORD_TOKEN);