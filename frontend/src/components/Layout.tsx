import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Bell,
  Newspaper,
  Bot,
  Settings,
  LogOut,
  Eye,
  Menu,
  X,
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const initials = user?.email
    ? user.email.substring(0, 2).toUpperCase()
    : "??";

  return (
    <div className="app-layout">
      {/* Mobile Top Header (hidden on desktop) */}
      <header className="mobile-header">
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button
            type="button"
            className="mobile-hamburger-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="mobile-header-logo">
            <div className="logo-icon">
              <Eye size={18} color="white" />
            </div>
            <span className="mobile-brand-name">Watcha</span>
          </div>
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

      {/* Slide-out Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div
          className="mobile-drawer-overlay"
          onClick={() => setMobileMenuOpen(false)}
        >
          <aside
            className="mobile-drawer"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mobile-drawer-header">
              <div className="mobile-header-logo">
                <div className="logo-icon">
                  <Eye size={20} color="white" />
                </div>
                <span className="mobile-brand-name">Watcha</span>
              </div>
              <button
                type="button"
                className="mobile-drawer-close"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close navigation"
              >
                <X size={20} />
              </button>
            </div>

            <nav className="mobile-drawer-nav">
              {navItems.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `nav-link ${isActive ? "active" : ""}`
                  }
                >
                  <Icon size={20} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </nav>

            <div className="mobile-drawer-footer">
              <div
                className="user-badge"
                onClick={() => {
                  setMobileMenuOpen(false);
                  logout();
                }}
                title="Sign out"
              >
                <div className="user-avatar">{initials}</div>
                <div className="user-info">
                  <div className="email">{user?.email}</div>
                </div>
                <LogOut size={16} color="var(--text-muted)" />
              </div>
            </div>
          </aside>
        </div>
      )}

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

      {/* Mobile Bottom Navigation Bar (pinned at bottom of screen on mobile) */}
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
