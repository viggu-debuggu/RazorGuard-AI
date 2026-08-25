"use client";

import "./globals.css";
import React from "react";
import { AuthProvider, useAuth } from "../context/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import { LogOut } from "lucide-react";

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
        {/* Skeleton sidebar */}
        <aside style={{ width: "var(--sidebar-width)", borderRight: "1px solid var(--border)", padding: "18px 16px", display: "flex", flexDirection: "column", gap: "12px" }}>
          <div className="skeleton" style={{ height: "22px", width: "80px", marginBottom: "8px" }} />
          {[1,2,3,4].map(i => (
            <div key={i} className="skeleton" style={{ height: "14px", width: `${55 + i * 8}%` }} />
          ))}
        </aside>
        {/* Skeleton content */}
        <main style={{ flex: 1, padding: "22px 28px", display: "flex", flexDirection: "column", gap: "14px" }}>
          <div className="skeleton" style={{ height: "18px", width: "220px" }} />
          <div className="skeleton" style={{ height: "14px", width: "340px" }} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginTop: "8px" }}>
            {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: "64px" }} />)}
          </div>
        </main>
      </div>
    );
  }

  if (!user || pathname === "/login") {
    return <>{children}</>;
  }

  const navItems = [
    { name: "Overview", path: "/dashboard" },
    { name: "Investigation Queue", path: "/transactions" },
    { name: "Relationship Map", path: "/graph" },
    { name: "Policy Vault", path: "/policies" },
  ];

  return (
    <div className="app-container">
      <aside className="sidebar">
        {/* Logo mark */}
        <div className="sidebar-logo">
          <span className="sidebar-logo-mark">RG</span>
          <span className="sidebar-logo-text">RazorGuard</span>
        </div>

        {/* Navigation — text-only, no icon on every item */}
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const active = pathname === item.path || pathname.startsWith(item.path + "/");
            return (
              <div
                key={item.name}
                className={`nav-item${active ? " active" : ""}`}
                onClick={() => router.push(item.path)}
              >
                {item.name}
              </div>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="sidebar-footer">
          <div>
            <p className="sidebar-user-name">{user.full_name}</p>
            <p className="sidebar-user-role">Active Session — Risk Ops Console</p>
          </div>
          <button
            onClick={logout}
            className="sidebar-signout"
          >
            Sign Out
          </button>
          <p className="sidebar-disclaimer">
            All transaction, customer, and relationship data in this environment is synthetic.
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
          href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>
          <NavigationShell>{children}</NavigationShell>
        </AuthProvider>
      </body>
    </html>
  );
}
