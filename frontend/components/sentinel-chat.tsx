'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';

type ChatRole = 'user' | 'assistant' | 'system';
type SignalTone = 'info' | 'success' | 'warning' | 'error';

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  meta?: string;
};

type Signal = {
  id: string;
  tone: SignalTone;
  title: string;
  detail: string;
};

type StreamEnvelope = {
  event: string;
  data: {
    type?: string;
    payload?: {
      message?: string;
      token?: string;
      provider?: string;
      status?: string;
    };
  };
};

const DEMO_PROMPTS = [
  {
    title: 'Resilience check',
    subtitle: 'Show fallback behavior under stress.',
    prompt: 'Explain what happens when the primary model is down.',
  },
  {
    title: 'Tool demo',
    subtitle: 'Trigger tool usage and summarize the output.',
    prompt: 'Search the workspace status and summarize the latest progress.',
  },
  {
    title: 'Hackathon pitch',
    subtitle: 'Turn the system into a crisp demo story.',
    prompt: 'Give me a 30 second demo pitch for Sentinel.',
  },
  {
    title: 'Recovery story',
    subtitle: 'Make the checkpointing value obvious.',
    prompt: 'Explain why checkpointing matters if the app crashes mid-task.',
  },
] as const;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
const STREAM_ENDPOINT = `${API_BASE}/api/v1/chat/stream`;

