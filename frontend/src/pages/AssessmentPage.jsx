import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { AssessmentView } from '../components/AssessmentView';

export function AssessmentPage({ selectedConceptId, onReturnToDashboard }) {
  const [question, setQuestion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadQuestion();
  }, [selectedConceptId]);

  const loadQuestion = async () => {
    setLoading(true);
    setError(null);
    try {
      if (selectedConceptId) {
        const questionsList = await api.getQuestions(selectedConceptId);
        if (questionsList && questionsList.length > 0) {
          setQuestion(questionsList[0]);
        } else {
          // Fallback to initial question if no questions for that concept
          const initialQ = await api.getInitialQuestion();
          setQuestion(initialQ);
        }
      } else {
        const initialQ = await api.getInitialQuestion();
        setQuestion(initialQ);
      }
    } catch (err) {
      setError(err.message || 'Failed to load assessment question');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-box">
        <div className="spinner" />
        <p>Loading assessment question...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert-box alert-error">
        {error}
        <button className="btn btn-secondary" style={{ marginLeft: '1rem' }} onClick={loadQuestion}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Adaptive Assessment</h1>
        <p className="page-subtitle">
          Write your technical answer below for local AI analysis
        </p>
      </div>

      <AssessmentView
        question={question}
        onQuestionChange={(newQ) => setQuestion(newQ)}
        onComplete={onReturnToDashboard}
      />
    </div>
  );
}
