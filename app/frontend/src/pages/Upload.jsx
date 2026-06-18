import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Stepper from '../components/Stepper';

const PRD_SCENARIOS = [
  { id: '', label: 'Not a PRD scenario' },
  { id: 'A1_delivery_success', label: 'A1 delivery success' },
  { id: 'A2_recipient_does_not_acknowledge', label: 'A2 missing acknowledgment' },
  { id: 'A3_recipient_acknowledges_too_late', label: 'A3 late acknowledgment' },
  { id: 'A4_robot_does_not_confirm_delivery', label: 'A4 missing robot confirmation' },
  { id: 'B1_human_interrupts_robot_stops', label: 'B1 interruption handled' },
  { id: 'B2_human_interrupts_robot_continues', label: 'B2 robot continues speaking' },
  { id: 'B3_robot_interrupts_human', label: 'B3 robot interrupts human' },
  { id: 'B4_robot_stops_but_no_sorry', label: 'B4 missing interruption acknowledgment' },
  { id: 'C1_retry_success', label: 'C1 retry success' },
  { id: 'C2_repair_exhausted', label: 'C2 repair exhausted' },
  { id: 'C3_retry_limit_exceeded', label: 'C3 retry limit exceeded' },
  { id: 'C4_global_timeout', label: 'C4 global timeout' },
];

export default function Upload() {
  const [scenarioId, setScenarioId] = useState('');
  const [contractFile, setContractFile] = useState(null);
  const [contractText, setContractText] = useState('');
  const [traceFile, setTraceFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationSuccess, setValidationSuccess] = useState(null);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!scenarioId || (!contractFile && !contractText) || !traceFile) {
      setError('Please fill out all fields and provide a contract and trace file.');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('scenario_id', scenarioId);
    if (contractFile) {
      formData.append('contract_file', contractFile);
    } else {
      formData.append('contract_text', contractText);
    }
    formData.append('trace_file', traceFile);

    try {
      const response = await fetch('http://localhost:8000/api/scenarios/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      navigate(`/scenario/${data.scenario_id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!contractFile && !contractText) {
      setError('Please provide a contract file or paste JSON to validate first.');
      return;
    }
    setValidating(true);
    setError(null);
    setValidationSuccess(null);

    const formData = new FormData();
    if (contractFile) {
      formData.append('contract_file', contractFile);
    } else {
      formData.append('contract_text', contractText);
    }

    try {
      const response = await fetch('http://localhost:8000/api/scenarios/validate-contract', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Validation failed');
      }

      setValidationSuccess('Contract is valid!');
    } catch (err) {
      setError(err.message);
    } finally {
      setValidating(false);
    }
  };

  return (
    <div>
      <Stepper currentStep={1} />

      <div className="card" style={{ maxWidth: 600, margin: '0 auto' }}>
        <div className="card-header">
          <div className="card-title">Upload New Scenario</div>
        </div>

        {error && (
          <div className="failure-box" style={{ marginBottom: 20 }}>
            {error}
          </div>
        )}
        {validationSuccess && (
          <div style={{ padding: '12px', background: '#ecfdf5', color: '#16a34a', border: '1px solid #a7f3d0', borderRadius: '4px', marginBottom: 20, fontSize: 13 }}>
            ✓ {validationSuccess}
          </div>
        )}

        <form onSubmit={handleUpload}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>PRD Scenario ID</label>
            <select
              className="filter-select"
              style={{ width: '100%' }}
              value={scenarioId}
              onChange={e => setScenarioId(e.target.value)}
            >
              {PRD_SCENARIOS.map(scenario => (
                <option key={scenario.id || 'none'} value={scenario.id}>
                  {scenario.label}
                </option>
              ))}
            </select>
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Contract File (.ig.json) OR Paste JSON</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <textarea
                className="filter-input"
                style={{ width: '100%', height: '120px', fontFamily: 'monospace', fontSize: 12 }}
                placeholder='{ "node": "bind", "left": ... }'
                value={contractText}
                onChange={e => { setContractText(e.target.value); setContractFile(null); setValidationSuccess(null); setError(null); }}
              />
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>OR select file:</span>
                <input
                  type="file"
                  accept=".json"
                  onChange={e => { setContractFile(e.target.files[0]); setContractText(''); setValidationSuccess(null); setError(null); }}
                  style={{ fontSize: 13, flex: 1 }}
                />
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={handleValidate}
                  disabled={(!contractFile && !contractText.trim()) || validating}
                >
                  {validating ? 'Validating...' : 'Validate'}
                </button>
              </div>
            </div>
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Trace File (.jsonl, .bag, .db3)</label>
            <input
              type="file"
              accept=".jsonl,.bag,.db3"
              onChange={e => setTraceFile(e.target.files[0])}
              style={{ fontSize: 13 }}
            />
            <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              ROS 2 .db3 and ROS 1 .bag files will be automatically extracted (optimized for Scenario 3 / NAO topics).
            </p>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', padding: '12px' }}
            disabled={loading}
          >
            {loading ? <><div className="spinner" style={{ width: 14, height: 14, marginRight: 8, margin: 0, borderTopColor: '#fff', borderColor: 'rgba(255,255,255,0.3)' }} /> Processing & Auditing...</> : 'Upload & Audit'}
          </button>
        </form>
      </div>
    </div>
  );
}
