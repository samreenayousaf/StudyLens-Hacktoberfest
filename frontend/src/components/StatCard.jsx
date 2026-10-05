import React from 'react';

export function StatCard({ label, value, type = 'default' }) {
  return (
    <div className={`stat-card ${type}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}
