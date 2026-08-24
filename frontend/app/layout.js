"use client";

import "./globals.css";
import React from "react";
import { AuthProvider, useAuth } from "../context/AuthContext";
import { useRouter, usePathname } from "next/navigation";
import { Shield, LayoutDashboard, ListTodo, FileText, Share2, LogOut } from "lucide-react";

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
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <p style={{ color: "var(--accent)", fontSize: "1.2rem", fontWeight: "600" }}>Booting RazorGuard Console...</p>
      </div>
    );
  }

  // Login page doesn't get the sidebar layout
  if (!user || pathname === "/login") {
    return <>{children}</>;
  }

  const navItems = [
    { name: "Risk Dashboard", path: "/", icon: <LayoutDashboard size={20} /> },
    { name: "Transactions Queue", path: "/transactions", icon: <ListTodo size={20} /> },
    { name: "Network Graph", path: "/graph", icon: <Share2 size={20} /> },
    { name: "Compliance Policies", path: "/policies", icon: <FileText size={20} /> },
  ];

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "35px" }}>
          <Shield size={28} color="var(--accent)" />
          <span style={{ fontWeight: "700", fontSize: "1.2rem", letterSpacing: "-0.05em" }}>RazorGuard AI</span>
        </div>
        
        <nav style={{ display: "flex", flexDirection: "column", gap: "8px", flexGrow: 1 }}>
          {navItems.map((item) => {
            const active = pathname === item.path || pathname.startsWith(item.path + "/");
            return (
              <div
                key={item.name}
                onClick={() => router.push(item.path)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  padding: "12px 16px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "0.9rem",
                  fontWeight: "500",
                  backgroundColor: active ? "rgba(56, 189, 248, 0.1)" : "transparent",
                  color: active ? "var(--accent)" : "var(--text-muted)",
                  transition: "background-color 0.2s, color 0.2s"
                }}
              >
                {item.icon}
                {item.name}
              </div>
            );
          })}
        </nav>

        <div style={{ borderTop: "1px solid var(--card-border)", paddingTop: "15px", display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>
            <p style={{ fontSize: "0.85rem", fontWeight: "600" }}>{user.full_name}</p>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{user.role}</p>
          </div>
          <button
            onClick={logout}
            className="secondary"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              padding: "8px 12px",
              fontSize: "0.85rem"
            }}
          >
            <LogOut size={16} />
            Sign Out
          </button>
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
      <body>
        <AuthProvider>
          <NavigationShell>{children}</NavigationShell>
        </AuthProvider>
      </body>
    </html>
  );
}
