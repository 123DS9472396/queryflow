/**
 * Sidebar.jsx — Query history sidebar for QueryFlow.
 * Shows past questions with timestamps, click to replay.
 */

const EXAMPLE_TOPICS = [
  { icon: '📊', label: 'Revenue by Hour' },
  { icon: '🚕', label: 'Trip Volume Trends' },
  { icon: '💳', label: 'Payment Analysis' },
  { icon: '📅', label: 'Day-of-Week Patterns' },
];

function formatTime(date) {
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export default function Sidebar({ history, onSelect, onNewChat }) {
  return (
    <aside className="sidebar" role="complementary" aria-label="Query history">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon" aria-hidden="true">🔍</div>
        <span className="sidebar-logo-text">QueryFlow</span>
      </div>

      {/* New Chat Button */}
      <button
        id="new-chat-btn"
        className="sidebar-new-chat"
        onClick={onNewChat}
        aria-label="Start new conversation"
      >
        <span>＋</span>
        <span>New conversation</span>
      </button>

      {/* History */}
      {history.length > 0 ? (
        <>
          <div className="sidebar-label">Recent queries</div>
          {history.map((item) => (
            <div
              key={item.id}
              className="sidebar-item"
              onClick={() => onSelect(item.question)}
              role="button"
              tabIndex={0}
              aria-label={`Replay: ${item.question}`}
              onKeyDown={e => e.key === 'Enter' && onSelect(item.question)}
            >
              <span className="sidebar-item-icon">💬</span>
              <div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 12 }}>
                  {item.question.length > 60
                    ? item.question.slice(0, 58) + '…'
                    : item.question}
                </div>
                <div style={{ color: 'var(--text-tertiary)', fontSize: 10, marginTop: 2 }}>
                  {formatTime(item.timestamp)}
                </div>
              </div>
            </div>
          ))}
        </>
      ) : (
        <>
          <div className="sidebar-label">Explore topics</div>
          {EXAMPLE_TOPICS.map((t, i) => (
            <div key={i} className="sidebar-item" style={{ cursor: 'default' }}>
              <span className="sidebar-item-icon">{t.icon}</span>
              <span>{t.label}</span>
            </div>
          ))}
        </>
      )}

      {/* Footer */}
      <div style={{
        marginTop: 'auto',
        padding: '12px 4px 0',
        borderTop: '1px solid var(--border-primary)',
        fontSize: 11,
        color: 'var(--text-tertiary)',
        lineHeight: 1.6,
      }}>
        <div>⚡ Groq LLaMA3-8b · free tier</div>
        <div>🏠 ClickHouse Cloud · free tier</div>
        <div style={{ marginTop: 6 }}>
          <a
            href="https://github.com/yourusername/queryflow"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--text-tertiary)', textDecoration: 'none' }}
          >
            ★ GitHub
          </a>
        </div>
      </div>
    </aside>
  );
}
