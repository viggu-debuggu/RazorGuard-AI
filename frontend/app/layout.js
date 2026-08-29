"use client";

import "./globals.css";
import React from "react";
import { AuthProvider, useAuth } from "../context/AuthContext";
import { ThemeProvider, useTheme } from "../context/ThemeContext";
import { useRouter, usePathname } from "next/navigation";

/* ── Icons ─────────────────────────────────────────────── */
const icons = {
  overview:    "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
  queue:       "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
  graph:       "M13 10V3L4 14h7v7l9-11h-7z",
  policies:    "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
  sun:         "M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z",
  moon:        "M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z",
  signout:     "M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1",
};

function NavIcon({ d, size = 15 }) {
  return (
    <svg width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
      <path d={d} />
    </svg>
  );
}

/* ── Theme Toggle ──────────────────────────────────────── */
function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  return (
    <button
      onClick={toggleTheme}
      className="theme-toggle"
      aria-label="Toggle theme"
      style={{ all: "unset", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 10px", borderRadius: "20px", border: "1px solid var(--border)", background: "var(--bg-inset)", cursor: "pointer", fontSize: "0.72rem", fontWeight: "600", color: "var(--fg-muted)", width: "100%", boxSizing: "border-box", gap: "8px" }}
    >
      <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
        <NavIcon d={isDark ? icons.moon : icons.sun} size={13} />
        {isDark ? "Dark" : "Light"}
      </span>
      {/* mini toggle pill */}
      <span style={{ width: "30px", height: "17px", borderRadius: "9px", background: isDark ? "var(--accent)" : "var(--border)", position: "relative", display: "block", transition: "background 0.2s", flexShrink: 0 }}>
        <span style={{ position: "absolute", top: "2px", left: isDark ? "14px" : "2px", width: "13px", height: "13px", borderRadius: "50%", background: "#fff", transition: "left 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.3)" }} />
      </span>
    </button>
  );
}

/* ── Main Shell ────────────────────────────────────────── */
const NavigationShell = ({ children }) => {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    if (!loading && !user && pathname !== "/login") {
      router.push("/login");
    }
  }, [user, loading, pathname]);

  if (loading) {
    return (
      <div style={{ display: "flex", minHeight: "100vh", backgroundColor: "var(--bg)" }}>
        <aside style={{ width: "var(--sidebar-width)", borderRight: "1px solid var(--border)", padding: "20px 16px", display: "flex", flexDirection: "column", gap: "14px" }}>
          <div className="skeleton" style={{ height: "24px", width: "90px", marginBottom: "10px" }} />
          {[1,2,3,4].map(i => (
            <div key={i} className="skeleton" style={{ height: "15px", width: `${55 + i * 8}%` }} />
          ))}
        </aside>
        <main style={{ flex: 1, padding: "26px 32px", display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="skeleton" style={{ height: "20px", width: "220px" }} />
          <div className="skeleton" style={{ height: "14px", width: "360px" }} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginTop: "10px" }}>
            {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: "72px", borderRadius: "10px" }} />)}
          </div>
        </main>
      </div>
    );
  }

  if (!user || pathname === "/login") {
    return <>{children}</>;
  }

  const navItems = [
    { name: "Overview",            path: "/dashboard",    icon: icons.overview },
    { name: "Investigation Queue", path: "/transactions", icon: icons.queue },
    { name: "Relationship Map",    path: "/graph",        icon: icons.graph },
    { name: "Policy Vault",        path: "/policies",     icon: icons.policies },
  ];

  return (
    <div className="app-container">
      <aside className="sidebar">
        {/* Logo */}
        <div className="sidebar-logo">
          <span className="sidebar-logo-mark">RG</span>
          <div>
            <div className="sidebar-logo-text">RazorGuard</div>
            <div style={{ fontSize: "0.58rem", color: "var(--fg-dim)", letterSpacing: "0.06em", textTransform: "uppercase", marginTop: "1px" }}>AI Risk Console</div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const active = pathname === item.path || pathname.startsWith(item.path + "/");
            return (
              <div
                key={item.name}
                className={`nav-item${active ? " active" : ""}`}
                onClick={() => router.push(item.path)}
              >
                <NavIcon d={item.icon} size={15} />
                {item.name}
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          {/* User info */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div style={{ width: "30px", height: "30px", borderRadius: "50%", background: "linear-gradient(135deg, var(--accent), var(--accent-text))", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.72rem", fontWeight: "800", color: "#fff", flexShrink: 0 }}>
              {user.full_name?.charAt(0)?.toUpperCase() || "A"}
            </div>
            <div>
              <p className="sidebar-user-name">{user.full_name}</p>
              <p className="sidebar-user-role">{user.role || "Analyst"}</p>
            </div>
          </div>

          {/* Theme toggle */}
          <ThemeToggle />

          {/* Sign out */}
          <button onClick={logout} className="sidebar-signout" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
            <NavIcon d={icons.signout} size={13} />
            Sign Out
          </button>

          <p className="sidebar-disclaimer">
            All data in this environment is synthetic and for demonstration purposes only.
          </p>
        </div>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
        <meta name="color-scheme" content="dark light" />
      </head>
      <body>
        <ThemeProvider>
          <AuthProvider>
            <NavigationShell>{children}</NavigationShell>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
