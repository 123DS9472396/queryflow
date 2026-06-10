/**
 * App.jsx — Root component for QueryFlow.
 *
 * Layout:
 *   ┌─────────────┬──────────────────────────────┐
 *   │  Sidebar    │  Header                      │
 *   │  (history)  ├──────────────────────────────┤
 *   │             │  Messages area               │
 *   │             │  (welcome or chat bubbles)   │
 *   │             ├──────────────────────────────┤
 *   │             │  Suggestion chips (once)     │
 *   │             │  ChatInput                   │
 *   └─────────────┴──────────────────────────────┘
 */
import { useState, useRef, useEffect } from 'react';
import { useChat } from './hooks/useChat';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';

const SUGGESTIONS = [
  { icon: '📈', text: 'What were the top 5 revenue hours on weekdays?' },
  { icon: '💳', text: 'Which payment method is most popular?' },
  { icon: '🗺️', text: 'Show me average trip distance by day of week' },
  { icon: '🕐', text: 'What is the busiest hour on Sundays?' },
  { icon: '💰', text: 'Compare credit card vs cash tip amounts' },
  { icon: '📅', text: 'What day had the most trips in January 2015?' },
];

export default function App() {
  const { messages, loading, history, sendMessage, clearMessages } = useChat();
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);
  const hasUserMessages = messages.some(m => m.role === 'user');

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || loading) return;
    sendMessage(q);
    setInput('');
  };

  const handleSuggestion = (text) => {
    if (loading) return;
    sendMessage(text);
  };

  const handleHistorySelect = (question) => {
    if (loading) return;
    sendMessage(question);
  };

  return (
    <div className="app-container">
      {/* Left sidebar — query history */}
      <Sidebar
        history={history}
        onSelect={handleHistorySelect}
        onNewChat={clearMessages}
      />

      {/* Main chat area */}
      <main className="chat-main" role="main">
        <Header />

        {/* Messages */}
        <div
          className="messages-area"
          role="list"
          aria-label="Conversation messages"
          aria-live="polite"
          aria-atomic="false"
        >
          {/* Welcome screen when no user messages yet */}
          {!hasUserMessages ? (
            <div className="welcome-screen">
              <div className="welcome-icon" aria-hidden="true">🔍</div>
              <div>
                <h2 className="welcome-title">Chat with your data</h2>
                <p className="welcome-subtitle">
                  Ask anything in plain English. QueryFlow runs on a <strong>Medallion Architecture</strong>, converting your query to{' '}
                  <span style={{ color: 'var(--accent)' }}>ClickHouse SQL</span>, and streaming back Power BI & Domo ready insights.
                </p>
              </div>

              {/* Suggestion chips */}
              <div className="welcome-chips" role="group" aria-label="Example questions">
                {SUGGESTIONS.map((s, i) => (
                  <button
                    key={i}
                    id={`suggestion-${i}`}
                    className="suggestion-chip"
                    onClick={() => handleSuggestion(s.text)}
                    aria-label={`Try: ${s.text}`}
                  >
                    <span className="chip-icon">{s.icon}</span>
                    {s.text}
                  </button>
                ))}
              </div>

              {/* Tech stack badges */}
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
                {['dbt', 'Airflow', 'Kafka', 'LangGraph', 'ClickHouse', 'Docker'].map(t => (
                  <span key={t} style={{
                    fontSize: 11, padding: '3px 10px',
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 20, color: 'var(--text-tertiary)',
                  }}>
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            /* Chat messages */
            messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} onRetry={sendMessage} />
            ))
          )}

          {/* Scroll anchor */}
          <div ref={bottomRef} aria-hidden="true" />
        </div>

        {/* Inline suggestion chips after first message */}
        {hasUserMessages && !loading && messages.length <= 3 && (
          <div style={{
            padding: '0 28px 12px',
            display: 'flex',
            flexWrap: 'wrap',
            gap: 6,
          }} role="group" aria-label="Quick question suggestions">
            {SUGGESTIONS.slice(0, 3).map((s, i) => (
              <button
                key={i}
                className="suggestion-chip"
                onClick={() => handleSuggestion(s.text)}
                style={{ fontSize: 11.5, padding: '5px 12px' }}
              >
                <span className="chip-icon">{s.icon}</span>
                {s.text}
              </button>
            ))}
          </div>
        )}

        {/* Input area */}
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          loading={loading}
        />
      </main>
    </div>
  );
}
