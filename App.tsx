import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppProvider, useApp } from "@/context/AppContext";
import { Navbar } from "@/components/Navbar";
import LoginPage from "@/pages/LoginPage";
import TimetablePage from "@/pages/TimetablePage";
import NotificationsPage from "@/pages/NotificationsPage";
import ReviewsPage from "@/pages/ReviewsPage";
import DashboardPage from "@/pages/DashboardPage";
import SettingsPage from "@/pages/SettingsPage";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient();

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user } = useApp();
  if (!user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  const { user } = useApp();

  return (
    <>
      {user && <Navbar />}
      <main>
        <Routes>
          <Route path="/" element={user ? <Navigate to="/timetable" replace /> : <LoginPage />} />
          <Route path="/timetable" element={<AuthGuard><TimetablePage /></AuthGuard>} />
          <Route path="/notifications" element={<AuthGuard><NotificationsPage /></AuthGuard>} />
          <Route path="/reviews" element={<AuthGuard><ReviewsPage /></AuthGuard>} />
          <Route path="/dashboard" element={<AuthGuard><DashboardPage /></AuthGuard>} />
          <Route path="/settings" element={<AuthGuard><SettingsPage /></AuthGuard>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <AppProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AppProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
