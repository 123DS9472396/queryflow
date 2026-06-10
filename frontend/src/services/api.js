/**
 * api.js — SSE streaming client for QueryFlow backend.
 *
 * Handles the Server-Sent Events protocol:
 *   POST /api/chat → streaming response of typed events
 *   { type: "thinking" | "sql" | "data" | "token" | "done" | "error" }
 */

const API_BASE = import.meta.env.VITE_API_URL || '';
// Empty string = use Vite proxy → localhost:8000 during dev

/**
 * streamChat — send a question and receive typed SSE events.
 *
 * @param {string} question - Natural language question
 * @param {object} callbacks
 *   .onThinking()         - LLM generation started
 *   .onSQL(sql)           - Generated SQL received
 *   .onData(rows)         - ClickHouse result rows received
 *   .onToken(text)        - Streaming answer token received
 *   .onDone()             - Stream complete
 *   .onError(message)     - Error received
 */
export async function streamChat(question, callbacks) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const errText = await response.text();
    callbacks.onError?.(`Server error ${response.status}: ${errText}`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Split on double newline (SSE event boundary)
    const parts = buffer.split('\n\n');
    buffer = parts.pop(); // keep incomplete trailing chunk

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith('data: ')) continue;

      try {
        const payload = JSON.parse(line.slice(6));

        switch (payload.type) {
          case 'thinking': callbacks.onThinking?.(); break;
          case 'step':     callbacks.onStep?.(payload.content); break;
          case 'sql':      callbacks.onSQL?.(payload.content); break;
          case 'data':     callbacks.onData?.(payload.content); break;
          case 'token':    callbacks.onToken?.(payload.content); break;
          case 'done':     callbacks.onDone?.(); break;
          case 'error':    callbacks.onError?.(payload.content); break;
          default:         console.warn('[SSE] Unknown event type:', payload.type);
        }
      } catch (parseErr) {
        console.warn('[SSE] Failed to parse event:', line, parseErr);
      }
    }
  }

  callbacks.onDone?.(); // safety: ensure done is always called
}

/**
 * fetchSuggestions — load example questions from backend.
 */
export async function fetchSuggestions() {
  try {
    const res = await fetch(`${API_BASE}/api/suggestions`);
    const data = await res.json();
    return data.suggestions || [];
  } catch {
    return [
      "What were the top 5 revenue hours on weekdays?",
      "Which payment method is most popular?",
      "Show me average trip distance by day of week",
      "What day had the most trips in January 2015?",
      "Compare credit card vs cash tip amounts",
    ];
  }
}
