// src/components/Sidebar.jsx
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  LayoutDashboard, Package, ArrowLeftRight, TrendingUp,
  ShoppingCart, Tag, Truck, FileText, Users, Settings,
  LogOut, ShieldCheck,
} from "lucide-react";

const NAV = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/products", icon: Package, label: "Products" },
  { to: "/transactions", icon: ArrowLeftRight, label: "Transactions" },
  { to: "/forecasts", icon: TrendingUp, label: "Forecasts" },
  { to: "/recommendations", icon: ShoppingCart, label: "Reorder" },
];
const MANAGE = [
  { to: "/categories", icon: Tag, label: "Categories" },
  { to: "/suppliers", icon: Truck, label: "Suppliers" },
  { to: "/reports", icon: FileText, label: "Reports" },
];
const ADMIN_NAV = [
  { to: "/users", icon: Users, label: "Users" },
  { to: "/audit", icon: ShieldCheck, label: "Audit Log" },
];

function NavItem({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
    >
      <Icon size={16} />
      {label}
    </NavLink>
  );
}

export default function Sidebar() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const initials = (user?.full_name ?? "U").split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5z"/>
            <path d="m4 7.5 8 4.5 8-4.5M12 12v9M8 5.3l8 4.5"/>
          </svg>
        </div>
        Inventra
      </div>

      <nav className="sidebar-nav">
        {NAV.map(n => <NavItem key={n.to} {...n} />)}
        <div className="nav-section-label">Manage</div>
        {MANAGE.map(n => <NavItem key={n.to} {...n} />)}
        <NavItem to="/settings" icon={Settings} label="Settings" />
        {isAdmin && <>
          <div className="nav-section-label">Admin</div>
          {ADMIN_NAV.map(n => <NavItem key={n.to} {...n} />)}
        </>}
      </nav>

      <div className="sidebar-footer">
        <div className="user-card">
          <div className="avatar">{initials}</div>
          <div className="user-info">
            <div className="user-name">{user?.full_name ?? "User"}</div>
            <div className="user-role">{user?.role?.replace("_", " ") ?? ""}</div>
          </div>
          <button className="btn btn-ghost btn-icon" title="Log out" onClick={logout}>
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}
