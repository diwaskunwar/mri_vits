import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { Provider, useDispatch } from 'react-redux';
import { store } from './store';
import type { AppDispatch } from './store';
import { setCredentials, clearCredentials, setLoading } from './store/slices/authSlice';
import { authService } from './services/api';
import { useAuth } from './hooks/useAuth';

// Pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import Invite from './pages/auth/Invite';
import Dashboard from './pages/dashboard/Dashboard';
import Patients from './pages/patients/Patients';
import PatientDetail from './pages/patients/PatientDetail';
import NewPatient from './pages/patients/NewPatient';
import PredictionsList from './pages/predictions/PredictionsList';
import PredictionDetail from './pages/predictions/PredictionDetail';
import NewScan from './pages/scans/NewScan';
import NewInvitation from './pages/invitations/NewInvitation';
import Layout from './components/Layout';

// ============================================
// Protected Route
// ============================================

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div
          className="rounded-full border-2 border-gray-200 border-t-gray-900 animate-spin"
          style={{ width: 28, height: 28 }}
        />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

// ============================================
// App Content — token validation on mount
// ============================================

function AppContent() {
  const dispatch = useDispatch<AppDispatch>();

  useEffect(() => {
    const validateToken = async () => {
      const token = localStorage.getItem('access_token');
      if (!token) {
        dispatch(setLoading(false));
        return;
      }
      try {
        const response = await authService.validateToken();
        if (response.valid) {
          dispatch(setCredentials({ user: response.user, token }));
        } else {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          dispatch(clearCredentials());
        }
      } catch {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        dispatch(clearCredentials());
      }
    };
    validateToken();
  }, [dispatch]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/invite/:token" element={<Invite />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/patients" element={<Patients />} />
                  <Route path="/patients/new" element={<NewPatient />} />
                  <Route path="/patients/:id" element={<PatientDetail />} />
                  <Route path="/predictions" element={<PredictionsList />} />
                  <Route path="/predictions/:id" element={<PredictionDetail />} />
                  <Route path="/scans/new" element={<NewScan />} />
                  <Route path="/invitations/new" element={<NewInvitation />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

// ============================================
// App — Redux Provider wrapper
// ============================================

function App() {
  return (
    <Provider store={store}>
      <AppContent />
    </Provider>
  );
}

export default App;
