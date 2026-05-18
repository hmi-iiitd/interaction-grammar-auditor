import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchMarkdownReport, fetchJsonReport } from '../api/client';
import Stepper from '../components/Stepper';

export default function Reports() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [markdown, setMarkdown] = useState('');
  const [jsonReport, setJsonReport] = useState(null);
  const [tab, setTab] = useState('markdown');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchMarkdownReport(id).then(setMarkdown).catch(() => setMarkdown('Failed to load report.')),
      fetchJsonReport(id).then(setJsonReport).catch(() => setJsonReport(null)),
    ]).finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading"><div className="spinner" /> Generating report...</div>;

  return (
    <div>
      <Stepper currentStep={3} />
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <button className="btn" onClick={() => navigate(`/scenario/${id}`)}>← Back</button>
          <div>
            <h1 className="page-title">Report — {id}</h1>
            <p className="page-subtitle">Generated audit summary report</p>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-sm)', marginBottom: 'var(--space-lg)' }}>
        <button
          className={`btn ${tab === 'markdown' ? 'btn-primary' : ''}`}
          onClick={() => setTab('markdown')}
        >
          📄 Markdown
        </button>
        <button
          className={`btn ${tab === 'json' ? 'btn-primary' : ''}`}
          onClick={() => setTab('json')}
        >
          📋 JSON
        </button>
        <button className="btn" onClick={() => {
          const blob = new Blob([tab === 'markdown' ? markdown : JSON.stringify(jsonReport, null, 2)], { type: 'text/plain' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${id}_report.${tab === 'markdown' ? 'md' : 'json'}`;
          a.click();
          URL.revokeObjectURL(url);
        }}>
          ⬇ Download
        </button>
      </div>

      <div className="card">
        {tab === 'markdown' ? (
          <pre className="code-block" style={{ whiteSpace: 'pre-wrap', maxHeight: 700, overflow: 'auto' }}>
            {markdown}
          </pre>
        ) : (
          <pre className="code-block" style={{ whiteSpace: 'pre-wrap', maxHeight: 700, overflow: 'auto' }}>
            {jsonReport ? JSON.stringify(jsonReport, null, 2) : 'No JSON report available.'}
          </pre>
        )}
      </div>
    </div>
  );
}
