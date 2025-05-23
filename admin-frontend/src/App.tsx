import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { CheckInProvider } from './contexts/CheckInContext';
import { AuthProvider, UserRole } from './contexts/AuthContext';
import { Layout } from './components/Layout';
import { Dashboard } from './components/Dashboard';
import { Members } from './components/Members';
import { CheckInPage } from './components/checkins/CheckInPage';
import NotificationPage from './components/notifications/NotificationPage';
import ReportPage from './components/reports/ReportPage';
import LoginPage from './components/auth/LoginPage';
import UnauthorizedPage from './components/auth/UnauthorizedPage';
import RoleAuthorization from './components/auth/RoleAuthorization';

const queryClient = new QueryClient();

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <Router>
          <AuthProvider>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/unauthorized" element={<UnauthorizedPage />} />
              
              {/* Protected routes */}
              <Route path="/" element={
                <RoleAuthorization allowedRoles={[
                  UserRole.ADMIN,
                  UserRole.MANAGER,
                  UserRole.STAFF,
                  UserRole.TRAINER,
                  UserRole.FRONT_DESK
                ]}>
                  <WebSocketProvider>
                    <CheckInProvider>
                      <Layout>
                        <Dashboard />
                      </Layout>
                    </CheckInProvider>
                  </WebSocketProvider>
                </RoleAuthorization>
              } />
              
              {/* Members - accessible by everyone except front desk */}
              <Route path="/members" element={
                <RoleAuthorization allowedRoles={[
                  UserRole.ADMIN,
                  UserRole.MANAGER,
                  UserRole.STAFF,
                  UserRole.TRAINER
                ]}>
                  <WebSocketProvider>
                    <CheckInProvider>
                      <Layout>
                        <Members />
                      </Layout>
                    </CheckInProvider>
                  </WebSocketProvider>
                </RoleAuthorization>
              } />
              
              {/* Check-in - accessible by admin, manager, staff, and front desk */}
              <Route path="/check-in" element={
                <RoleAuthorization allowedRoles={[
                  UserRole.ADMIN,
                  UserRole.MANAGER,
                  UserRole.STAFF,
                  UserRole.FRONT_DESK
                ]}>
                  <WebSocketProvider>
                    <CheckInProvider>
                      <Layout>
                        <CheckInPage />
                      </Layout>
                    </CheckInProvider>
                  </WebSocketProvider>
                </RoleAuthorization>
              } />
              
              {/* Notifications - accessible by admin and manager only */}
              <Route path="/notifications" element={
                <RoleAuthorization allowedRoles={[
                  UserRole.ADMIN,
                  UserRole.MANAGER
                ]}>
                  <WebSocketProvider>
                    <Layout>
                      <NotificationPage />
                    </Layout>
                  </WebSocketProvider>
                </RoleAuthorization>
              } />
              
              {/* Reports - accessible by admin and manager only */}
              <Route path="/reports" element={
                <RoleAuthorization allowedRoles={[
                  UserRole.ADMIN,
                  UserRole.MANAGER
                ]}>
                  <WebSocketProvider>
                    <Layout>
                      <ReportPage />
                    </Layout>
                  </WebSocketProvider>
                </RoleAuthorization>
              } />
              
              {/* Redirect to dashboard if logged in, otherwise to login */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AuthProvider>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
