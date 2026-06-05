import { useState } from "react"

// ── change this to your Render URL after deploying ──
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

const TONE_COLORS = {
  relieving:    "#6ee7b7",
  encouraging:  "#818cf8",
  urgent:       "#fb923c",
  aspirational: "#f9a8d4",
  curiosity:    "#fcd34d",
}

function toneColor(tone = "") {
  const t = tone.toLowerCase()
  return Object.entries(TONE_COLORS).find(([k]) => t.includes(k))?.[1] ?? "#64748b"
}

// ── NOTIFICATION CARD ────────────────────────────────────────────────────────

function NotifCard({ notif, index }) {
  const color = toneColor(notif.tone_used)
  return (
    <div style={{
      background: "var(--card)",
      border: `1px solid ${color}33`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 12,
      padding: "20px 24px",
      display: "flex",
      flexDirection: "column",
      gap: 10,
      animation: `fadeUp 0.4s ease ${index * 0.08}s both`,
    }}>
      {/* top row */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <span style={{ fontSize: 11, color: "var(--muted)", letterSpacing: 2 }}>
          NOTIFICATION {notif.notification_number}
        </span>
        <span style={{
          fontSize: 11, padding: "3px 10px", borderRadius: 20,
          background: color + "22", color, letterSpacing: 1,
        }}>
          {notif.tone_used}
        </span>
      </div>

      {/* title */}
      <p style={{ fontFamily:"'Syne', sans-serif", fontSize: 20, fontWeight: 700, color: "#fff", lineHeight: 1.3 }}>
        {notif.title}
      </p>

      {/* body */}
      <p style={{ fontSize: 14, color: "var(--text)", lineHeight: 1.6, opacity: 0.85 }}>
        {notif.body}
      </p>

      {/* divider */}
      <div style={{ height: 1, background: "var(--border)", margin: "4px 0" }} />

      {/* meta row */}
      <div style={{ display:"flex", flexWrap:"wrap", gap: 8 }}>
        <Tag label="Scheme" value={notif.scheme_or_service_id} color={color} />
        <Tag label="Lang"   value={notif.language}             color={color} />
        <Tag label="Friend check" value={notif.human_check}    color={notif.human_check === "yes" ? "#6ee7b7" : "#fb923c"} />
      </div>

      {/* rationale */}
      {notif.relevance_rationale && (
        <p style={{ fontSize: 12, color: "var(--muted)", fontStyle:"italic", lineHeight: 1.5 }}>
          ↳ {notif.relevance_rationale}
        </p>
      )}

      {/* signals */}
      {notif.data_signals_used && (
        <p style={{ fontSize: 11, color: "#334155", lineHeight: 1.5 }}>
          signals: {notif.data_signals_used}
        </p>
      )}
    </div>
  )
}

function Tag({ label, value, color }) {
  return (
    <span style={{
      fontSize: 11, padding: "2px 8px", borderRadius: 6,
      background: "var(--surface)", border: "1px solid var(--border)",
      color: "var(--muted)",
    }}>
      <span style={{ color }}>{label}:</span> {value}
    </span>
  )
}

// ── METADATA TABLE ───────────────────────────────────────────────────────────

function MetaTable({ profile }) {
  const rows = Object.entries(profile)
  return (
    <div style={{
      background: "var(--card)",
      border: "1px solid var(--border)",
      borderRadius: 12,
      overflow: "hidden",
    }}>
      <div style={{
        padding: "14px 20px",
        background: "var(--surface)",
        borderBottom: "1px solid var(--border)",
        fontFamily: "'Syne', sans-serif",
        fontSize: 13, fontWeight: 700, letterSpacing: 2,
        color: "var(--muted)", textTransform: "uppercase",
      }}>
        User Profile
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr" }}>
        {rows.map(([k, v], i) => (
          <div key={k} style={{
            display:"flex", flexDirection:"column", gap: 2,
            padding: "12px 20px",
            borderBottom: i < rows.length - 2 ? "1px solid var(--border)" : "none",
            borderRight: i % 2 === 0 ? "1px solid var(--border)" : "none",
          }}>
            <span style={{ fontSize: 10, color: "var(--muted)", letterSpacing: 1.5, textTransform:"uppercase" }}>
              {k.replace(/_/g," ")}
            </span>
            <span style={{ fontSize: 14, color: "var(--text)", fontWeight: 500 }}>
              {String(v) || "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── LOADER ───────────────────────────────────────────────────────────────────

function Loader() {
  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap: 16, padding: 48 }}>
      <div style={{
        width: 48, height: 48, borderRadius: "50%",
        border: "2px solid var(--border)",
        borderTop: "2px solid var(--accent)",
        animation: "spin 0.8s linear infinite",
      }} />
      <p style={{ color: "var(--muted)", fontSize: 13, letterSpacing: 1 }}>
        generating 5 notifications...
      </p>
    </div>
  )
}

// ── APP ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [userId, setUserId]         = useState("")
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState("")
  const [data, setData]             = useState(null)   // full API response

  async function handleSearch() {
    if (!userId.trim()) return
    setLoading(true)
    setError("")
    setData(null)

    try {
      const res = await fetch(`${API_BASE}/notify/${userId.trim()}`)
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || "Server error")
      }
      setData(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === "Enter") handleSearch()
  }

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "48px 24px" }}>

      {/* ── HEADER */}
      <div style={{ marginBottom: 48, textAlign:"center" }}>
        <p style={{ fontSize: 11, letterSpacing: 4, color: "var(--accent)", marginBottom: 12 }}>
          NOTIFICATION ENGINE
        </p>
        <h1 style={{
          fontFamily:"'Syne', sans-serif", fontSize: "clamp(32px,5vw,52px)",
          fontWeight: 800, lineHeight: 1.1, color: "#fff",
        }}>
          Personalized<br />
          <span style={{ color: "var(--accent)" }}>Government Alerts</span>
        </h1>
        <p style={{ color:"var(--muted)", marginTop: 16, fontSize: 14 }}>
          Enter a user ID to generate 5 independent notifications
        </p>
      </div>

      {/* ── SEARCH */}
      <div style={{ display:"flex", gap: 12, marginBottom: 40 }}>
        <input
          value={userId}
          onChange={e => setUserId(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Enter user_id  e.g. 208135"
          style={{
            flex: 1, padding: "14px 20px",
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, color: "var(--text)", fontSize: 16,
            fontFamily: "'DM Mono', monospace",
            outline: "none", transition: "border 0.2s",
          }}
          onFocus={e  => e.target.style.borderColor = "var(--accent)"}
          onBlur={e   => e.target.style.borderColor = "var(--border)"}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          style={{
            padding: "14px 28px", borderRadius: 10,
            background: loading ? "var(--surface)" : "var(--accent)",
            color: loading ? "var(--muted)" : "#0a0a0f",
            border: "none", cursor: loading ? "not-allowed" : "pointer",
            fontFamily: "'Syne', sans-serif", fontWeight: 700, fontSize: 15,
            transition: "all 0.2s",
          }}
        >
          {loading ? "..." : "Generate →"}
        </button>
      </div>

      {/* ── ERROR */}
      {error && (
        <div style={{
          padding: "14px 20px", borderRadius: 10,
          background: "#7f1d1d22", border: "1px solid #ef444444",
          color: "#fca5a5", fontSize: 14, marginBottom: 32,
        }}>
          {error}
        </div>
      )}

      {/* ── LOADER */}
      {loading && <Loader />}

      {/* ── RESULTS */}
      {data && !loading && (
        <div style={{ display:"flex", flexDirection:"column", gap: 32 }}>

          {/* generated at */}
          <p style={{ fontSize: 11, color: "var(--muted)", letterSpacing: 1 }}>
            user {data.user_id} · {new Date(data.generated_at).toLocaleString()}
          </p>

          {/* ── 5 NOTIFICATIONS */}
          <div style={{ display:"flex", flexDirection:"column", gap: 16 }}>
            <h2 style={{
              fontFamily:"'Syne', sans-serif", fontSize: 13,
              fontWeight: 700, letterSpacing: 3,
              color: "var(--muted)", textTransform:"uppercase",
            }}>
              5 Notifications
            </h2>
            {data.notifications.map((n, i) => (
              <NotifCard key={n.notification_number} notif={n} index={i} />
            ))}
          </div>

          {/* ── USER PROFILE (below) */}
          <div>
            <h2 style={{
              fontFamily:"'Syne', sans-serif", fontSize: 13,
              fontWeight: 700, letterSpacing: 3,
              color: "var(--muted)", textTransform:"uppercase",
              marginBottom: 16,
            }}>
              User Metadata
            </h2>
            <MetaTable profile={data.user_profile} />
          </div>

        </div>
      )}

      {/* ── GLOBAL STYLES */}
      <style>{`
        @keyframes spin    { to { transform: rotate(360deg); } }
        @keyframes fadeUp  {
          from { opacity: 0; transform: translateY(16px); }
          to   { opacity: 1; transform: translateY(0);    }
        }
        input::placeholder { color: #334155; }
        * { -webkit-font-smoothing: antialiased; }
      `}</style>
    </div>
  )
}
