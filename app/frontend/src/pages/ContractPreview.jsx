import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthoringStepper from '../components/AuthoringStepper';
import { getDraft, generateContract } from '../api/client';

const TABS = ['Plain Language', 'IG Syntax', 'JSON', 'Provenance'];

export default function ContractPreview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [draft, setDraft] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  const loadDraft = async () => {
    try {
      const data = await getDraft(id);
      setDraft(data.draft);
    } catch {
      // Draft not generated yet — generate it
      setGenerating(true);
      try {
        const data = await generateContract(id);
        setDraft(data.draft);
      } catch (e) {
        setError(e.message);
      } finally {
        setGenerating(false);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadDraft(); }, [id]);

  const handleRegenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const data = await generateContract(id);
      setDraft(data.draft);
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <div className="loading"><div className="spinner" /> Loading contract draft...</div>;
  if (error && !draft) return <div className="failure-box">{error}</div>;

  return (
    <div>
      <AuthoringStepper currentStep={4} />

      <div className="page-header">
        <h1 className="page-title">Contract Preview</h1>
        <p className="page-subtitle">
          Review the generated contract in all representations. Edit or regenerate before validation.
        </p>
      </div>

      {error && <div className="failure-box" style={{ marginBottom: 16 }}>{error}</div>}

      {/* Tabs */}
      <div className="tab-header" style={{ marginBottom: 0 }}>
        {TABS.map((tab, i) => (
          <button
            key={tab}
            className={`tab-btn ${activeTab === i ? 'tab-active' : ''}`}
            onClick={() => setActiveTab(i)}
          >
            {tab}
          </button>
        ))}
      </div>

      {draft && (
        <div className="card" style={{ borderTopLeftRadius: 0, borderTopRightRadius: 0 }}>
          {/* Plain Language */}
          {activeTab === 0 && (
            <div className="tab-content">
              <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.8, color: 'var(--text-secondary)' }}>
                {draft.plain_language || 'No plain language contract generated.'}
              </div>
            </div>
          )}

          {/* IG Syntax */}
          {activeTab === 1 && (
            <div className="tab-content">
              <div className="code-block" style={{ fontSize: 13, lineHeight: 1.7 }}>
                {draft.ig_syntax || 'No IG syntax generated.'}
              </div>
            </div>
          )}

          {/* JSON */}
          {activeTab === 2 && (
            <div className="tab-content">
              <div className="code-block" style={{ fontSize: 12, lineHeight: 1.6 }}>
                {JSON.stringify(draft.json_contract, null, 2)}
              </div>
            </div>
          )}

          {/* Provenance */}
          {activeTab === 3 && (
            <div className="tab-content">
              {(draft.provenance || []).length === 0 ? (
                <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>No provenance records.</p>
              ) : (
                <div>
                  {draft.provenance.map((p, i) => (
                    <div key={i} className="provenance-row">
                      <div className="provenance-header">
                        <code className="provenance-id">{p.obligation_id}</code>
                        <span className={`badge ${p.confirmed_by_user ? 'badge-sat' : 'badge-warn'}`}>
                          {p.confirmed_by_user ? 'Confirmed' : 'Unconfirmed'}
                        </span>
                      </div>
                      <div className="provenance-source">
                        <span className="provenance-type">{p.source_type.replace(/_/g, ' ')}</span>
                        <span className="provenance-text">{p.source_text}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 20 }}>
        <button className="btn" onClick={() => navigate(`/author/clarify/${id}`)}>← Back to Clarify</button>
        <button className="btn btn-outline" onClick={handleRegenerate} disabled={generating}>
          {generating ? 'Regenerating...' : '↻ Regenerate'}
        </button>
        <button
          className="btn btn-primary"
          onClick={() => navigate(`/author/validate/${id}`)}
          id="proceed-to-validation-btn"
        >
          Proceed to Validation →
        </button>
      </div>
    </div>
  );
}
