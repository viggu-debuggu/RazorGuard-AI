"use client";

import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";

export default function PoliciesCenter() {
  const { token } = useAuth();

  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploading, setUploading] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [expandedRow, setExpandedRow] = useState(null);

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!file || !token) return;

    setUploading(true);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append("title", title);
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/api/v1/policies/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await response.json();
      if (response.ok) {
        setUploadStatus({
          success: true,
          message: `Indexed ${data.chunks_indexed} semantic chunks from "${title}".`,
        });
        setTitle("");
        setFile(null);
        e.target.reset();
      } else {
        setUploadStatus({ success: false, message: data.detail || "Upload failed." });
      }
    } catch {
      setUploadStatus({ success: false, message: "Network error during upload." });
    } finally {
      setUploading(false);
    }
  };

  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    if (!searchQuery || !token) return;

    setSearching(true);
    setSearchResults([]);
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/policies/search?query=${encodeURIComponent(searchQuery)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div>
      {/* Page header */}
      <div className="page-header">
        <h1 className="page-title">Policy Vault</h1>
        <span className="page-subtitle">
          Indexed compliance manuals — queried via Hybrid RRF (dense + sparse retrieval)
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: "12px", alignItems: "start" }}>

        {/* Left: Upload form */}
        <div className="panel">
          <h2>Import Policy Manual</h2>
          <form
            onSubmit={handleUploadSubmit}
            style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}
          >
            <fieldset
              style={{
                border: "1px solid var(--border)",
                borderRadius: "3px",
                padding: "10px 12px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              <div>
                <label>Manual Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Card-Not-Present Risk Policy v3"
                  required
                />
              </div>
              <div>
                <label>File (PDF or TXT)</label>
                <input
                  type="file"
                  accept=".pdf,.txt"
                  onChange={(e) => setFile(e.target.files[0])}
                  style={{ padding: "6px 0", cursor: "pointer" }}
                  required
                />
              </div>
            </fieldset>

            <button type="submit" disabled={uploading}>
              {uploading ? "Indexing…" : "Import & Index Manual"}
            </button>
          </form>

          {uploadStatus && (
            <div
              style={{
                marginTop: "12px",
                padding: "10px 12px",
                borderRadius: "3px",
                fontSize: "0.75rem",
                lineHeight: "1.4",
                backgroundColor: uploadStatus.success ? "var(--risk-safe-bg)" : "var(--risk-high-bg)",
                border: `1px solid ${uploadStatus.success ? "var(--risk-safe-border)" : "var(--risk-high-border)"}`,
                color: uploadStatus.success ? "var(--risk-safe)" : "var(--risk-high)",
              }}
            >
              {uploadStatus.message}
            </div>
          )}
        </div>

        {/* Right: Search + Results */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>

          {/* Search bar */}
          <div className="panel">
            <h2>Compliance Search Engine</h2>
            <form
              onSubmit={handleSearchSubmit}
              style={{ display: "flex", gap: "8px", marginTop: "8px" }}
            >
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder='e.g. "CNP transaction limit" or "SCA exemption criteria"'
                required
                style={{ flex: 1 }}
              />
              <button type="submit" disabled={searching} style={{ whiteSpace: "nowrap", minWidth: "80px" }}>
                {searching ? "Querying…" : "Search"}
              </button>
            </form>
          </div>

          {/* Results */}
          {searchResults.length === 0 && !searching ? (
            <div
              className="panel"
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                padding: "40px 20px",
                color: "var(--fg-dim)",
                gap: "6px",
                textAlign: "center",
              }}
            >
              <span style={{ fontSize: "1.6rem" }}>§</span>
              <p style={{ fontSize: "0.8rem", color: "var(--fg-muted)" }}>
                Enter a compliance question to search indexed policy manuals.
              </p>
              <p style={{ fontSize: "0.7rem", color: "var(--fg-dim)" }}>
                Try: "CNP transaction limit" · "SCA exemption criteria" · "RBI card-present rules"
              </p>
            </div>
          ) : searching ? (
            <div className="panel" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton" style={{ height: "56px" }} />
              ))}
            </div>
          ) : (
            <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
              <div className="data-table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th style={{ width: "26%" }}>Document</th>
                      <th style={{ width: "8%" }}>Chunk</th>
                      <th style={{ width: "12%", textAlign: "right" }}>RRF Score</th>
                      <th>Excerpt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {searchResults.map((result, idx) => (
                      <React.Fragment key={idx}>
                        <tr
                          onClick={() => setExpandedRow(expandedRow === idx ? null : idx)}
                          style={{ cursor: "pointer" }}
                        >
                          <td style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--accent-text)" }}>
                            {result.document_title}
                          </td>
                          <td>
                            <span className="tabular" style={{ fontSize: "0.72rem", color: "var(--fg-muted)" }}>
                              #{result.chunk_index}
                            </span>
                          </td>
                          <td className="num">
                            <span
                              className="tabular"
                              style={{
                                fontSize: "0.78rem",
                                fontWeight: "700",
                                color: result.score > 70 ? "var(--risk-safe)" : result.score > 40 ? "var(--risk-warn)" : "var(--fg-muted)",
                              }}
                            >
                              {result.score.toFixed(0)}%
                            </span>
                          </td>
                          <td
                            style={{
                              fontSize: "0.75rem",
                              color: "var(--fg-muted)",
                              maxWidth: "360px",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: expandedRow === idx ? "normal" : "nowrap",
                            }}
                          >
                            {result.content}
                          </td>
                        </tr>
                        {expandedRow === idx && (
                          <tr>
                            <td
                              colSpan={4}
                              style={{
                                padding: "10px 14px",
                                backgroundColor: "var(--bg-inset)",
                                fontSize: "0.78rem",
                                color: "var(--fg)",
                                lineHeight: "1.55",
                                borderBottom: "1px solid var(--border)",
                              }}
                            >
                              <p style={{ marginBottom: "6px", fontStyle: "italic" }}>{result.content}</p>
                              <p style={{ fontSize: "0.65rem", color: "var(--fg-dim)" }}>
                                Source: {result.filename} · Chunk {result.chunk_index}
                              </p>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
