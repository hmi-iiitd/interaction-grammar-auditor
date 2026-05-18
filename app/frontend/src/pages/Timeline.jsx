import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchAuditDetails } from '../api/client';

export default function Timeline() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchAuditDetails(id).then(setData).catch(console.error);
  }, [id]);

  if (!data) return <div className="loading"><div className="spinner" /> Loading timeline...</div>;

  const { trace, violations, counterexample, evidence } = data;
  const events = trace.events || [];
  const triggerIds = new Set(violations.map(v => v.trigger_event_id).filter(Boolean));

  const primLabel = (p) => {
    if (p === '\u03b1') return '\u03b1';
    if (p === '\u03c3') return '\u03c3';
    if (p === '\u03c1') return '\u03c1';
    if (p === '\u03b9') return '\u03b9';
    return p;
  };

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn" onClick={() => navigate(`/scenario/${id}`)} style={{ padding: '4px 10px' }}>&larr;</button>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Scenario: <strong>{id}</strong></div>
            <h1 className="page-title">Event Timeline</h1>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16, overflow: 'auto' }}>
        <div className="card-header">
          <div className="card-title">Event timeline</div>
          <span className="badge badge-info">{events.length} of {events.length} events</span>
        </div>
        <div className="timeline-horizontal">
          {events.map((evt, i) => {
            const isTrigger = triggerIds.has(evt.event_id);
            return (
              <div key={evt.event_id} className="timeline-event-h">
                <div className="timeline-time">{evt.timestamp.toFixed(2)}s</div>
                <div className={`timeline-node ${isTrigger ? 'trigger' : ''}`}>
                  {primLabel(evt.primitive)}
                </div>
                {i < events.length - 1 && <div className="timeline-connector" />}
                <div className="timeline-label">{evt.event_type}</div>
                <div className="timeline-sublabel">{evt.agent} &middot; {evt.modality}</div>
                <div className="timeline-eid">{evt.event_id}</div>
                {isTrigger && <div className="timeline-violation-label">TRIGGER</div>}
              </div>
            );
          })}
          {counterexample && (
            <div className="timeline-event-h">
              <div className="timeline-time">{counterexample.falsification?.time?.toFixed(2)}s</div>
              <div className="timeline-node violation">!</div>
              <div className="timeline-label" style={{ color: 'var(--unsat)', fontWeight: 600 }}>Violation</div>
              <div className="timeline-sublabel" style={{ color: 'var(--unsat)' }}>deadline passed</div>
              <span className="badge badge-unsat" style={{ marginTop: 4, fontSize: 10 }}>VIOLATION</span>
            </div>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {counterexample ? (
          <div className="card" style={{ borderColor: '#fecaca' }}>
            <div className="card-header">
              <div className="card-title" style={{ color: 'var(--unsat)' }}>Counterexample</div>
              <span className="badge badge-unsat">VIOLATION</span>
            </div>
            <div className="detail-row">
              <div className="detail-label">Violated obligation</div>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12, paddingLeft: 4 }}>
              {counterexample.violated_obligation}
            </p>
            <div className="detail-row">
              <div className="detail-label">Trigger</div>
              <div className="detail-value"><code>{counterexample.trigger.event_id}</code> at {counterexample.trigger.time}s</div>
            </div>
            <div className="detail-row">
              <div className="detail-label">Expected</div>
              <div className="detail-value">{counterexample.expected.event} in {counterexample.expected.time_window}</div>
            </div>
            <div className="detail-row">
              <div className="detail-label">Observed</div>
              <div className="detail-value">{counterexample.observed.description}</div>
            </div>
            <div className="detail-row">
              <div className="detail-label">Falsification</div>
              <div className="detail-value" style={{ color: 'var(--unsat)', fontWeight: 600 }}>
                {counterexample.falsification.time}s &mdash; {counterexample.falsification.description}
              </div>
            </div>
            <div className="detail-row">
              <div className="detail-label">Attribution</div>
              <div className="detail-value">{counterexample.attribution}</div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ borderColor: '#bbf7d0' }}>
            <div className="card-title" style={{ color: 'var(--sat)' }}>No Violations</div>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>
              This scenario satisfied all contract obligations.
            </p>
          </div>
        )}

        {evidence.length > 0 && evidence[0].window_events.length > 0 && (
          <div className="card">
            <div className="card-header">
              <div className="card-title">Evidence window ({evidence[0].window_start}s &ndash; {evidence[0].window_end}s)</div>
            </div>
            <table className="data-table" style={{ fontSize: 12 }}>
              <thead><tr><th>Time</th><th>Event</th><th>Details</th></tr></thead>
              <tbody>
                {evidence[0].window_events.map(evt => (
                  <tr key={evt.event_id} style={{ cursor: 'default' }}>
                    <td style={{ fontFamily: 'JetBrains Mono', fontSize: 11 }}>{evt.timestamp.toFixed(2)}s</td>
                    <td><span className="badge badge-info" style={{ fontSize: 10, marginRight: 6 }}>{evt.event_id}</span>{evt.event_type}</td>
                    <td style={{ color: 'var(--text-muted)' }}>{evt.agent} &middot; {evt.modality}{evt.object ? ` \u00b7 ${evt.object}` : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
