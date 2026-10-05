const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || `Request failed with status ${response.status}`;
      throw new Error(message);
    }
    return await response.json();
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Could not connect to StudyLens backend. Make sure FastAPI server is running on http://127.0.0.1:8000.');
    }
    throw error;
  }
}

export const api = {
  checkHealth: () => request('/api/health'),
  getConcepts: () => request('/api/concepts'),
  getQuestions: (conceptId) => request(`/api/questions${conceptId ? `?concept_id=${conceptId}` : ''}`),
  getInitialQuestion: () => request('/api/questions/initial'),
  getMastery: () => request('/api/mastery'),
  getWeakMastery: () => request('/api/mastery/weak'),
  getNextRetest: () => request('/api/retest/next'),
  submitLearningAnswer: (questionId, answerText) =>
    request('/api/learning/submit-answer', {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, answer_text: answerText }),
    }),
};
