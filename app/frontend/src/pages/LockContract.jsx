import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthoringStepper from '../components/AuthoringStepper';
import { getLockedContract, lockContract, getSummary } from '../api/client';

export default function LockContract() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [meta, setMeta] = useState(null);
  const [contract, setContract] = useState(null);
  const [auditReady, setAuditReady] = useState(false);
  const [auditStatus, setAuditStatus] = useState('');
  const [descTitle, setDescTitle] = useState('');
  const [locking, setLocking] = useState(false);
  const [locked, setLocked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check if already locked
    getLockedContract(id)
      .then(data => {
        setMeta(data.metadata);
        setContract(data.contract);
        setAuditReady(data.can_audit);
        setAuditStatus(data.audit_status);
        setLocked(true);
      })
      .catch(() => {
        // Not locked yet — that's fine
      })
      .finally(() => setLoading(false));

    // Get description title
    getSummary(id)
      .then(data => setDescTitle(data.summary?.description_id || id))
      .catch(() => {});
  }, [id]);

  const handleLock = async () => {
    setLocking(true);
    setError(null);
    try {
      const data = await lockContract(id);
      setMeta(data.metadata);
      setLocked(true);
      // Reload full data
      const full = await getLockedContract(id);
      setContract(full.contract);
      setAuditReady(full.can_audit);
      setAuditStatus(full.audit_status);
    } catch (e) {
      setError(e.message);
    } finally {
      setLocking(false);
    }
  };

  if (loading) return <div className="loading"><div className="spinner" /> Checking lock status...</div>;

  return (
    <div>
      <AuthoringStepper currentStep={6} />

      <div className="page-header">
        <h1 className="page-title">{locked ? 'Contract Locked' : 'Lock Contract'}</h1>
        <p className="page-subtitle">
          {locked
            ? 'Your contract is locked and ready for auditing.'
            : 'Review and lock the contract to prevent post-hoc modifications before audit.'}
        </p>
      </div>

      {error && <div className="failure-box" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Lock Summary Card */}
      <div className="card lock-summary" style={{ maxWidth: 640, margin: '0 auto', marginBottom: 20 }}>
        {locked && meta ? (
          <>
            <div className="lock-success-banner">
              <div className="lock-success-icon">🔒</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>Contract Locked</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  {meta.locked_at ? `Locked at ${new Date(meta.locked_at).toLocaleString()}` : 'Locked'}
                </div>
              </div>
            </div>

            <div className="lock-meta-grid">
              <LockField label="Contract ID" value={meta.contract_id} mono />
              <LockField label="Version" value={`v${meta.version}`} />
              <LockField label="Source Scenario" value={meta.source_description_id} mono />
              <LockField label="Confirmed Assumptions" value={meta.confirmed_assumptions} />
              <LockField label="Unresolved Assumptions" value={meta.unresolved_assumptions}
                warn={meta.unresolved_assumptions > 0} />
              <LockField
                label="Contract Hash"
                value={meta.contract_hash}
                mono
                full
              />
            </div>

            <div style={{ marginTop: 20, padding: '12px 16px', background: auditReady ? 'var(--bg-sat)' : 'var(--warn-bg)', borderRadius: 8, fontSize: 13 }}>
              <span style={{ fontWeight: 600 }}>{auditReady ? '✓ Ready for Audit' : '⚠ Not Ready'}</span>
              <span style={{ marginLeft: 8, color: 'var(--text-secondary)' }}>{auditStatus}</span>
            </div>
          </>
        ) : (
          <>
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>🔓</div>
              <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Contract Ready to Lock</h3>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 400, margin: '0 auto', lineHeight: 1.6 }}>
                Locking prevents any modifications to the contract after this point.
                Any future edits will create a new version. Audits can only run on locked contracts.
              </p>
            </div>

            <div className="lock-meta-grid" style={{ marginTop: 16 }}>
              <LockField label="Source Scenario" value={id} mono />
              <LockField label="Version" value="v1.0 (new)" />
            </div>
          </>
        )}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 24 }}>
        <button className="btn" onClick={() => navigate(`/author/validate/${id}`)}>
          ← Back to Validation
        </button>

        {!locked ? (
          <button
            className="btn btn-primary"
            onClick={handleLock}
            disabled={locking}
            style={{ padding: '12px 32px', fontSize: 14 }}
            id="lock-contract-btn"
          >
            {locking ? (
              <>
                <div className="spinner" style={{ width: 14, height: 14, borderTopColor: '#fff', borderColor: 'rgba(255,255,255,0.3)' }} />
                Locking...
              </>
            ) : (
              '🔒 Lock Contract for Auditing'
            )}
          </button>
        ) : (
          <button
            className="btn btn-primary"
            onClick={() => navigate('/upload')}
            style={{ padding: '12px 32px', fontSize: 14 }}
            id="proceed-to-audit-btn"
          >
            Proceed to Audit →
          </button>
        )}
      </div>
    </div>
  );
}

function LockField({ label, value, mono, full, warn }) {
  return (
    <div className={`lock-field ${full ? 'lock-field-full' : ''}`}>
      <div className="lock-field-label">{label}</div>
      <div className={`lock-field-value ${mono ? 'mono' : ''} ${warn ? 'warn' : ''}`}>
        {value}
      </div>
    </div>
  );
}
