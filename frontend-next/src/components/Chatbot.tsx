'use client';
import React, { useState } from 'react';
import styles from './Chatbot.module.css';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: string[];
  credibility?: number;
}

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    role: 'user',
    content: 'Will there be heavy rain in Pune today?',
    timestamp: '15:31',
  },
  {
    role: 'assistant',
    content:
      'Yes, there is a high probability of heavy rain in Pune today. Current observations show 12.4 mm rainfall in the last 24 hours with moderate to heavy rain expected in the next 6 hours. The IMD has issued a Heavy Rainfall Warning for Pune and nearby districts.',
    timestamp: '15:32',
    sources: ['IMD', 'MOSDAC', 'GFS', 'ERA5', 'RAG', 'Safety Guardrail'],
    credibility: 0.74,
  },
];

const QUICK_PROMPTS = [
  'Flood risk?',
  'Why this alert?',
  'Farmer advice',
  'Show sources',
];

export default function Chatbot() {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim()) return;
    const newMsg: ChatMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }),
    };
    setMessages((prev) => [...prev, newMsg]);
    setInput('');
    // TODO: connect to WebSocket backend
  };

  return (
    <div className={`panel ${styles.chatPanel}`}>
      <div className="panel-header">
        <span>Chat with WeatherGPT</span>
        <button className={styles.clearBtn}>Clear Chat</button>
      </div>

      <div className={styles.messageList}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`${styles.message} ${
              msg.role === 'user' ? styles.userMsg : styles.assistantMsg
            }`}
          >
            <div className={styles.bubble}>
              <div className={styles.msgContent}>{msg.content}</div>
              {msg.sources && (
                <div className={styles.evidence}>
                  <div className={styles.evidenceLabel}>Sources used:</div>
                  <div className={styles.chipRow}>
                    {msg.sources.map((src, i) => (
                      <span
                        key={i}
                        className={`${styles.chip} ${
                          src === 'Safety Guardrail'
                            ? styles.chipSafety
                            : styles.chipSource
                        }`}
                      >
                        {src}
                      </span>
                    ))}
                  </div>
                  {msg.credibility !== undefined && (
                    <div className={styles.credScore}>
                      Avg. Credibility: <strong>{msg.credibility.toFixed(2)}</strong>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className={styles.msgTime}>{msg.timestamp}</div>
          </div>
        ))}
      </div>

      <div className={styles.quickPrompts}>
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            className={styles.quickBtn}
            onClick={() => setInput(prompt)}
          >
            {prompt}
          </button>
        ))}
      </div>

      <div className={styles.inputRow}>
        <input
          className={styles.input}
          type="text"
          placeholder="Ask about weather, risks, or get safety advice..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        />
        <button className={styles.sendBtn} onClick={handleSend}>
          ➤
        </button>
      </div>
    </div>
  );
}
