import { NavLink } from 'react-router-dom';

export default function Sidebar() {
  const links = [
    { to: '/upload', label: '+ New Audit' },
    { to: '/', label: 'Dataset' },
    { to: '/settings', label: 'Settings' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">IG</div>
          <div>
            <div className="sidebar-logo-text">Interaction Contract Auditor</div>
            <div className="sidebar-logo-sub">Temporal Compliance for HRI</div>
          </div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {links.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer" />
    </aside>
  );
}
