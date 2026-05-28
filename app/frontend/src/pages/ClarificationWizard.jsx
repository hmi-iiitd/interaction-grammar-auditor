import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import AuthoringStepper from '../components/AuthoringStepper';
import { getQuestions, submitAnswers } from '../api/client';

export default function ClarificationWizard() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [currentIdx, setCurrentIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getQuestions(id)
      .then(data => {
        setQuestions(data.questions || []);
        if ((data.questions || []).length === 0) {
          navigate(`/author/preview/${id}`);
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const q = questions[currentIdx];

  const setAnswer = (questionId, field, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: { ...prev[questionId], [field]: value },
    }));
  };

  const toggleOption = (questionId, option) => {
    setAnswers(prev => {
      const current = prev[questionId]?.selected_options || [];
      const next = current.includes(option)
        ? current.filter(o => o !== option)
        : [...current, option];
      return {
        ...prev,
        [questionId]: { ...prev[questionId], selected_options: next },
      };
    });
  };

  const selectSingleOption = (questionId, option) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        answer_text: option,
        selected_options: [option],
      },
    }));
  };

  const handleSubmitAll = async () => {
    setSubmitting(true);
    setError(null);

    const formatted = questions.map(q => ({
      question_id: q.question_id,
      answer_text: answers[q.question_id]?.answer_text || '',
      selected_options: answers[q.question_id]?.selected_options || [],
    }));

    try {
      await submitAnswers(id, formatted);
      navigate(`/author/preview/${id}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className="loading"><div className="spinner" /> Loading questions...</div>;
  if (error) return <div className="failure-box">{error}</div>;
  if (questions.length === 0) return null;

  const isDeadlineOrPriority = q?.category === 'deadline_missing' || q?.category === 'interruption_priority_missing';
  const currentAnswer = answers[q?.question_id] || {};
  const progress = ((currentIdx + 1) / questions.length) * 100;

  return (
    <div>
      <AuthoringStepper currentStep={3} />

      <div className="page-header">
        <h1 className="page-title">Clarification Wizard</h1>
        <p className="page-subtitle">
          Answer the following questions to resolve missing or ambiguous details.
        </p>
      </div>

      {/* Progress bar */}
      <div className="auth-progress-bar" style={{ marginBottom: 24 }}>
        <div className="auth-progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginBottom: 20 }}>
        Question {currentIdx + 1} of {questions.length}
      </div>

      {/* Question Card */}
      <div className="card question-card" style={{ maxWidth: 640, margin: '0 auto' }}>
        <div style={{ marginBottom: 8 }}>
          <span className={`badge ${
            q.category === 'deadline_missing' ? 'badge-warn' :
            q.category === 'repair_policy_missing' ? 'badge-unsat' :
            q.category === 'event_modality_missing' ? 'badge-info' :
            q.category === 'failure_condition_missing' ? 'badge-unsat' :
            'badge-info'
          }`}>
            {q.category.replace(/_/g, ' ')}
          </span>
          {q.required && <span className="badge" style={{ marginLeft: 6, background: '#fef2f2', color: '#dc2626' }}>required</span>}
        </div>

        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 20, lineHeight: 1.5 }}>
          {q.question_text}
        </h3>

        {/* Options */}
        {(q.suggested_options || []).length > 0 && (
          <div className="auth-options-grid">
            {q.suggested_options.map(opt => {
              const isSelected = isDeadlineOrPriority
                ? currentAnswer.answer_text === opt
                : (currentAnswer.selected_options || []).includes(opt);
              return (
                <button
                  key={opt}
                  className={`auth-option-btn ${isSelected ? 'selected' : ''}`}
                  onClick={() => isDeadlineOrPriority
                    ? selectSingleOption(q.question_id, opt)
                    : toggleOption(q.question_id, opt)
                  }
                >
                  <span className="auth-option-check">{isSelected ? '●' : '○'}</span>
                  {opt}
                </button>
              );
            })}
          </div>
        )}

        {/* Custom answer */}
        <div style={{ marginTop: 16 }}>
          <label className="auth-label">Custom Answer</label>
          <input
            className="filter-input"
            style={{ width: '100%' }}
            placeholder={isDeadlineOrPriority ? 'e.g. 3.0 seconds' : 'Type a custom answer...'}
            value={currentAnswer.answer_text || ''}
            onChange={e => setAnswer(q.question_id, 'answer_text', e.target.value)}
          />
        </div>
      </div>

      {/* Navigation */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 24 }}>
        <button
          className="btn"
          disabled={currentIdx === 0}
          onClick={() => setCurrentIdx(i => i - 1)}
        >
          ← Previous
        </button>

        {currentIdx < questions.length - 1 ? (
          <button
            className="btn btn-primary"
            onClick={() => setCurrentIdx(i => i + 1)}
          >
            Next →
          </button>
        ) : (
          <button
            className="btn btn-primary"
            onClick={handleSubmitAll}
            disabled={submitting}
            id="submit-answers-btn"
          >
            {submitting ? 'Applying Answers...' : 'Submit All Answers →'}
          </button>
        )}
      </div>
    </div>
  );
}
