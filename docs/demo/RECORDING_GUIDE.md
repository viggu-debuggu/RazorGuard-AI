# RazorGuard AI — Demo Recording Guide

60–90 second screen recording script for judges.  
**Prerequisites:** Complete setup from Quick Start in README — `docker compose up -d --build` + seed script run.

---

## Equipment Setup

- **Resolution**: 1920×1080 (or 1280×720 for faster export)
- **Browser**: Chrome or Firefox, maximised
- **Recording tool**: OBS Studio, Loom, or any screen capture tool
- **Cursor highlight**: Enable mouse highlight plugin for visibility
- **URL**: `http://localhost:3000`

---

## Script (Shot by Shot)

### [0:00–0:12] Scene 1 — Login

| Action | Expected UI State |
|---|---|
| Open `http://localhost:3000` in browser | RazorGuard AI login page loads — dark background, logo visible |
| Click the **Email** field | Field focused |
| Type `analyst@razorguard.ai` | Email entered |
| Click the **Password** field | Field focused |
| Type `password` | Password entered (masked) |
| Click **Login** / press Enter | Brief spinner → redirect to **Dashboard** |

> **Screen region to capture**: Full browser viewport (login form centered).

---

### [0:12–0:25] Scene 2 — Dashboard Overview

| Action | Expected UI State |
|---|---|
| Wait 1 second for dashboard to load | KPI cards visible: "Processed Today", "Auto Approved", "Awaiting Review", "Blocked" |
| Move cursor over KPI cards slowly | Brief hover animation on each card |
| Briefly narrate (voiceover): _"Three transactions in the queue — Scenario C shows 86.9% risk score"_ | Volume/risk trend chart visible |

> **Screen region to capture**: Top KPI bar + trend chart.

---

### [0:25–0:45] Scene 3 — Scenario C Investigation (HIGH RISK)

| Action | Expected UI State |
|---|---|
| Click the **Transactions** sidebar link or navigate to transaction list | List of transactions visible with risk score column |
| Click on transaction `TXN-92817` (the "Escalated" row with ~86.9% score) | Investigation panel opens |
| Scroll slowly through the investigation panel | Agent reasoning steps visible: "ML Score: ~86.9%", evidence cards (geographic mismatch, velocity spike, shared device) |
| Point cursor at the **RAG compliance badges** (blue/orange badges showing policy citations) | Tooltip or detail visible showing "PSD2-Art-97" and "CNP-LIMIT-08" policy clauses |

> **Screen region to capture**: Investigation panel — full width; zoom in on RAG badge area if possible.

---

### [0:45–1:00] Scene 4 — Graph Visualisation

| Action | Expected UI State |
|---|---|
| Click the **Graph** tab in the navigation | Force-directed graph canvas loads (may take 1–2 seconds) |
| Click on the node labelled `CUST-7821` | Node highlighted; neighbour nodes (`usr_suspect_1`, `usr_suspect_2`, `usr_suspect_3`) glow in red/orange |
| Hover over the `df_demo_unseen_99` device node | Tooltip shows: shared device fingerprint, 4 linked blocked accounts |

> **Screen region to capture**: Graph canvas full width with node selected.

---

### [1:00–1:20] Scene 5 — Analyst Override + Audit Log

| Action | Expected UI State |
|---|---|
| Return to the `TXN-92817` investigation panel (click Back or Transactions list) | Investigation panel visible |
| Scroll to the **Analyst Override** section | Action buttons: "Approve", "Block", "Escalate" visible |
| Click **Block** | Action selected / highlighted |
| Type in the notes field: `Device fingerprint shared across 3 blocked suspect accounts — confirmed fraud ring.` | Text entered |
| Click **Submit Override** | Confirmation banner or status change visible; transaction status updates to "Blocked" |
| Scroll to the bottom of the investigation panel to the **Audit Log** section | New audit entry visible with timestamp, actor `Analyst: analyst@razorguard.ai`, and the exact notes submitted |

> **Screen region to capture**: Override form + resulting audit log entry (both on screen simultaneously if layout allows).

---

## Post-Recording Checklist

- [ ] Trim dead time at start/end
- [ ] Add text overlays for each scene title (optional but recommended)
- [ ] Export at ≥720p, ≤150 MB
- [ ] Upload to YouTube (unlisted), Loom, or attach as MP4 to the submission
- [ ] Paste the video link into `docs/demo/README.md` and the README badge at the top of the repo

---

## Troubleshooting

| Issue | Fix |
|---|---|
| Login fails | Re-run `docker compose exec backend python scripts/seed_data.py` |
| Graph is empty | Seed script must be run after the backend is healthy; check `docker compose logs backend` |
| Risk score differs slightly | Expected — LLM explanation varies; deterministic core score should be stable within ±1% |
| RAG badges missing | Ensure `LLM_PROVIDER=mock` or a valid Gemini API key is set in `.env` |
