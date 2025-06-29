import fetch from 'node-fetch';
import * as fs from 'fs';
import * as path from 'path';

const SASSY_SYSTEM_PROMPT = `You are UnionCrax, a witty, sassy Discord user. Never say you are an AI, assistant, or bot. Never say you are here to help. Never mention being artificial or programmed. Respond like a real, clever, playful human. Keep replies extremely short (max 1-2 sentences), casual, and do not use emojis. Only mention your name (UnionCrax) if directly asked. Never write long paragraphs. Never break character. When referencing people, use their actual Discord display name, not 'user'. Never end a sentence with 'just don't...' or similar incomplete phrases. Always finish your sentences naturally. When someone posts a GIF or image, use the description provided to make a creative, sassy, and specific comment about what the image or GIF might show. Never reply with generic greetings or questions like 'hey there' or 'what's up'. If the description is about a character, meme, or scene, reference it directly in your response.`;

const MEMORY_PATH = path.join(__dirname, '../../userMemory.json');
const MAX_PROMPT_TOKENS = 1800; // ~1800 words, adjust for your model's context window

function loadMemory(): Record<string, { role: 'user' | 'ai', content: string, timestamp: string, displayName?: string }[]> {
    try {
        if (fs.existsSync(MEMORY_PATH)) {
            const raw = fs.readFileSync(MEMORY_PATH, 'utf-8');
            if (!raw.trim()) return {};
            return JSON.parse(raw);
        }
    } catch (e) {
        console.warn('Could not load memory:', e);
    }
    return {};
}

function saveMemory(memory: Record<string, { role: 'user' | 'ai', content: string, timestamp: string, displayName?: string }[]>) {
    try {
        fs.writeFileSync(MEMORY_PATH, JSON.stringify(memory, null, 2), 'utf-8');
    } catch (e) {
        console.warn('Could not save memory:', e);
    }
}

const userHistories: Record<string, { role: 'user' | 'ai', content: string, timestamp: string, displayName?: string }[]> = loadMemory();

function extractUserFacts(history: { role: 'user' | 'ai', content: string, timestamp: string, displayName?: string }[]): string[] {
    // Extract facts like name changes from user history
    const facts: string[] = [];
    for (const entry of history) {
        if (entry.role === 'user') {
            const match = entry.content.match(/(?:my name is|call me|from now on my name is)\s+([\w\s]+)/i);
            if (match) {
                facts.push(`This user wants to be called ${match[1].trim()}.`);
            }
        }
    }
    return facts;
}

class OllamaClient {
    private apiUrl: string;
    private processing: boolean = false;
    private queue: Array<{ message: string, userId: string, displayName: string, resolve: (v: string) => void, reject: (e: any) => void }> = [];

    constructor(apiUrl: string) {
        this.apiUrl = apiUrl;
    }

    async sendMessage(message: string, userId: string, displayName: string): Promise<string> {
        return new Promise((resolve, reject) => {
            this.queue.push({ message, userId, displayName, resolve, reject });
            this.processQueue();
        });
    }

    private async processQueue() {
        if (this.processing || this.queue.length === 0) return;
        this.processing = true;
        const { message, userId, displayName, resolve, reject } = this.queue.shift()!;
        try {
            // Add user message to history
            if (!userHistories[userId]) userHistories[userId] = [];
            userHistories[userId].push({ role: 'user', content: message, timestamp: new Date().toISOString(), displayName });
            // Only extract and use facts, not full memory
            const facts = extractUserFacts(userHistories[userId]);
            let memoryContext = '';
            if (facts.length > 0) {
                memoryContext = facts.join(' ');
            }
            const prompt = `${SASSY_SYSTEM_PROMPT}\n${memoryContext}\n${displayName}: ${message}\nUnionCrax:`;
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt,
                    stream: false,
                    model: 'llama2:7b-chat',
                    options: { temperature: 1.1, num_predict: 80 }
                }),
            });
            if (!response.ok) throw new Error('Failed to fetch response from AI model');
            const data = await response.json();
            const aiReply = data.response || data.message || JSON.stringify(data);
            // Save AI response to memory
            userHistories[userId].push({ role: 'ai', content: aiReply, timestamp: new Date().toISOString() });
            saveMemory(userHistories);
            resolve(aiReply);
        } catch (e) {
            reject(e);
        } finally {
            this.processing = false;
            this.processQueue();
        }
    }
}

export default OllamaClient;