import React from 'react';

export function Badge({ level }) {
  const normalizedLevel = (level || 'unassessed').toLowerCase();
  const label = normalizedLevel.charAt(0).toUpperCase() + normalizedLevel.slice(1);

  return (
    <span className={`badge ${normalizedLevel}`}>
      {label}
    </span>
  );
}

export function ProgressBar({ score, level }) {
  const normalizedLevel = (level || 'unassessed').toLowerCase();
  const clampedScore = Math.max(0, Math.min(100, Math.round(score || 0)));

  return (
    <div className="progress-container">
      <div className="progress-bar-bg">
        <div
          className={`progress-bar-fill ${normalizedLevel}`}
          style={{ width: `${clampedScore}%` }}
        />
      </div>
      <div className="progress-text">{clampedScore}%</div>
    </div>
  );
}
