"use client";

import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "next/navigation";
import { Shield } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const { login, user } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (user) {
      router.push("/");
    }
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err.message || "Failed to log in.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      minHeight: "100vh",
      background: "radial-gradient(circle at center, #0c1220 0%, #09090b 100%)",
      padding: "20px"
    }}>
      <div className="glass-card" style={{ width: "100%", maxWidth: "400px", padding: "40px 30px" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px", marginBottom: "30px" }}>
          <Shield size={44} color="var(--accent)" />
          <h2 style={{ fontSize: "1.6rem", fontWeight: "700", letterSpacing: "-0.05em", color: "#fff" }}>RazorGuard AI</h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", textAlign: "center" }}>
            Autonomous Payment Risk Management Portal
          </p>
        </div>

        {error && (
          <div style={{
            backgroundColor: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            color: "var(--danger)",
            padding: "12px",
            borderRadius: "8px",
            fontSize: "0.85rem",
            marginBottom: "20px"
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
              Analyst Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="analyst@razorguard.ai"
              required
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: "600", color: "var(--text-muted)", marginBottom: "6px" }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          <button type="submit" disabled={submitting} style={{ marginTop: "10px", padding: "12px" }}>
            {submitting ? "Signing In..." : "Access Console"}
          </button>
        </form>
        
        <div style={{ marginTop: "25px", fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center" }}>
          <p>Confidential analyst interface. Authorized login credentials only.</p>
        </div>
      </div>
    </div>
  );
}
