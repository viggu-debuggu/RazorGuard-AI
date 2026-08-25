"use client";

import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const { login, user } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (user) router.push("/dashboard");
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err.message || "Authentication failed. Check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        backgroundColor: "var(--bg)",
        padding: "20px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "360px",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: "4px",
          padding: "36px 32px",
        }}
      >
        {/* Logo */}
        <div style={{ marginBottom: "28px" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginBottom: "6px" }}>
            <span
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "2rem",
                color: "var(--accent-text)",
                lineHeight: 1,
                letterSpacing: "-0.02em",
              }}
            >
              RG
            </span>
            <span
              style={{
                fontSize: "0.65rem",
                fontWeight: "700",
                letterSpacing: "0.14em",
                textTransform: "uppercase",
                color: "var(--fg-muted)",
              }}
            >
              RazorGuard
            </span>
          </div>
          <p style={{ fontSize: "0.78rem", color: "var(--fg-muted)", lineHeight: "1.4" }}>
            Post-escalation investigation console for risk operations analysts.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div
            style={{
              backgroundColor: "var(--risk-high-bg)",
              border: "1px solid var(--risk-high-border)",
              color: "var(--risk-high)",
              padding: "8px 12px",
              borderRadius: "3px",
              fontSize: "0.78rem",
              marginBottom: "16px",
              lineHeight: "1.4",
            }}
          >
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div>
            <label>Analyst Email</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="analyst@razorguard.ai"
              autoComplete="email"
              required
            />
          </div>

          <div>
            <label>Password</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </div>

          <button
            id="login-submit"
            type="submit"
            disabled={submitting}
            style={{ marginTop: "6px", padding: "10px" }}
          >
            {submitting ? "Authenticating…" : "Access Console"}
          </button>
        </form>

        {/* Footer notice */}
        <div
          style={{
            marginTop: "24px",
            paddingTop: "16px",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <p style={{ fontSize: "0.68rem", color: "var(--fg-dim)", lineHeight: "1.4" }}>
            Authorized risk operations personnel only. All sessions are logged and audited.
          </p>
        </div>
      </div>
    </div>
  );
}
