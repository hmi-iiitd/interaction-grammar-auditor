import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AuthoringStepper from '../components/AuthoringStepper';
import { saveDescription, clarifyScenario } from '../api/client';

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

export default function AuthorScenario() {
  const [description, setDescription] = useState('');
  const [scenarioId, setScenarioId] = useState('');
  const [title, setTitle] = useState('');
  const [robotPlatform, setRobotPlatform] = useState('NAO');
  const [interactionFamily, setInteractionFamily] = useState('turn-taking');
  const [participantRole, setParticipantRole] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleExtract = async (e) => {
    e.preventDefault();
    if (!description.trim()) {
      setError('Please describe the intended HRI scenario.');
      return;
    }
    if (description.trim().length < 20) {
      setError('Please provide more detail about the intended interaction (at least 20 characters).');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Step 1: Save description
      const { description_id } = await saveDescription({
        description,
        scenario_id: scenarioId,
        scenario_title: title,
        robot_platform: robotPlatform,
        interaction_family: interactionFamily,
        participant_role: participantRole,
        notes,
      });

      // Step 2: Run LLM clarification immediately
      await clarifyScenario(description_id);

      // Navigate to understanding screen
      navigate(`/author/understand/${description_id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const exampleScenario = `The robot greets the participant and asks them to confirm the task. The participant can confirm by saying yes or by nodding. If the participant does not respond, the robot should ask again, but only twice. If the participant interrupts while the robot is speaking, the robot should stop and acknowledge the interruption before continuing.`;

  return (
    <div>
      <AuthoringStepper currentStep={1} />

      <div className="page-header">
        <h1 className="page-title">Author New Contract</h1>
        <p className="page-subtitle">
          Describe your intended HRI scenario in natural language.
          The system will help you convert it into a validated Interaction Grammar contract.
        </p>
      </div>

      <div className="card" style={{ maxWidth: 720, margin: '0 auto' }}>
        <div className="card-header">
          <div className="card-title">Describe the Intended HRI Scenario</div>
        </div>

        {error && (
          <div className="failure-box" style={{ marginBottom: 20 }}>{error}</div>
        )}

        <form onSubmit={handleExtract}>
          <div style={{ marginBottom: 20 }}>
            <label className="auth-label">Scenario Description *</label>
            <textarea
              id="scenario-description"
              className="auth-textarea"
              placeholder="Describe the interaction the robot should follow. Include triggers, expected responses, timing constraints, retry behavior, and interruption handling..."
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={8}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
              <span className="auth-hint">
                {description.length} characters
              </span>
              <button
                type="button"
                className="auth-example-btn"
                onClick={() => setDescription(exampleScenario)}
              >
                Load example scenario
              </button>
            </div>
          </div>

          <div className="auth-optional-grid">
            <div>
              <label className="auth-label">PRD Scenario ID</label>
              <select
                id="scenario-id"
                className="filter-select"
                style={{ width: '100%' }}
                value={scenarioId}
                onChange={e => {
                  const nextId = e.target.value;
                  setScenarioId(nextId);
                  if (nextId && !title.trim()) setTitle(nextId);
                }}
              >
                {PRD_SCENARIOS.map(scenario => (
                  <option key={scenario.id || 'none'} value={scenario.id}>
                    {scenario.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="auth-label">Scenario Title</label>
              <input
                id="scenario-title"
                className="filter-input"
                style={{ width: '100%' }}
                placeholder="e.g. Task Confirmation with Interruption"
                value={title}
                onChange={e => setTitle(e.target.value)}
              />
            </div>
            <div>
              <label className="auth-label">Robot Platform</label>
              <select
                id="robot-platform"
                className="filter-select"
                style={{ width: '100%' }}
                value={robotPlatform}
                onChange={e => setRobotPlatform(e.target.value)}
              >
                <option value="NAO">NAO</option>
                <option value="Pepper">Pepper</option>
                <option value="TIAGo">TIAGo</option>
                <option value="Fetch">Fetch</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div>
              <label className="auth-label">Interaction Family</label>
              <select
                id="interaction-family"
                className="filter-select"
                style={{ width: '100%' }}
                value={interactionFamily}
                onChange={e => setInteractionFamily(e.target.value)}
              >
                <option value="turn-taking">Turn-taking</option>
                <option value="acknowledgment">Acknowledgment</option>
                <option value="instruction-following">Instruction Following</option>
                <option value="collaborative">Collaborative Task</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="auth-label">Participant Role</label>
              <input
                id="participant-role"
                className="filter-input"
                style={{ width: '100%' }}
                placeholder="e.g. patient, student, visitor"
                value={participantRole}
                onChange={e => setParticipantRole(e.target.value)}
              />
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <label className="auth-label">Notes</label>
            <textarea
              id="scenario-notes"
              className="auth-textarea"
              placeholder="Additional context or constraints..."
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={3}
              style={{ minHeight: 'auto' }}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center', padding: '14px', marginTop: 24, fontSize: 14 }}
            disabled={loading}
            id="extract-obligations-btn"
          >
            {loading ? (
              <>
                <div className="spinner" style={{ width: 14, height: 14, borderTopColor: '#fff', borderColor: 'rgba(255,255,255,0.3)' }} />
                Analyzing Scenario...
              </>
            ) : (
              '✦ Extract Candidate Obligations'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
