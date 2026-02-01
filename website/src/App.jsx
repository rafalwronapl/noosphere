import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import MoltbookObservatory from './MoltbookObservatory';
import LandingPage from './LandingPage';
import DiscoveriesPage from './DiscoveriesPage';
import FeedbackPage from './FeedbackPage';
import IdentityGate from './components/IdentityGate';

function AppContent() {
  const [data, setData] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showIdentityGate, setShowIdentityGate] = useState(false);
  const [userType, setUserType] = useState(null);

  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const savedType = localStorage.getItem('observatory_user_type');
    if (savedType) {
      setUserType(savedType);
    }

    Promise.all([
      fetch('/data/latest.json').then(res => res.ok ? res.json() : Promise.reject('Failed to load data')),
      fetch('/data/graph.json').then(res => res.ok ? res.json() : null).catch(() => null)
    ])
      .then(([mainData, graph]) => {
        setData(mainData);
        setGraphData(graph);
      })
      .catch(err => setError(err.message || err))
      .finally(() => setLoading(false));
  }, []);

  const handleIdentitySelect = (type) => {
    setUserType(type);
    localStorage.setItem('observatory_user_type', type);
    setShowIdentityGate(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🔭</div>
          <div className="text-white text-xl">Loading Noosphere...</div>
          <div className="text-gray-500 text-sm mt-2">Fetching latest agent data</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <div className="text-red-500 text-xl">Error: {error}</div>
          <div className="text-gray-500 text-sm mt-2">
            Make sure to run: python generate_dashboard_data.py
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {showIdentityGate && (
        <IdentityGate
          onSelect={handleIdentitySelect}
          onClose={() => setShowIdentityGate(false)}
        />
      )}
      <Routes>
        <Route path="/" element={
          <LandingPage
            onEnterDashboard={() => navigate('/dashboard')}
            onViewDiscoveries={() => navigate('/discoveries')}
            onViewFeedback={() => navigate('/feedback')}
            onShowIdentityGate={() => setShowIdentityGate(true)}
            userType={userType}
            stats={data?.meta}
          />
        } />
        <Route path="/dashboard" element={
          <div>
            <button
              onClick={() => navigate('/')}
              className="fixed top-4 left-4 z-50 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm flex items-center gap-2"
            >
              ← Back
            </button>
            <MoltbookObservatory data={data} graphData={graphData} />
          </div>
        } />
        <Route path="/discoveries" element={
          <DiscoveriesPage onBack={() => navigate('/')} />
        } />
        <Route path="/feedback" element={
          <FeedbackPage onBack={() => navigate('/')} />
        } />
        <Route path="/submit" element={
          <FeedbackPage onBack={() => navigate('/')} />
        } />
      </Routes>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
