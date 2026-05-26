'use client';

import { useEffect, useMemo, useState } from 'react';
import { SentinelChat } from '@/components/sentinel-chat';

type ChaosState = {
  kill_claude: boolean;
  latency_spike: boolean;
  mcp_crash: boolean;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
const CHAOS_ENDPOINT = `${API_BASE}/api/v1/chaos`;

const CHAOS_CONTROLS: Array<{
  key: keyof ChaosState;
  title: string;
  label: string;
  description: string;
}> = [
  {
    key: 'kill_claude',
    title: 'Kill Claude API',
    label: 'Disable the primary model',
    description: 'Simulates a complete primary model outage, forcing the pipeline to route to fallback and emergency tiers.',
  },
  {
    key: 'latency_spike',
    title: 'Latency Spike',
    label: 'Add a 10s delay',
    description: 'Simulates network or provider slowness so you can test checkpointing and streaming behavior.',
  },
  {
    key: 'mcp_crash',
    title: 'MCP Server Crash',
    label: 'Fail tool execution',
    description: 'Simulates a tool runtime outage and triggers circuit-breaker fallback behavior in the tool layer.',
  },
];

function formatChaosLabel(state: ChaosState) {
  const enabled = Object.entries(state)
    .filter(([, value]) => value)
    .map(([key]) => key.replace('_', ' '));

  if (!enabled.length) {
    return 'Stable';
  }

  return `Chaos active: ${enabled.join(', ')}`;
}

export function ChaosDashboard() {
  const [chaos, setChaos] = useState<ChaosState>({
    kill_claude: false,
    latency_spike: false,
    mcp_crash: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function loadState() {
      try {
        const response = await fetch(CHAOS_ENDPOINT);
        if (!response.ok) {
          throw new Error(`Unable to load chaos state: ${response.status}`);
        }
        const data = await response.json();
        setChaos(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load chaos state');
      }
    }

    loadState();
  }, []);

  async function toggleChaos(feature: keyof ChaosState) {
    const nextState = {
      ...chaos,
      [feature]: !chaos[feature],
    };

    setChaos(nextState);
    setSaving(true);
    setError(null);

    try {
      const response = await fetch(CHAOS_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ [feature]: nextState[feature] }),
      });
      if (!response.ok) {
        throw new Error(`Unable to update chaos state: ${response.status}`);
      }
      const data = await response.json();
      setChaos(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update chaos state');
    } finally {
      setSaving(false);
    }
  }

  const summary = useMemo(
    () => ({
      active: formatChaosLabel(chaos),
      tierSummary: [
        { label: 'Tier 1 (Primary)', value: 'Claude 3.5 Sonnet', status: chaos.kill_claude ? 'Disabled' : 'Online' },
        { label: 'Tier 2 (Fallback)', value: 'GPT-4o-mini', status: 'Ready' },
        { label: 'Tier 3 (Emergency)', value: 'Local Llama 3', status: 'Available' },
      ],
    }),
    [chaos],
  );

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">TrueFoundry Hackathon Demo</span>
          <h1 className="hero-title">SENTINEL</h1>
          <p className="hero-subtitle">
            A mission-critical AI cockpit with live fallback control, chaos toggles, and a resilient response stream.
            Use the dashboard to break the primary path and prove the failover story in under three minutes.
          </p>
        </div>

        <div className="hero-status">
          <div className="status-pill">
            <span className="status-dot" />
            <strong>{summary.active}</strong>
          </div>
          <div className="status-pill">
            <small>Demo mode</small>
            <strong>{saving ? 'Applying changes…' : 'Interactive'}</strong>
          </div>
        </div>
      </section>

      <section className="layout-grid">
        <div className="panel chat-layout">
          <SentinelChat chaosStatus={chaos} />
        </div>

        <aside className="panel panel--solid">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Chaos Dashboard</h2>
              <p className="panel-subtitle">
                Control model routing, latency, and tool stability from a single pane.
              </p>
            </div>
            <span className="pill">Dynamic resilience</span>
          </div>

          <div className="dash">
            <section>
              <div className="section-heading">Simulation controls</div>
              <div className="signal-list">
                {CHAOS_CONTROLS.map((control) => (
                  <button
                    key={control.key}
                    type="button"
                    className="toggle-row"
                    onClick={() => toggleChaos(control.key)}
                    disabled={saving}
                  >
                    <div>
                      <div className="toggle-label">
                        <strong>{control.title}</strong>
                      </div>
                      <div className="toggle-caption">{control.description}</div>
                    </div>
                    <div className={`toggle-switch ${chaos[control.key] ? 'toggle-switch--active' : ''}`}>
                      <span>{chaos[control.key] ? 'ON' : 'OFF'}</span>
                    </div>
                  </button>
                ))}
              </div>
            </section>

            <section>
              <div className="section-heading">Routing tiers</div>
              <div className="metrics">
                {summary.tierSummary.map((item) => (
                  <article key={item.label} className="metric-card">
                    <span className="metric-value">{item.value}</span>
                    <div className="metric-label">{item.label}</div>
                    <div className="metric-label">{item.status}</div>
                  </article>
                ))}
              </div>
            </section>

            <section>
              <div className="section-heading">Proof-ready demo script</div>
              <article className="metric-card">
                <p className="metric-label">
                  1. Enable <strong>Kill Claude API</strong> to force tiered routing.
                </p>
                <p className="metric-label">
                  2. Send a prompt that mentions tools and recovery, then watch streaming fallback events.
                </p>
                <p className="metric-label">
                  3. Turn on <strong>Latency Spike</strong> and show how the system maintains progress without resetting.
                </p>
                <p className="metric-label">
                  4. Activate <strong>MCP Server Crash</strong> and demonstrate the safe circuit breaker response.
                </p>
              </article>
            </section>

            {error ? (
              <section>
                <div className="signal-item signal-item--error">
                  <div>
                    <div className="signal-title">Chaos sync error</div>
                    <div className="signal-detail">{error}</div>
                  </div>
                </div>
              </section>
            ) : null}
          </div>
        </aside>
      </section>
    </main>
  );
}
