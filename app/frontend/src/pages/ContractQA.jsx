import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchScenario, askQuestion } from '../api/client';
import Stepper from '../components/Stepper';

const SUGGESTIONS = [
  'Why did this interaction fail?',
  'When did the failure become decidable?',
  'Which event triggered the obligation?',
  'What was expected but missing?',
];

export default function ContractQA() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEnd = useRef(null);

  useEffect(() => { fetchScenario(id).then(setData).catch(console.error); }, [id]);
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const sendMessage = async (text) => {
    const q = text || input;
    if (!q.trim()) return;
    setMessages(prev => [...prev, { role: 'user', text: q }]);
    setInput('');
    setLoading(true);
    try {
      const res = await askQuestion(id, q);
      setMessages(prev => [...prev, { role: 'assistant', text: res.answer, source: res.source }]);
    } catch { setMessages(prev => [...prev, { role: 'assistant', text: 'Error connecting.' }]); }
    setLoading(false);
  };

  if (!data) return <div className="loading"><div className="spinner" /> Loading...</div>;
  const { contract, audit_report: audit } = data;

  return (
    <div>
      <Stepper currentStep={3} />
      <div className="page-header" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn" onClick={() => navigate(`/scenario/${id}`)} style={{ padding: '4px 10px' }}>&larr;</button>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Scenario: <strong>{id}</strong></div>
            <h1 className="page-title">Contract & Q&A</h1>
          </div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="card">
          <div className="card-header">
            <div className="card-title">Contract</div>
            <span className="badge badge-info">{audit.contract_id}</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>Plain-language interaction contract</p>
          {contract.items && contract.items.map((item, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <span style={{ fontWeight: 700, color: 'var(--accent)', minWidth: 20 }}>{i + 1}.</span>
              <div className="code-block" style={{ flex: 1, fontSize: 11 }}>{JSON.stringify(item, null, 2)}</div>
            </div>
          ))}
          {contract.node && (
            <div style={{ marginTop: 16 }}>
              <div className="card-title" style={{ fontSize: 13, marginBottom: 8 }}>Readable contract syntax</div>
              <div className="code-block">Contract type: {contract.node}</div>
            </div>
          )}
        </div>
        <div className="card" style={{ padding: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="card-title">Ask about this audit</div>
            <div className="grounding-badge"><div className="grounding-dot" /> Grounded in loaded audit package</div>
          </div>
          {messages.length === 0 && (
            <div className="chat-suggestions">
              {SUGGESTIONS.map(text => (
                <button key={text} className="chat-suggestion" onClick={() => sendMessage(text)}>{text}</button>
              ))}
            </div>
          )}
          <div className="chat-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`chat-message ${msg.role}`}>
                <div className="chat-avatar">{msg.role === 'user' ? 'U' : 'A'}</div>
                <div>
                  <div className="chat-bubble">{msg.text}</div>
                  {msg.source && <div className="chat-time">Source: {msg.source}</div>}
                </div>
              </div>
            ))}
            {loading && <div className="chat-message assistant"><div className="chat-avatar">A</div><div className="chat-bubble"><div className="spinner" style={{ width: 14, height: 14, margin: 0 }} /></div></div>}
            <div ref={chatEnd} />
          </div>
          <div className="chat-input-area">
            <input className="chat-input" placeholder="Ask a question..." value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendMessage()} />
            <button className="btn btn-primary" onClick={() => sendMessage()}>Send</button>
          </div>
        </div>
      </div>
    </div>
  );
}
