import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';

const UploadPage = lazy(() => import('./pages/UploadPage'));
const ReviewPage = lazy(() => import('./pages/ReviewPage'));

const PageLoader = () => (
  <div className="route-loader" role="status" aria-live="polite">
    Loading workspace…
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/review/:documentId/:sectionId?" element={<ReviewPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
