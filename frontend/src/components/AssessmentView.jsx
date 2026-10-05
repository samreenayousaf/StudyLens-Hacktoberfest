import React, { useState } from 'react';
import { api } from '../services/api';
import { Badge, ProgressBar } from './Badge';

export function AssessmentView({ question, onQuestionChange, onComplete }) {
  const [answerText, setAnswerText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitResult, setSubmitResult] = useState(null);

  const conceptName = question?.concept?.name || question?.concept || 'Software Engineering';

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!answerText.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const result = await api.submitLearningAnswer(question.id, answerText.trim());
      setSubmitResult(result);
    } catch (err) {
      setSubmitError(err.message || 'Failed to analyze answer');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleContinueRetest = () => {
    if (!submitResult?.retest?.question_id) return;
    const nextQ = {
      id: submitResult.retest.question_id,
      question_id: submitResult.retest.question_id,
      question_text: submitResult.retest.question_text,
      concept_id: submitResult.retest.concept_id,
      concept: {
        id: submitResult.retest.concept_id,
        name: submitResult.retest.concept,
      },
    };
    setAnswerText('');
    setSubmitResult(null);
    setSubmitError(null);
    onQuestionChange(nextQ);
  };

  const handleContinueLearning = () => {
    setAnswerText('');
    setSubmitResult(null);
    setSubmitError(null);
    onComplete();
  };

  if (!question) {
    return (
      <div className="loading-box">
        <div className="spinner" />
        <p>Loading assessment question...</p>
      </div>
    );
  }

  return (
    <div className="assessment-container">
      <div className="question-box">
        <div className="question-category">{conceptName}</div>
        <div className="question-text">{question.question_text}</div>
      </div>

      {submitError && (
        <div className="alert-box alert-error">
          {submitError}
        </div>
      )}

      {!submitResult ? (
        <form onSubmit={handleSubmit} className="answer-form">
          <label htmlFor="student-answer-input" className="sr-only">
            Student Answer Explanation
          </label>
          <textarea
            id="student-answer-input"
            className="answer-textarea"
            placeholder="Write your explanation here..."
            value={answerText}
            onChange={(e) => setAnswerText(e.target.value.slice(0, 2000))}
            disabled={isSubmitting}
            required
          />
          <div className="form-footer">
            <span className="char-counter">{answerText.length} / 2000</span>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!answerText.trim() || isSubmitting}
            >
              {isSubmitting ? 'Analyzing your answer locally...' : 'Submit Answer'}
            </button>
          </div>
          {isSubmitting && (
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
              Your answer is processed by the local StudyLens AI (Gemma 3:1B).
            </p>
          )}
        </form>
      ) : (
        <div className="result-section">
          {/* AI Analysis Summary */}
          <div className="card">
            <div className="card-title">AI Answer Analysis</div>
            
            <div className="score-display" style={{ marginBottom: '1.25rem' }}>
              <div className="score-big">
                {Math.round(submitResult.analysis.understanding_score)}
              </div>
              <div className="score-meta">
                <div className="score-title">Understanding Score</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Out of 100 points</div>
              </div>
            </div>

            <div className="info-block" style={{ marginBottom: '1rem' }}>
              <div className="info-title">Why StudyLens gave this assessment</div>
              <p className="evidence-text">{submitResult.analysis.evidence}</p>
            </div>

            {submitResult.analysis.misconceptions?.length > 0 ? (
              <div className="info-block" style={{ marginBottom: '1rem' }}>
                <div className="info-title">Identified Misconceptions</div>
                <div>
                  {submitResult.analysis.misconceptions.map((misc, idx) => (
                    <span key={idx} className="misconception-tag">
                      ⚠️ {misc}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <div className="info-block" style={{ marginBottom: '1rem' }}>
                <div className="info-title">Misconceptions</div>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                  No significant misconceptions detected.
                </p>
              </div>
            )}

            <div className="info-block">
              <div className="info-title">Detected Concepts</div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.25rem' }}>
                {submitResult.analysis.detected_concepts?.map((c, idx) => (
                  <span key={idx} className="badge proficient">{c}</span>
                ))}
              </div>
            </div>
          </div>

          {/* Deterministic Mastery Update */}
          <div className="card">
            <div className="card-title">Updated Mastery Status</div>
            <div className="concept-item">
              <div className="concept-info">
                <div className="concept-name">{conceptName}</div>
                <div className="concept-desc">
                  Attempts: {submitResult.mastery.attempts_count} | Correct: {submitResult.mastery.correct_count}
                </div>
              </div>
              <Badge level={submitResult.mastery.mastery_level} />
              <ProgressBar
                score={submitResult.mastery.mastery_score}
                level={submitResult.mastery.mastery_level}
              />
            </div>
          </div>

          {/* Retest Decision Card */}
          {submitResult.retest?.required ? (
            <div className="card" style={{ borderColor: 'rgba(245, 158, 11, 0.4)', backgroundColor: 'rgba(245, 158, 11, 0.05)' }}>
              <div className="card-title" style={{ color: 'var(--color-developing)' }}>
                Targeted Retest Required
              </div>
              <p style={{ fontSize: '0.95rem', color: 'var(--text-main)', marginBottom: '1rem' }}>
                {submitResult.retest.reason}
              </p>
              <div className="question-box" style={{ marginBottom: '1.25rem' }}>
                <div className="question-category">Next Retest Question — {submitResult.retest.concept}</div>
                <div className="question-text">{submitResult.retest.question_text}</div>
              </div>
              <button
                className="btn btn-primary"
                onClick={handleContinueRetest}
              >
                Continue Retest
              </button>
            </div>
          ) : (
            <div className="card" style={{ borderColor: 'rgba(16, 185, 129, 0.4)', backgroundColor: 'rgba(16, 185, 129, 0.05)' }}>
              <div className="card-title" style={{ color: 'var(--color-strong)' }}>
                Assessment Complete
              </div>
              <p style={{ fontSize: '0.95rem', color: 'var(--text-main)', marginBottom: '1.25rem' }}>
                {submitResult.retest?.reason || 'Your mastery level for this concept does not require an immediate retest.'}
              </p>
              <button
                className="btn btn-primary"
                onClick={handleContinueLearning}
              >
                Continue Learning
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
