import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthoringStepper from '../components/AuthoringStepper';
import { validateDraft, mapEvents, confirmEventMapping } from '../api/client';

export default function ValidateAndMap() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [validation, setValidation] = useState(null);
  const [mappings, setMappings] = useState(null);
  const [hasUnresolved, setHasUnresolved] = useState(false);
  const [traceEventsInput, setTraceEventsInput] = useState('');
  const [validating, setValidating] = useState(false);
  const [mapping, setMapping] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    runValidation();
  }, [id]);

  const runValidation = async () => {
    setValidating(true);
    setError(null);
    try {
      const data = await validateDraft(id);
      setValidation(data.validation);
    } catch (e) {
      setError(e.message);
    } finally {
      setValidating(false);
      setLoading(false);
    }
  };

  const handleMapEvents = async () => {
    if (!traceEventsInput.trim()) return;
    setMapping(true);
    setError(null);
    try {
      const events = traceEventsInput.split(/[,\n]+/).map(e => e.trim()).filter(Boolean);
      const data = await mapEvents(id, events);
      setMappings(data.mappings);
      setHasUnresolved(data.has_unresolved);
    } catch (e) {
      setError(e.message);
    } finally {
      setMapping(false);
    }
  };

  const handleConfirm = async (contractEvent, traceEvents) => {
    try {
      const data = await confirmEventMapping(id, contractEvent, traceEvents);
      setMappings(data.mappings);
      setHasUnresolved(data.has_unresolved);
    } catch (e) {
      setError(e.message);
    }
  };

  const canProceed = validation?.all_passed;

  if (loading) return <div className="loading"><div className="spinner" /> Validating contract...</div>;

  return (
    <div>
      <AuthoringStepper currentStep={5} />

      <div className="page-header">
        <h1 className="page-title">Validation & Event Mapping</h1>
        <p className="page-subtitle">Validate the contract and map events to trace vocabulary before locking.</p>
      </div>

      {error && <div className="failure-box" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Validation Status */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <div className="card-title">Contract Validation</div>
          <button className="btn" onClick={runValidation} disabled={validating}>
            {validating ? 'Re-validating...' : '↻ Re-validate'}
          </button>
        </div>

        {validation && (
          <div>
            <div className="validation-grid">
              <ValidationCard
                label="Schema Validation"
                passed={validation.schema_valid}
                icon="📋"
              />
              <ValidationCard
                label="Semantic Validation"
                passed={validation.semantic_valid}
                icon="🔍"
              />
              <ValidationCard
                label="Repair Sites"
                passed={validation.repair_sites_valid}
                icon="🔧"
              />
            </div>

            {/* Errors */}
            {(validation.errors || []).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--unsat)' }}>
                  Errors
                </div>
                {validation.errors.map((err, i) => (
                  <div key={i} className="failure-box" style={{ marginBottom: 8, fontSize: 12 }}>
                    {err}
                  </div>
                ))}
              </div>
            )}

            {/* Warnings */}
            {(validation.warnings || []).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, color: 'var(--warn)' }}>
                  Warnings
                </div>
                {validation.warnings.map((w, i) => (
                  <div key={i} style={{ padding: '8px 12px', background: 'var(--warn-bg)', border: '1px solid #fde68a', borderRadius: 6, marginBottom: 6, fontSize: 12, color: '#92400e' }}>
                    {w}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Event Vocabulary Mapping */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <div className="card-title">Event Vocabulary Mapping</div>
          <span className="badge badge-info">Optional</span>
        </div>

        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
          If you have trace events from a ROS bag, paste them below to map contract events to trace vocabulary.
        </p>

        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <textarea
            className="auth-textarea"
            style={{ minHeight: 60, flex: 1 }}
            placeholder="Paste trace event names, one per line or comma-separated..."
            value={traceEventsInput}
            onChange={e => setTraceEventsInput(e.target.value)}
          />
          <button
            className="btn btn-outline"
            onClick={handleMapEvents}
            disabled={mapping || !traceEventsInput.trim()}
            style={{ alignSelf: 'flex-end' }}
          >
            {mapping ? 'Mapping...' : 'Auto-Map'}
          </button>
        </div>

        {/* Mapping Results */}
        {mappings && mappings.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>Contract Event</th>
                <th>Match Type</th>
                <th>Trace Event(s)</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {mappings.map((m, i) => (
                <tr key={i}>
                  <td><code>{m.contract_event}</code></td>
                  <td>
                    <span className={`badge ${
                      m.mapping_type === 'exact' ? 'badge-sat' :
                      m.mapping_type === 'fuzzy' ? 'badge-warn' : 'badge-unsat'
                    }`}>
                      {m.mapping_type}
                    </span>
                  </td>
                  <td>
                    {(m.trace_events || []).map(e => (
                      <code key={e} style={{ display: 'inline-block', marginRight: 4, marginBottom: 2 }}>{e}</code>
                    ))}
                    {(!m.trace_events || m.trace_events.length === 0) && <span style={{ color: 'var(--text-muted)' }}>—</span>}
                  </td>
                  <td>
                    <span className={`badge ${m.confirmed ? 'badge-sat' : 'badge-warn'}`}>
                      {m.confirmed ? '✓ Confirmed' : 'Pending'}
                    </span>
                  </td>
                  <td>
                    {!m.confirmed && m.trace_events && m.trace_events.length > 0 && (
                      <button
                        className="btn"
                        style={{ padding: '4px 10px', fontSize: 11 }}
                        onClick={() => handleConfirm(m.contract_event, m.trace_events)}
                      >
                        Confirm
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {hasUnresolved && (
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--warn)' }}>
            ⚠ Some mappings are unresolved. Confirm or update them before auditing.
          </div>
        )}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
        <button className="btn" onClick={() => navigate(`/author/preview/${id}`)}>← Back to Preview</button>
        <button
          className="btn btn-primary"
          onClick={() => navigate(`/author/lock/${id}`)}
          disabled={!canProceed}
          id="proceed-to-lock-btn"
        >
          {canProceed ? 'Proceed to Lock →' : 'Fix Errors First'}
        </button>
      </div>
    </div>
  );
}

function ValidationCard({ label, passed, icon }) {
  return (
    <div className="validation-card">
      <div className="validation-icon">{icon}</div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{label}</div>
        <span className={`badge ${passed ? 'badge-sat' : 'badge-unsat'}`} style={{ marginTop: 4 }}>
          {passed ? 'PASSED' : 'FAILED'}
        </span>
      </div>
    </div>
  );
}
