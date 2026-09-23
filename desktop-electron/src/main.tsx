import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

type Health = { ok: boolean; model: string; camera_port: number; version: string };

declare global { interface Window { projected: { health: () => Promise<Health> } } }

function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { window.projected.health().then(setHealth).catch((e: Error) => setError(e.message)); }, []);
  return <main className="shell">
    <div className="eyebrow">PROJECTED AI INTERFACE / V2</div>
    <h1>Local desktop control</h1>
    <p className="lede">Camera input stays on your local network. The desktop ships with its model assets and does not download them at runtime.</p>
    <section className="card">
      <div className={`status ${health?.ok ? 'ready' : ''}`}><span />{health?.ok ? 'READY' : error || 'Starting local backend…'}</div>
      <dl>
        <div><dt>Local model</dt><dd>{health?.model || 'SmolLM-135M'}</dd></div>
        <div><dt>Camera receiver</dt><dd>ws://local-network:{health?.camera_port || 8765}/frames</dd></div>
        <div><dt>Runtime</dt><dd>{health?.version || 'v2 desktop bundle'}</dd></div>
      </dl>
    </section>
  </main>;
}

createRoot(document.getElementById('root')!).render(<App />);
