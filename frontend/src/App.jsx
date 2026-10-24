// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import Chatbot from "./components/Chatbot";

import Login           from "./pages/Login";
import Dashboard       from "./pages/Dashboard";
import Products        from "./pages/Products";
import Transactions    from "./pages/Transactions";
import Forecasts       from "./pages/Forecasts";
import Recommendations from "./pages/Recommendations";
import Categories      from "./pages/Categories";
import Suppliers       from "./pages/Suppliers";
import Reports         from "./pages/Reports";
import Settings        from "./pages/Settings";
import Users           from "./pages/Users";
import Audit           from "./pages/Audit";

function RequireAuth({ children }) {
  const { isLoggedIn } = useAuth();
  return isLoggedIn ? children : <Navigate to="/login" replace />;
}

function RequireAdmin({ children }) {
  const { isAdmin } = useAuth();
  return isAdmin ? children : <Navigate to="/" replace />;
}

function AppRoutes() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<RequireAuth><Layout><Dashboard /></Layout></RequireAuth>} />
        <Route path="/products" element={<RequireAuth><Layout><Products /></Layout></RequireAuth>} />
        <Route path="/transactions" element={<RequireAuth><Layout><Transactions /></Layout></RequireAuth>} />
        <Route path="/forecasts" element={<RequireAuth><Layout><Forecasts /></Layout></RequireAuth>} />
        <Route path="/recommendations" element={<RequireAuth><Layout><Recommendations /></Layout></RequireAuth>} />
        <Route path="/categories" element={<RequireAuth><Layout><Categories /></Layout></RequireAuth>} />
        <Route path="/suppliers" element={<RequireAuth><Layout><Suppliers /></Layout></RequireAuth>} />
        <Route path="/reports" element={<RequireAuth><Layout><Reports /></Layout></RequireAuth>} />
        <Route path="/settings" element={<RequireAuth><Layout><Settings /></Layout></RequireAuth>} />
        <Route path="/users" element={<RequireAdmin><Layout><Users /></Layout></RequireAdmin>} />
        <Route path="/audit" element={<RequireAdmin><Layout><Audit /></Layout></RequireAdmin>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Chatbot />
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
