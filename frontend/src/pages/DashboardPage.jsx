import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Badge, ProgressBar } from '../components/Badge';
import { StatCard } from '../components/StatCard';

export function DashboardPage({ onStartAssessment }) {
  const [concepts, setConcepts] = useState([]);
  const [masteryList, setMasteryList] = useState([]);
  const [weakList, setWeakList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [conceptsRes, masteryRes, weakRes] = await Promise.all([
        api.getConcepts(),
        api.getMastery(),
        api.getWeakMastery(),
      ]);
      setConcepts(conceptsRes || []);
      setMasteryList(masteryRes || []);
      setWeakList(weakRes || []);
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  // Build a map of concept_id -> mastery record
  const masteryMap = {};
  masteryList.forEach((m) => {
    masteryMap[m.concept_id] = m;
  });

  // Calculate overview counts from REAL mastery data
  let strongCount = 0;
  let proficientCount = 0;
  let developingCount = 0;
  let weakCount = 0;

  masteryList.forEach((m) => {
    const lvl = (m.mastery_level || '').toLowerCase();
    if (lvl === 'strong') strongCount++;
    else if (lvl === 'proficient') proficientCount++;
    else if (lvl === 'developing') developingCount++;
    else if (lvl === 'weak') weakCount++;
  });

  const totalConcepts = concepts.length;

  if (loading) {
    return (
      <div className="loading-box">
        <div className="spinner" />
        <p>Loading StudyLens dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert-box alert-error">
        {error}
        <button className="btn btn-secondary" style={{ marginLeft: '1rem' }} onClick={loadDashboardData}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Learning Dashboard</h1>
        <p className="page-subtitle">
          Adaptive Software Engineering concept mastery powered by local Gemma 3:1B
        </p>
      </div>

      {/* Overview Stat Cards */}
      <div className="stats-grid">
        <StatCard label="Total Concepts" value={totalConcepts} />
        <StatCard label="Strong" value={strongCount} type="strong" />
        <StatCard label="Proficient" value={proficientCount} type="proficient" />
        <StatCard label="Developing" value={developingCount} type="developing" />
        <StatCard label="Weak" value={weakCount} type="weak" />
      </div>

      {/* Weak Concepts Requiring Attention */}
      {weakList.length > 0 && (
        <div className="card" style={{ borderColor: 'rgba(239, 68, 68, 0.4)' }}>
          <div className="card-title" style={{ color: 'var(--color-weak)' }}>
            ⚠️ Concepts Requiring Attention ({weakList.length})
          </div>
          <div className="concept-list">
            {weakList.map((m) => (
              <div key={m.id} className="concept-item">
                <div className="concept-info">
                  <div className="concept-name">{m.concept?.name || `Concept #${m.concept_id}`}</div>
                  <div className="concept-desc">Score: {Math.round(m.mastery_score)} / 100</div>
                </div>
                <Badge level="weak" />
                <button
                  className="btn btn-primary"
                  onClick={() => onStartAssessment(m.concept_id)}
                >
                  Practice
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Concepts Mastery List */}
      <div className="card">
        <div className="card-title">
          <span>Curriculum Concept Mastery</span>
          <button className="btn btn-secondary" onClick={() => onStartAssessment()}>
            Start Assessment
          </button>
        </div>

        <div className="concept-list">
          {concepts.map((concept) => {
            const m = masteryMap[concept.id];
            const level = m ? m.mastery_level : 'unassessed';
            const score = m ? m.mastery_score : 0;

            return (
              <div key={concept.id} className="concept-item">
                <div className="concept-info">
                  <div className="concept-name">{concept.name}</div>
                  <div className="concept-desc">{concept.description}</div>
                </div>
                <Badge level={level} />
                <ProgressBar score={score} level={level} />
                <button
                  className="btn btn-secondary"
                  onClick={() => onStartAssessment(concept.id)}
                >
                  {m ? 'Re-assess' : 'Assess'}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
