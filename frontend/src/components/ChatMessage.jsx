/**
 * ChatMessage.jsx — Renders a single chat bubble (user or assistant).
 *
 * Assistant messages contain:
 *   - Thinking animation (while loading)
 *   - Streamed natural language answer text
 *   - Collapsible SQL block with syntax highlighting
 *   - MiniChart with query results
 *   - Row count badge
 */
import { useState } from 'react';
import MiniChart from './MiniChart';

// Bot avatar SVG
const BotIcon = () => (
  <div className="message-avatar avatar-bot" aria-hidden="true">🔍</div>
);

// User avatar
const UserIcon = () => (
  <div className="message-avatar" style={{
    background: 'rgba(139,92,246,0.2)',
    border: '1px solid rgba(139,92,246,0.3)',
    fontSize: 13,
  }} aria-hidden="true">
    👤
  </div>
);

// LangGraph pipeline step indicator
function ThinkingIndicator({ step }) {
  const stepLabels = {
    'Starting...': '🔄 Starting pipeline...',
    'Generate Sql': '🧠 Generating SQL with Groq LLaMA3...',
    'Validate Sql': '🛡️ Validating SQL safety...',
    'Execute Query': '⚡ Querying ClickHouse...',
    'Generate Answer': '✍️ Writing answer...',
  };
  const label = stepLabels[step] || (step ? `⚙️ ${step}...` : '🔄 Thinking...');
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div className="thinking-dots" aria-label="Thinking...">
        <div className="thinking-dot" />
        <div className="thinking-dot" />
        <div className="thinking-dot" />
      </div>
      <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>{label}</span>
    </div>
  );
}

// Collapsible SQL block
function SQLBlock({ sql }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <details className="sql-toggle">
      <summary>
        <span style={{ fontSize: 12 }}>⚡</span>
        <span>View SQL</span>
        <button
          onClick={(e) => { e.preventDefault(); handleCopy(); }}
          style={{
            marginLeft: 8,
            padding: '1px 6px',
            borderRadius: 4,
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'transparent',
            fontSize: 10,
            color: copied ? '#10b981' : '#506080',
            cursor: 'pointer',
            transition: 'color 150ms',
          }}
        >
          {copied ? '✓ Copied' : 'Copy'}
        </button>
        <span className="sql-chevron">▾</span>
      </summary>
      <pre className="sql-code" role="region" aria-label="Generated SQL query">
        {sql}
      </pre>
    </details>
  );
}

// Welcome message (special)
function WelcomeMessage() {
  return (
    <div style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.7 }}>
      <span style={{ fontSize: 20 }}>👋</span>{' '}
      Hi! I'm <strong style={{ color: 'var(--accent)' }}>QueryFlow</strong> — ask me anything
      about NYC taxi data in plain English. I'll convert it to ClickHouse SQL,
      run it, and show you the results with a chart.
    </div>
  );
}

export default function ChatMessage({ message, onRetry }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="message-wrapper user" role="listitem">
        <div className="message-bubble bubble-user" aria-label={`You: ${message.text}`}>
          {message.text}
        </div>
        <UserIcon />
      </div>
    );
  }

  // Assistant message
  return (
    <div className="message-wrapper assistant" role="listitem">
      <BotIcon />
      <div className="message-bubble bubble-bot">
        {/* Welcome state */}
        {message.isWelcome && <WelcomeMessage />}

        {/* Thinking animation — shows current LangGraph node */}
        {message.isThinking && !message.text && !message.sql && (
          <ThinkingIndicator step={message.currentStep} />
        )}

        {/* Generating SQL indicator */}
        {message.isThinking && message.sql && !message.text && (
          <div style={{ color: 'var(--text-secondary)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ animation: 'pulse 1s ease infinite', display: 'inline-block' }}>⚡</span>
            Running query...
          </div>
        )}

        {/* Streaming answer text */}
        {message.text && (
          <div>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.7, color: message.isError ? '#f87171' : 'var(--text-primary)' }}>
              {message.text}
              {message.loading && (
                <span style={{ display:'inline-block', width:2, height:14, background:'var(--accent)', marginLeft:2, verticalAlign:'text-bottom', animation:'pulse 0.8s ease infinite' }} />
              )}
            </p>
            {/* Retry button on errors */}
            {message.isError && onRetry && (
              <button
                onClick={() => onRetry(message.question)}
                style={{ marginTop:10, display:'inline-flex', alignItems:'center', gap:6, background:'rgba(248,113,113,0.1)', color:'#f87171', border:'1px solid rgba(248,113,113,0.25)', borderRadius:8, padding:'6px 14px', fontSize:12, fontWeight:700, cursor:'pointer', transition:'all 0.2s' }}
                onMouseEnter={e => e.currentTarget.style.background='rgba(248,113,113,0.2)'}
                onMouseLeave={e => e.currentTarget.style.background='rgba(248,113,113,0.1)'}>
                🔄 Retry this query
              </button>
            )}
          </div>
        )}

        {/* SQL collapsible block */}
        {message.sql && <SQLBlock sql={message.sql} />}

        {/* Mini chart */}
        {message.data && message.data.length > 0 && (
          <MiniChart data={message.data} />
        )}

        {/* Row count */}
        {message.data && !message.loading && (
          <div className="row-count">
            <span>📋</span>
            <span>{message.data.length} row{message.data.length !== 1 ? 's' : ''} returned</span>
          </div>
        )}
      </div>
    </div>
  );
}
