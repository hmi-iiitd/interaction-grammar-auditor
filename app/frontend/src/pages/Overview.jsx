import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchScenario } from '../api/client';
import Stepper from '../components/Stepper';

export default function Overview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchScenario(id).then(setData).catch(console.error);
  }, [id]);

  if (!data) return <div className="loading"><div className="spinner" /> Loading scenario...</div>;

  const { metadata, audit_report: audit, trace } = data;
  const verdict = audit.verdict;
  const violations = audit.violations || [];
  const events = trace.events || [];
  const v = violations[0] || {};

  return (
    <div>
      <Stepper currentStep={2} />
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn" onClick={() => navigate('/')} style={{ padding: '4px 10px' }}>&larr;</button>
            <div className="card-title" style={{ fontSize: 20 }}>Scenario: {id}</div>
          </div>
          <span className={`badge ${verdict === 'SAT' ? 'badge-sat' : 'badge-unsat'}`} style={{ fontSize: 14, padding: '6px 16px' }}>
            {verdict} / {verdict === 'SAT' ? 'PASSED' : 'FAILED'}
          </span>
        </div>

        <div className="meta-grid">
          <div className="meta-item">
            <div className="meta-icon">It</div>
            <div><div className="meta-label">Interaction type</div><div className="meta-value">{metadata.interaction_type}</div></div>
          </div>
          <div className="meta-item">
            <div className="meta-icon">Rp</div>
            <div><div className="meta-label">Robot platform</div><div className="meta-value">{metadata.robot_platform}</div></div>
          </div>
          <div className="meta-item">
            <div className="meta-icon">Src</div>
            <div><div className="meta-label">Source</div><div className="meta-value">{metadata.source_bag || 'synthetic'}</div></div>
          </div>
          <div className="meta-item">
            <div className="meta-icon">Ct</div>
            <div><div className="meta-label">Contract</div><div className="meta-value">{audit.contract_id}</div></div>
          </div>
          <div className="meta-item">
            <div className="meta-icon">Ev</div>
            <div><div className="meta-label">Events extracted</div><div className="meta-value">{events.length}</div></div>
          </div>
          <div className="meta-item">
            <div className="meta-icon" style={{ background: violations.length > 0 ? '#fef2f2' : '#ecfdf5', color: violations.length > 0 ? '#dc2626' : '#16a34a' }}>Vi</div>
            <div><div className="meta-label">Violations</div><div className="meta-value" style={{ color: violations.length > 0 ? 'var(--unsat)' : 'var(--sat)' }}>{violations.length}</div></div>
          </div>
        </div>
      </div>

      {verdict === 'UNSAT' && violations.length > 0 && (
        <div className="card" style={{ marginBottom: 16, borderColor: '#fecaca' }}>
          <div className="card-title" style={{ color: 'var(--unsat)', marginBottom: 12 }}>Failure Summary</div>
          
          <div className="failure-box">
            The expected {v.expected_event || 'response'} did not occur within {v.deadline_seconds || 'the required'}s after the trigger event.
          </div>

          <div className="detail-row">
            <div className="detail-label">Trigger event</div>
            <div className="detail-value"><code>{v.trigger_event_id}</code> at {v.trigger_time}s</div>
          </div>
          <div className="detail-row">
            <div className="detail-label">Expected</div>
            <div className="detail-value">{v.expected_event || 'N/A'}</div>
          </div>
          <div className="detail-row">
            <div className="detail-label">Observed</div>
            <div className="detail-value">{v.observed_event || 'no matching event observed'}</div>
          </div>
          <div className="detail-row">
            <div className="detail-label">Failure site</div>
            <div className="detail-value">{v.site}</div>
          </div>
          <div className="detail-row">
            <div className="detail-label">Attribution</div>
            <div className="detail-value">{v.agent_attribution}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button className="btn-primary btn" onClick={() => navigate(`/timeline/${id}`)}>View Timeline</button>
        <button className="btn-outline btn" onClick={() => navigate(`/report/${id}`)}>View Report</button>
        <button className="btn" onClick={() => window.open(`http://localhost:8000/api/reports/${id}/markdown`, '_blank')}>Export Markdown Report</button>
        <button className="btn" onClick={() => window.open(`http://localhost:8000/api/reports/${id}/json`, '_blank')}>Export JSON Report</button>
      </div>
    </div>
  );
}
