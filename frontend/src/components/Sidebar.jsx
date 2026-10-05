import React from 'react';

export function Sidebar({ activePage, setActivePage }) {
  return (
    <aside className="sidebar">
      <div className="brand-header">
        <div className="brand-logo">S</div>
        <div className="brand-title">StudyLens</div>
      </div>

      <nav className="nav-menu">
        <button
          className={`nav-item ${activePage === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActivePage('dashboard')}
        >
          <span>📊</span> Dashboard
        </button>
        <button
          className={`nav-item ${activePage === 'assessment' ? 'active' : ''}`}
          onClick={() => setActivePage('assessment')}
        >
          <span>✏️</span> Assessment
        </button>
        <button
          className={`nav-item ${activePage === 'progress' ? 'active' : ''}`}
          onClick={() => setActivePage('progress')}
        >
          <span>📈</span> Progress
        </button>
      </nav>

      <div className="sidebar-footer">
        <div className="status-indicator">
          <span className="status-dot"></span>
          <span>Local AI Online</span>
        </div>
      </div>
    </aside>
  );
}
