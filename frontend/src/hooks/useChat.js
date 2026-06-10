/**
 * useChat.js — Core chat state management hook for QueryFlow.
 *
 * Manages:
 *  - messages array (user + assistant)
 *  - SSE streaming state
 *  - query history (for sidebar)
 *  - streaming token accumulation
 */
import { useState, useCallback, useRef } from 'react';
import { streamChat } from '../services/api';

const INITIAL_MESSAGE = {
  id: 'welcome',
  role: 'assistant',
  text: '',
  sql: null,
  data: null,
  loading: false,
  isWelcome: true,
};

export function useChat() {
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState([]); // for sidebar
  const abortRef = useRef(null);

  const updateLastMessage = useCallback((updater) => {
    setMessages(prev => {
      const msgs = [...prev];
      const last = { ...msgs[msgs.length - 1] };
      msgs[msgs.length - 1] = updater(last);
      return msgs;
    });
  }, []);

  const sendMessage = useCallback(async (question) => {
    if (!question.trim() || loading) return;

    // Add user message
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      text: question,
    };

    // Add empty assistant placeholder
    const botMsg = {
      id: `bot-${Date.now()}`,
      role: 'assistant',
      text: '',
      sql: null,
      data: null,
      loading: true,
      isThinking: true,
      question, // store for retry
    };

    setMessages(prev => [...prev, userMsg, botMsg]);
    setLoading(true);

    // Add to history for sidebar
    setHistory(prev => [
      { id: Date.now(), question, timestamp: new Date() },
      ...prev.slice(0, 19), // keep last 20
    ]);

    try {
      await streamChat(question, {
        onThinking: () => {
          updateLastMessage(msg => ({ ...msg, isThinking: true, currentStep: 'Starting...' }));
        },
        onStep: (stepName) => {
          // LangGraph node progress: Generate Sql → Validate Sql → Execute Query → Generate Answer
          updateLastMessage(msg => ({ ...msg, currentStep: stepName, isThinking: true }));
        },
        onSQL: (sql) => {
          updateLastMessage(msg => ({ ...msg, sql, isThinking: false }));
        },
        onData: (data) => {
          updateLastMessage(msg => ({ ...msg, data }));
        },
        onToken: (token) => {
          updateLastMessage(msg => ({
            ...msg,
            text: msg.text + token,
            isThinking: false,
          }));
        },
        onDone: () => {
          updateLastMessage(msg => ({ ...msg, loading: false, isThinking: false }));
          setLoading(false);
        },
        onError: (err) => {
          updateLastMessage(msg => ({
            ...msg,
            text: `⚠️ ${err}`,
            loading: false,
            isThinking: false,
            isError: true,
          }));
          setLoading(false);
        },
      });
    } catch (err) {
      updateLastMessage(msg => ({
        ...msg,
        text: `⚠️ Connection error: ${err.message}`,
        loading: false,
        isThinking: false,
        isError: true,
      }));
      setLoading(false);
    }
  }, [loading, updateLastMessage]);

  const clearMessages = useCallback(() => {
    setMessages([INITIAL_MESSAGE]);
    setLoading(false);
  }, []);

  return { messages, loading, history, sendMessage, clearMessages };
}