function uid() {
  return globalThis.crypto.randomUUID();
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function parseSseEvent(chunk: string): StreamEnvelope | null {
  const lines = chunk.split('\n');
  const eventLine = lines.find((line) => line.startsWith('event:'));
  const dataLine = lines.find((line) => line.startsWith('data:'));

  if (!eventLine || !dataLine) {
    return null;
  }

  const event = eventLine.slice('event:'.length).trim();
  const payload = dataLine.slice('data:'.length).trim();

  try {
    return {
      event,
      data: JSON.parse(payload) as StreamEnvelope['data'],
    };
  } catch {
    return null;
  }
}

async function animateMessage(
  updateMessage: (content: string) => void,
  text: string,
) {
  const step = Math.max(1, Math.ceil(text.length / 80));

  for (let index = step; index < text.length; index += step) {
    updateMessage(text.slice(0, index));
    await sleep(16);
  }

  updateMessage(text);
}

export function SentinelChat() {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uid(),
      role: 'assistant',
      content:
        'SENTINEL is online. Send a request and I will stream the result, show fallback events, and keep the demo moving even if the primary lane fails.',
      meta: 'Ready for live streaming',
    },
  ]);
  const [signals, setSignals] = useState<Signal[]>([
    {
      id: uid(),
      tone: 'success',
      title: 'Backend connection',
      detail: STREAM_ENDPOINT,
    },
    {
      id: uid(),
      tone: 'info',
      title: 'Resilience lane',
      detail: 'Primary model → fallback model → checkpointed recovery',
    },
    {
      id: uid(),
      tone: 'info',
      title: 'Tooling',
      detail: 'Search, file reader, calculator, and graph orchestration ready',
    },
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [liveStatus, setLiveStatus] = useState('Idle and ready');
  const [activeProvider, setActiveProvider] = useState('Primary lane');
  const [lastLatency, setLastLatency] = useState<number | null>(null);
  const [fallbackState, setFallbackState] = useState('Standby');
  const [draftPreview, setDraftPreview] = useState('');

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const assistantMessageIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const metrics = useMemo(
    () => [
      {
        label: 'Latency',
        value: lastLatency == null ? '--' : `${lastLatency}ms`,
        note: 'Measured from submit to stream completion.',
      },
      {
        label: 'Signals',
        value: `${signals.length}`,
        note: 'Live status events pushed from the backend.',
      },
      {
        label: 'Lane',
        value: fallbackState,
        note: 'Shows whether the primary or fallback route is active.',
      },
      {
        label: 'Endpoint',
        value: 'SSE',
        note: 'POST /api/v1/chat/stream returns live events.',
      },
    ],
    [fallbackState, lastLatency, signals.length],
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, signals, isStreaming]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  function pushSignal(tone: SignalTone, title: string, detail: string) {
    setSignals((current) => [
      { id: uid(), tone, title, detail },
      ...current,
    ].slice(0, 6));
  }

  function updateAssistantMessage(content: string) {
    const assistantId = assistantMessageIdRef.current;

    if (!assistantId) {
      return;
    }

    setMessages((current) =>
      current.map((message) =>
        message.id === assistantId
          ? {
              ...message,
              content,
            }
          : message,
      ),
    );
  }

  async function submitPrompt(text: string) {
    if (!text.trim() || isStreaming) {
      return;
    }

    abortRef.current?.abort();
    const abortController = new AbortController();
    abortRef.current = abortController;

    const userMessage: ChatMessage = {
      id: uid(),
      role: 'user',
      content: text,
      meta: 'Operator prompt',
    };

    const assistantId = uid();
    assistantMessageIdRef.current = assistantId;
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: 'Routing through Sentinel...',
      meta: 'Typing live',
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setPrompt('');
    setDraftPreview('');
    setIsStreaming(true);
    setLiveStatus('Connecting to backend stream...');
    setFallbackState('Primary lane');

    const startedAt = performance.now();

    try {
      const response = await fetch(STREAM_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({ prompt: text }),
        signal: abortController.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Stream request failed with HTTP ${response.status}`);
      }

      setLiveStatus('Live stream active');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        while (buffer.includes('\n\n')) {
          const boundary = buffer.indexOf('\n\n');
          const rawEvent = buffer.slice(0, boundary).trim();
          buffer = buffer.slice(boundary + 2);

          const envelope = parseSseEvent(rawEvent);

          if (!envelope) {
            continue;
          }

          if (envelope.event === 'status') {
            const message = envelope.data.payload?.message ?? 'Status update received.';
            setLiveStatus(message);
            pushSignal('info', 'System status', message);

            if (message.toLowerCase().includes('fallback') || message.toLowerCase().includes('unstable')) {
              setFallbackState('Fallback lane');
            }

            setMessages((current) => [
              ...current,
              {
                id: uid(),
                role: 'system',
                content: message,
                meta: 'Stream event',
              },
            ]);
          }

          if (envelope.event === 'token') {
            const responseText = envelope.data.payload?.token ?? 'No content returned.';
            await animateMessage(updateAssistantMessage, responseText);
            setDraftPreview(responseText);
          }

          if (envelope.event === 'completion') {
            const provider = envelope.data.payload?.provider ?? 'Primary lane';
            const elapsed = Math.round(performance.now() - startedAt);

            setLastLatency(elapsed);
            setActiveProvider(provider);
            setLiveStatus(`Completed in ${elapsed}ms`);
            setFallbackState(provider.toLowerCase().includes('fallback') ? 'Fallback lane' : 'Primary lane');
            pushSignal('success', 'Completion', `Response finished via ${provider}`);

            setMessages((current) =>
              current.map((message) =>
                message.id === assistantId
                  ? {
                      ...message,
                      meta: provider,
                    }
                  : message,
              ),
            );
          }

          if (envelope.event === 'error') {
            const message = envelope.data.payload?.message ?? 'Stream failed.';
            setLiveStatus('Encountered an error');
            setFallbackState('Error lane');
            pushSignal('error', 'Stream error', message);

            setMessages((current) => [
              ...current,
              {
                id: uid(),
                role: 'system',
                content: message,
                meta: 'Error',
              },
            ]);
          }
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown request failure';
      setLiveStatus('Request failed');
      setFallbackState('Error lane');
      pushSignal('error', 'Frontend request failed', message);

      setMessages((current) => [
        ...current,
        {
          id: uid(),
          role: 'system',
          content: `Frontend error: ${message}`,
          meta: 'Transport',
        },
      ]);
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitPrompt(prompt);
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">TrueFoundry Hackathon Demo</span>
          <h1 className="hero-title">SENTINEL</h1>
          <p className="hero-subtitle">
            A resilient AI orchestration cockpit with fallback routing, tool execution,
            and live streaming responses. Built to prove the demo, not to overbuild the
            stack.
          </p>
        </div>

        <div className="hero-status">
          <div className="status-pill">
            <span className="status-dot" />
            <strong>{liveStatus}</strong>
          </div>
          <div className="status-pill">
            <small>Active model lane</small>
            <strong>{activeProvider}</strong>
          </div>
        </div>
      </section>

      <section className="layout-grid">
        <div className="panel chat-layout">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Live command stream</h2>
              <p className="panel-subtitle">
                Send a prompt, watch the stream, and see failover state in real time.
              </p>
            </div>

            <span className="pill">POST /api/v1/chat/stream</span>
          </div>

          <div className="message-list">
            {messages.map((message) => (
              <article
                key={message.id}
                className={[
                  'message',
                  message.role === 'assistant' ? 'message--assistant' : '',
                  message.role === 'system' ? 'message--system' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                <div className="message-meta">
                  <span className="message-role">{message.role}</span>
                  <span>{message.meta ?? 'live'}</span>
                </div>
                <div
                  className={[
                    'message-content',
                    message.role === 'assistant' && message.id === assistantMessageIdRef.current && isStreaming
                      ? 'assistant-cursor'
                      : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                >
                  {message.content}
                </div>
              </article>
            ))}

            {isStreaming ? (
              <div className="message message--assistant">
                <div className="message-meta">
                  <span className="message-role">system</span>
                  <span>streaming</span>
                </div>
                <div className="typing-dots" aria-label="Typing in progress">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            ) : null}

            <div ref={bottomRef} />
          </div>

          <div className="composer">
            <form className="composer-inner" onSubmit={handleSubmit}>
              <textarea
                className="prompt-input"
                value={prompt}
                onChange={(event) => {
                  setPrompt(event.target.value);
                  setDraftPreview(event.target.value);
                }}
                placeholder="Ask Sentinel to summarize a roadmap, trigger fallback logic, inspect a file, or explain the recovery flow..."
                rows={5}
              />

              <div className="composer-row">
                <p className="composer-note">
                  Use the send button or a quick prompt. The UI consumes the SSE stream
                  and renders status, token, and completion events.
                </p>

                <div className="button-row">
                  <button
                    type="button"
                    className="button button--ghost"
                    onClick={() => {
                      abortRef.current?.abort();
                      setIsStreaming(false);
                      setLiveStatus('Stream cancelled');
                    }}
                    disabled={!isStreaming}
                  >
                    Stop stream
                  </button>

                  <button type="submit" className="button button--primary" disabled={isStreaming}>
                    {isStreaming ? 'Sending...' : 'Send prompt'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>

        <aside className="panel panel--solid">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Operator rail</h2>
              <p className="panel-subtitle">
                Demo cues, health signals, and quick actions for the hackathon stage.
              </p>
            </div>

            <span className="pill">Sentinel control room</span>
          </div>

          <div className="dash">
            <div className="metrics">
              {metrics.map((metric) => (
                <article key={metric.label} className="metric-card">
                  <span className="metric-value">{metric.value}</span>
                  <div className="metric-label">{metric.label}</div>
                  <div className="metric-label">{metric.note}</div>
                </article>
              ))}
            </div>

            <section>
              <div className="section-heading">Quick prompts</div>
              <div className="quick-grid">
                {DEMO_PROMPTS.map((item) => (
                  <button
                    key={item.title}
                    type="button"
                    className="quick-button"
                    onClick={async () => {
                      setPrompt(item.prompt);
                      setDraftPreview(item.prompt);
                      await submitPrompt(item.prompt);
                    }}
                    disabled={isStreaming}
                  >
                    <span className="quick-title">{item.title}</span>
                    <span className="quick-subtitle">{item.subtitle}</span>
                  </button>
                ))}
              </div>
            </section>

            <section>
              <div className="section-heading">Live signals</div>
              <div className="signal-list">
                {signals.map((signal) => (
                  <article key={signal.id} className="signal-item">
                    <span className={`signal-dot signal-dot--${signal.tone}`} />
                    <div>
                      <div className="signal-title">{signal.title}</div>
                      <div className="signal-detail">{signal.detail}</div>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="signal-item">
              <span className="signal-dot signal-dot--info" />
              <div>
                <div className="signal-title">Demo readiness</div>
                <div className="signal-detail">
                  {draftPreview
                    ? `Draft loaded: ${draftPreview.slice(0, 96)}${draftPreview.length > 96 ? '…' : ''}`
                    : 'Prompt preview appears here before sending. The stream is designed to make the failover story obvious on stage.'}
                </div>
              </div>
            </section>
          </div>
        </aside>
      </section>
    </main>
  );
}