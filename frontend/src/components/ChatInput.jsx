/**
 * ChatInput.jsx — Auto-growing textarea input with send button.
 */
import { useRef, useEffect } from 'react';

export default function ChatInput({ value, onChange, onSend, loading, placeholder }) {
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [value]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="input-area">
      <div className="input-row" role="form" aria-label="Send a question">
        <textarea
          id="chat-input"
          ref={textareaRef}
          className="chat-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || 'Ask anything about NYC taxi data...'}
          disabled={loading}
          rows={1}
          aria-label="Type your analytics question"
          aria-multiline="true"
        />
        <button
          id="send-button"
          className="send-button"
          onClick={onSend}
          disabled={loading || !value.trim()}
          aria-label={loading ? 'Generating answer...' : 'Send question'}
          title={loading ? 'Generating...' : 'Send (Enter)'}
        >
          {loading ? '⏳' : '➤'}
        </button>
      </div>
      <p className="input-hint">
        Press <kbd style={{ padding: '1px 5px', background: 'rgba(255,255,255,0.08)', borderRadius: 4, fontSize: 10 }}>Enter</kbd> to send ·
        <kbd style={{ padding: '1px 5px', background: 'rgba(255,255,255,0.08)', borderRadius: 4, fontSize: 10, marginLeft: 4 }}>Shift+Enter</kbd> for new line
      </p>
    </div>
  );
}
