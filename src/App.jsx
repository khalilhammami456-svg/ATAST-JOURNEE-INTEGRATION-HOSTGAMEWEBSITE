import { BrowserRouter, Route, Routes } from 'react-router-dom';
import AdminLayout from './layouts/AdminLayout';
import Home from './pages/Home';
import NotFound from './pages/NotFound';
import Dashboard from './pages/admin/Dashboard';
import Teams from './pages/admin/Teams';
import TeamDetail from './pages/admin/TeamDetail';
import Participants from './pages/admin/Participants';
import Games from './pages/admin/Games';
import LeaderboardPage from './pages/admin/LeaderboardPage';
import ScreenControl from './pages/admin/ScreenControl';
import Settings from './pages/admin/Settings';
import DisplayScreen from './pages/display/DisplayScreen';
import { NotificationProvider } from './components/ui/Notification';
import { ConfirmProvider } from './components/ui/ConfirmDialog';
import { useThemeSync } from './hooks/useThemeSync';

export default function App() {
  useThemeSync();

  return (
    <NotificationProvider>
      <ConfirmProvider>
        <BrowserRouter
          basename={import.meta.env.BASE_URL}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/display" element={<DisplayScreen />} />
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="teams" element={<Teams />} />
              <Route path="teams/:teamId" element={<TeamDetail />} />
              <Route path="participants" element={<Participants />} />
              <Route path="games" element={<Games />} />
              <Route path="leaderboard" element={<LeaderboardPage />} />
              <Route path="screen" element={<ScreenControl />} />
              <Route path="settings" element={<Settings />} />
            </Route>
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </ConfirmProvider>
    </NotificationProvider>
  );
}
