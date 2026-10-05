import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Badge, ProgressBar } from '../components/Badge';

export function ProgressPage({ onStartAssessment }) {
  const [masteryList, setMasteryList] = useState([]);
  const [concepts, setConcepts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadProgressData();
  }, []);

  const loadProgressData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [masteryRes, conceptsRes] = await Promise.all([
        api.getMastery(),
        api.getConcepts(),
      ]);
      setMasteryList(masteryRes || []);
      setConcepts(conceptsRes || []);
    } catch (err) {
      setError(err.message || 'Failed to load progress data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-box">
        <div className="spinner" />
        <p>Loading learning progress...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert-box alert-error">
        {error}
        <button className="btn btn-secondary" style={{ marginLeft: '1rem' }} onClick={loadProgressData}>
          Retry
        </button>
      </div>
    );
  }

  // Handle first-time empty state
  if (masteryList.length === 0) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">Learning Progress</h1>
          <p className="page-subtitle">Track your concept mastery growth</p>
        </div>

        <div className="empty-state">
          <div className="empty-title">Your learning profile is empty</div>
          <p className="empty-desc">
            Start your first assessment to let StudyLens begin learning which concepts need more attention.
          </p>
          <button className="btn btn-primary" onClick={() => onStartAssessment()}>
            Start Assessment
          </button>
        </div>
      </div>
    );
  }

  const assessedCount = masteryList.length;
  const totalConcepts = concepts.length;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Learning Progress</h1>
        <p className="page-subtitle">
          Summary of {assessedCount} of {totalConcepts} assessed software engineering concepts
        </p>
      </div>

      <div className="card">
        <div className="card-title">Assessed Concepts Breakdown</div>
        <div className="concept-list">
          {masteryList.map((m) => (
            <div key={m.id} className="concept-item">
              <div className="concept-info">
                <div className="concept-name">{m.concept?.name || `Concept #${m.concept_id}`}</div>
                <div className="concept-desc">
                  Attempts: {m.attempts_count} | Correct: {m.correct_count} | Updated: {new Date(m.updated_at).toLocaleDateString()}
                </div>
              </div>
              <Badge level={m.mastery_level} />
              <ProgressBar score={m.mastery_score} level={m.mastery_level} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
