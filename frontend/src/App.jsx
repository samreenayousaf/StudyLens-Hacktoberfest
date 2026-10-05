import React, { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { DashboardPage } from './pages/DashboardPage';
import { AssessmentPage } from './pages/AssessmentPage';
import { ProgressPage } from './pages/ProgressPage';

export function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [selectedConceptId, setSelectedConceptId] = useState(null);

  const handleStartAssessment = (conceptId = null) => {
    setSelectedConceptId(conceptId);
    setActivePage('assessment');
  };

  const handleReturnToDashboard = () => {
    setSelectedConceptId(null);
    setActivePage('dashboard');
  };

  return (
    <div className="app-container">
      <Sidebar
        activePage={activePage}
        setActivePage={(page) => {
          setSelectedConceptId(null);
          setActivePage(page);
        }}
      />
      <main className="main-content">
        {activePage === 'dashboard' && (
          <DashboardPage onStartAssessment={handleStartAssessment} />
        )}
        {activePage === 'assessment' && (
          <AssessmentPage
            selectedConceptId={selectedConceptId}
            onReturnToDashboard={handleReturnToDashboard}
          />
        )}
        {activePage === 'progress' && (
          <ProgressPage onStartAssessment={handleStartAssessment} />
        )}
      </main>
    </div>
  );
}

export default App;
