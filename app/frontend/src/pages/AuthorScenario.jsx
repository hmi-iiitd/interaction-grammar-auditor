import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AuthoringStepper from '../components/AuthoringStepper';
import { saveDescription, clarifyScenario } from '../api/client';

export default function AuthorScenario() {
  const [description, setDescription] = useState('');
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
