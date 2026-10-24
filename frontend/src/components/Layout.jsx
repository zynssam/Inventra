// src/components/Layout.jsx
import Sidebar from "./Sidebar";
import { useLocation } from "react-router-dom";

const TITLES = {
  "/": "Dashboard", "/products": "Products", "/transactions": "Transactions",
  "/forecasts": "Forecasts", "/recommendations": "Reorder Recommendations",
  "/categories": "Categories", "/suppliers": "Suppliers",
  "/reports": "Reports", "/users": "User Management",
  "/audit": "Audit Log", "/settings": "Settings",
};

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const title = TITLES[pathname] ?? "Inventra";

  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-content">
        <header className="topbar">
          <span className="topbar-title">{title}</span>
        </header>
        <main className="page-body">{children}</main>
      </div>
    </div>
  );
}
