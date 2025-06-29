export interface Message {
    userId: string;
    content: string;
    timestamp: Date;
}

export interface BotResponse {
    responseId: string;
    content: string;
    timestamp: Date;
}