"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { API_URL } from "../lib/api";


const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load cached session parameters at mount time
    const savedToken = localStorage.getItem("token");
    const savedUser = localStorage.getItem("user");
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken(null);
    setUser(null);
  }, []);

  // Global fetch wrapper — auto-logout on 401 so stale tokens never
  // leave the analyst on a broken screen after a container restart.
  const apiFetch = useCallback(
    async (url, options = {}) => {
      const res = await fetch(url, options);
      if (res.status === 401) {
        logout();
        // Return the response so callers can still inspect it if needed
      }
      return res;
    },
    [logout]
  );

  const login = async (email, password) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Authentication check failed.");
      }
      
      const data = await response.json();
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("user", JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
      return data.user;
    } catch (error) {
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, apiFetch, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
