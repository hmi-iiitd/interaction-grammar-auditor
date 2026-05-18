import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchScenarios } from '../api/client';

export default function Dataset() {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    fetchScenarios().then(setData).catch(console.error);
  }, []);

  if (!data) return <div className="loading"><div className="spinner" /> Loading scenarios...</div>;

  const { scenarios, stats } = data;

  const filtered = scenarios.filter(s => {
    if (filter === 'sat' && s.verdict !== 'SAT') return false;
    if (filter === 'unsat' && s.verdict !== 'UNSAT') return false;
    if (search && !s.scenario_id.toLowerCase().includes(search.toLowerCase())
        && !s.description.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Interaction Audit Dataset</h1>
      </div>

      <div className="filter-bar">
        <input
          className="filter-input"
          placeholder="Search scenarios, interactions, violations..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select className="filter-select" value={filter} onChange={e => setFilter(e.target.value)}>
          <option value="all">All verdicts</option>
          <option value="sat">SAT only</option>
          <option value="unsat">UNSAT only</option>
        </select>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 20 }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Interaction</th>
              <th>Verdict</th>
              <th>Violation</th>
              <th>Report</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(s => (
              <tr key={s.scenario_id} onClick={() => navigate(`/scenario/${s.scenario_id}`)}>
                <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{s.scenario_id}</td>
                <td>{s.description}</td>
                <td>
                  <span className={`badge ${s.verdict === 'SAT' ? 'badge-sat' : 'badge-unsat'}`}>
                    {s.verdict}
                  </span>
                </td>
                <td>{s.violation_types.join(', ') || '\u2014'}</td>
                <td>
                  <button
                    className="btn"
                    style={{ padding: '4px 10px', fontSize: 12 }}
                    onClick={e => { e.stopPropagation(); navigate(`/report/${s.scenario_id}`); }}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="stats-bar">
        <div className="stat-card">
          <div className="stat-icon blue">T</div>
          <div>
            <div className="stat-label">Total scenarios</div>
            <div className="stat-value total">{stats.total}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green">S</div>
          <div>
            <div className="stat-label">SAT</div>
            <div className="stat-value sat">{stats.sat}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon red">U</div>
          <div>
            <div className="stat-label">UNSAT</div>
            <div className="stat-value unsat">{stats.unsat}</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon amber">!</div>
          <div>
            <div className="stat-label">Most common violation</div>
            <div className="stat-value" style={{ fontSize: 16 }}>{stats.most_common_violation}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
