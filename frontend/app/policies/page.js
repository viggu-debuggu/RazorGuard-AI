"use client";

import React, { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { FileUp, Search, BookOpen, AlertCircle } from "lucide-react";

export default function PoliciesCenter() {
  const { token } = useAuth();
  
  // Document Upload State
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Search RAG State
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

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
        headers: { "Authorization": `Bearer ${token}` },
        body: formData
      });
      
      const data = await response.json();
      if (response.ok) {
        setUploadStatus({ success: true, message: `Successfully uploaded manual and indexed ${data.chunks_indexed} semantic chunks.` });
        setTitle("");
        setFile(null);
        e.target.reset();
      } else {
        setUploadStatus({ success: false, message: data.detail || "Failed to upload manual." });
      }
    } catch (err) {
      setUploadStatus({ success: false, message: "Network connection error occurred." });
    } finally {
      setUploading(false);
    }
  };

  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    if (!searchQuery || !token) return;
    
    setSearching(true);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/policies/search?query=${encodeURIComponent(searchQuery)}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSearchResults(data);
      } else {
        console.error("Failed to query policies store.");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div>
      <h1>Compliance Policy Center</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "30px" }}>
        
        {/* Left Column: Upload New Policy */}
        <div className="glass-card" style={{ height: "fit-content" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "15px" }}>
            <FileUp size={22} color="var(--accent)" />
            <h2>Upload Risk Guidelines</h2>
          </div>
          
          <form onSubmit={handleUploadSubmit} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "4px" }}>
                Manual/Policy Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Card-Not-Present Risk Policy"
                required
              />
            </div>
            
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "4px" }}>
                Select File (PDF / TXT)
              </label>
              <input
                type="file"
                accept=".pdf,.txt"
                onChange={(e) => setFile(e.target.files[0])}
                style={{ padding: "8px 0" }}
                required
              />
            </div>

            <button type="submit" disabled={uploading}>
              {uploading ? "Indexing Document..." : "Import & Index Manual"}
            </button>
          </form>

          {uploadStatus && (
            <div style={{
              marginTop: "15px",
              padding: "12px",
              borderRadius: "8px",
              fontSize: "0.8rem",
              backgroundColor: uploadStatus.success ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
              border: `1px solid ${uploadStatus.success ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
              color: uploadStatus.success ? "var(--success)" : "var(--danger)"
            }}>
              {uploadStatus.message}
            </div>
          )}
        </div>

        {/* Right Column: Search/Query RAG store */}
        <div style={{ display: "flex", flexDirection: "column", gap: "25px" }}>
          
          <div className="glass-card">
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "15px" }}>
              <BookOpen size={22} color="var(--accent)" />
              <h2>Compliance Search Engine</h2>
            </div>
            
            <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
              <div style={{ flexGrow: 1, position: "relative" }}>
                <Search size={18} color="var(--text-muted)" style={{ position: "absolute", left: "12px", top: "12px" }} />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Ask policy rules: CNP transaction limit, PSD2 verification directives..."
                  style={{ paddingLeft: "38px" }}
                  required
                />
              </div>
              <button type="submit" disabled={searching}>
                {searching ? "Querying..." : "Search"}
              </button>
            </form>

            {/* Results Grid */}
            <div style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
              {searchResults.length === 0 ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "40px", color: "var(--text-muted)" }}>
                  <AlertCircle size={32} style={{ marginBottom: "10px" }} />
                  <p style={{ fontSize: "0.85rem" }}>Query the Compliance Policy Database.</p>
                  <p style={{ fontSize: "0.75rem", marginTop: "4px" }}>Results are blended using Reciprocal Rank Fusion.</p>
                </div>
              ) : (
                searchResults.map((result, idx) => (
                  <div
                    key={idx}
                    className="glass-card"
                    style={{
                      backgroundColor: "rgba(9, 9, 11, 0.4)",
                      padding: "16px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px"
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem" }}>
                      <span style={{ color: "var(--accent)", fontWeight: "600" }}>{result.document_title}</span>
                      <span style={{ color: "var(--success)", fontWeight: "700" }}>RRF Score: {result.score.toFixed(0)}%</span>
                    </div>
                    <p style={{ fontSize: "0.85rem", color: "#f4f4f5", lineHeight: "1.4" }}>{result.content}</p>
                    <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontStyle: "italic", alignSelf: "flex-end" }}>
                      File: {result.filename} (Chunk: {result.chunk_index})
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
