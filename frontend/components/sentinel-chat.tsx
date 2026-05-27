'use client';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import remarkGfm from 'remark-gfm';
import { FormEvent, useEffect, useRef, useState } from 'react';

type ChatRole = 'user' | 'assistant' | 'system';
type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  meta?: string;
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
      content: 'SENTINEL is online. Submit an instruction and the agent will stream progress, fallback events, and final results.',
      meta: 'Ready',
    },
  ]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [liveStatus, setLiveStatus] = useState('Idle and ready');
  const [activeProvider, setActiveProvider] = useState('Primary lane');
  const [lastLatency, setLastLatency] = useState<number | null>(null);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const assistantMessageIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isStreaming]);


  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

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
    setIsStreaming(true);
    setLiveStatus('Connecting to backend stream...');

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

          }

          if (envelope.event === 'token') {
            const responseText = envelope.data.payload?.token ?? 'No content returned.';
            await animateMessage(updateAssistantMessage, responseText);
          }

          if (envelope.event === 'completion') {
            const provider = envelope.data.payload?.provider ?? 'Primary lane';
            const elapsed = Math.round(performance.now() - startedAt);

            setLastLatency(elapsed);
            setActiveProvider(provider);
            setLiveStatus(`Completed in ${elapsed}ms`);

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
          <span className="eyebrow">Operational Console</span>
          <h1 className="hero-title">SENTINEL</h1>
          <p className="hero-subtitle">
            A resilient AI orchestration console with fallback routing, tool execution,
            and live streaming responses for incident response and automation.
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

      <section className="layout-grid chat-central">
        <div className="panel chat-layout">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Agent Workspace</h2>
              <p className="panel-subtitle">Interact with Sentinel and observe live progress.</p>
            </div>
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
                 <ReactMarkdown
                 remarkPlugins={[remarkMath,remarkGfm]}
                 rehypePlugins={[rehypeKatex]}
                 >{message.content}</ReactMarkdown>
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
                }}
                placeholder="Describe the incident or task (e.g., 'Coordinate response for a water main break on 5th Ave')"
                rows={5}
              />

              <div className="composer-row">
                <p className="composer-note">
                  Send an instruction and review the live response as Sentinel processes it.
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
      </section>
    </main>
  );
}