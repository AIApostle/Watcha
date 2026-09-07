import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Bell,
  Newspaper,
  Bot,
  Settings,
  LogOut,
  Eye,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/alerts", icon: Bell, label: "Alerts" },
  { to: "/news", icon: Newspaper, label: "News" },
  { to: "/agent", icon: Bot, label: "Agent" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Layout() {
  const { user, logout } = useAuth();

  const initials = user?.email
    ? user.email.substring(0, 2).toUpperCase()
    : "??";

  return (
    <div className="app-layout">
      {/* Mobile Top Header (hidden on desktop) */}
      <header className="mobile-header">
        <div className="mobile-header-logo">
          <div className="logo-icon">
            <Eye size={18} color="white" />
          </div>
          <span className="mobile-brand-name">Watcha</span>
        </div>
        <div className="mobile-user-action">
          <div className="user-avatar">{initials}</div>
          <button
            onClick={logout}
            className="mobile-logout-btn"
            title="Sign out"
            aria-label="Logout"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {/* Desktop Sidebar (hidden on mobile) */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">
            <Eye size={20} color="white" />
          </div>
          <h1>Watcha</h1>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              <Icon size={20} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-badge" onClick={logout} title="Logout">
            <div className="user-avatar">{initials}</div>
            <div className="user-info">
              <div className="email">{user?.email}</div>
            </div>
            <LogOut size={16} color="var(--text-muted)" />
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <Outlet />
      </main>

      {/* Mobile Bottom Navigation Bar (hidden on desktop) */}
      <nav className="mobile-bottom-nav">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `mobile-nav-item ${isActive ? "active" : ""}`
            }
          >
            <Icon size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
