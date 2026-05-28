import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthoringStepper from '../components/AuthoringStepper';
import { getSummary, updateSummary } from '../api/client';

export default function ScenarioUnderstanding() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editSummary, setEditSummary] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getSummary(id)
      .then(d => {
        setData(d);
        setEditSummary(d.summary.structured_summary || '');
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const result = await updateSummary(id, { structured_summary: editSummary });
      setData(prev => ({ ...prev, summary: result.summary }));
      setEditing(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="loading"><div className="spinner" /> Loading summary...</div>;
  if (error) return <div className="failure-box">{error}</div>;
  if (!data) return null;

  const { summary, provenance } = data;

  return (
    <div>
      <AuthoringStepper currentStep={2} />

      <div className="page-header">
        <h1 className="page-title">Scenario Understanding</h1>
        <p className="page-subtitle">Review the system's interpretation of your scenario. Edit if needed before proceeding.</p>
      </div>

      {/* Structured Summary */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <div className="card-title">Structured Summary</div>
          <button className="btn" onClick={() => setEditing(!editing)}>
            {editing ? 'Cancel' : '✎ Edit'}
          </button>
        </div>
        {editing ? (
          <div>
            <textarea
              className="auth-textarea"
              value={editSummary}
              onChange={e => setEditSummary(e.target.value)}
              rows={6}
            />
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={saving}
              style={{ marginTop: 12 }}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        ) : (
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
            {summary.structured_summary}
          </p>
        )}
      </div>

      {/* Actors & Events */}
      <div className="detail-grid" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}>Detected Actors</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {(summary.actors || []).map(a => (
              <span key={a} className="badge badge-info">{a}</span>
            ))}
            {(!summary.actors || summary.actors.length === 0) && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>No actors detected</span>
            )}
          </div>
        </div>
        <div className="card">
          <div className="card-title" style={{ marginBottom: 12 }}>Detected Events</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {(summary.events || []).map(e => (
              <span key={e} className="auth-event-tag">{e}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Candidate Obligations */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-title" style={{ marginBottom: 16 }}>Candidate Obligations</div>
        {(summary.obligations || []).length === 0 ? (
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No obligations extracted.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Type</th>
                <th>Trigger</th>
                <th>Expected</th>
                <th>Deadline</th>
                <th>Site</th>
              </tr>
            </thead>
            <tbody>
              {summary.obligations.map((obl, i) => (
                <tr key={obl.obligation_id || i}>
                  <td style={{ fontWeight: 600 }}>{i + 1}</td>
                  <td>
                    <span className={`badge ${obl.obligation_type === 'sequence' ? 'badge-info' :
                      obl.obligation_type === 'repair' ? 'badge-warn' :
                      obl.obligation_type === 'conditional_sequence' ? 'badge-unsat' :
                      'badge-sat'}`}>
                      {obl.obligation_type}
                    </span>
                  </td>
                  <td><code>{obl.trigger || '—'}</code></td>
                  <td><code>{obl.expected || '—'}</code></td>
                  <td>
                    {obl.deadline_seconds != null
                      ? <span className="badge badge-sat">{obl.deadline_seconds}s</span>
                      : <span className="badge badge-warn">unspecified</span>
                    }
                  </td>
                  <td><code>{obl.site || '—'}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Missing Details & Ambiguities */}
      {((summary.missing_details || []).length > 0 || (summary.potential_ambiguities || []).length > 0) && (
        <div className="detail-grid" style={{ marginBottom: 20 }}>
          {(summary.missing_details || []).length > 0 && (
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>⚠ Missing Details</div>
              <ul style={{ paddingLeft: 20, fontSize: 13, color: 'var(--warn)' }}>
                {summary.missing_details.map((d, i) => <li key={i} style={{ marginBottom: 4 }}>{d}</li>)}
              </ul>
            </div>
          )}
          {(summary.potential_ambiguities || []).length > 0 && (
            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>? Potential Ambiguities</div>
              <ul style={{ paddingLeft: 20, fontSize: 13, color: 'var(--accent-blue)' }}>
                {summary.potential_ambiguities.map((a, i) => <li key={i} style={{ marginBottom: 4 }}>{a}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
        <button className="btn" onClick={() => navigate('/author')}>← Back</button>
        <button
          className="btn btn-primary"
          onClick={() => navigate(`/author/clarify/${id}`)}
          id="accept-and-continue-btn"
        >
          Accept & Continue →
        </button>
      </div>
    </div>
  );
}
