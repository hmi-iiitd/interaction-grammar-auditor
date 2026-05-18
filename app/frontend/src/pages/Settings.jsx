export default function Settings() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">LLM provider and application configuration</p>
      </div>

      <div className="detail-grid">
        <div className="card">
          <div className="card-title">LLM Provider</div>
          <div className="detail-row"><span className="detail-label">Provider</span><span className="detail-value">NVIDIA NIM</span></div>
          <div className="detail-row"><span className="detail-label">Primary Model</span><span className="detail-value">deepseek-ai/deepseek-v4-flash</span></div>
          <div className="detail-row"><span className="detail-label">Fallback</span><span className="detail-value">nvidia/nemotron-3-super-120b-a12b</span></div>
          <div className="detail-row"><span className="detail-label">Temperature</span><span className="detail-value">0.1</span></div>
          <div className="detail-row"><span className="detail-label">Max Tokens</span><span className="detail-value">2048</span></div>
        </div>
        <div className="card">
          <div className="card-title">Application</div>
          <div className="detail-row"><span className="detail-label">Backend</span><span className="detail-value">http://localhost:8000</span></div>
          <div className="detail-row"><span className="detail-label">Dataset</span><span className="detail-value">./dataset</span></div>
          <div className="detail-row"><span className="detail-label">Mode</span><span className="detail-value">Template (M2)</span></div>
          <div className="detail-row"><span className="detail-label">LLM Active</span><span className="detail-value" style={{color: 'var(--accent-amber)'}}>Pending M3</span></div>
        </div>
      </div>
    </div>
  );
}
