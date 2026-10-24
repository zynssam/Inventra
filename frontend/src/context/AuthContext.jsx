// src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { Auth } from "../api";

const SESSION_KEY = "inventraUser";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem(SESSION_KEY)); } catch { return null; }
  });
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (email, password) => {
    const data = await Auth.login(email, password);
    const session = { token: data.access_token, user_id: data.user_id, role: data.role, full_name: data.full_name, email };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    setUser(session);
    return session;
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(SESSION_KEY);
    setUser(null);
  }, []);

  const isAdmin      = user?.role === "admin";
  const canWrite     = user?.role === "admin" || user?.role === "store_manager";
  const isLoggedIn   = !!user?.token;

  return (
    <AuthContext.Provider value={{ user, login, logout, isAdmin, canWrite, isLoggedIn, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
