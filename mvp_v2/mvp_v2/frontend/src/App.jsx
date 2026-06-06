import { useState, useEffect } from "react"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

const TONE_COLORS = {
  relieving:    "#6ee7b7",
  encouraging:  "#818cf8",
  urgent:       "#fb923c",
  aspirational: "#f9a8d4",
  curiosity:    "#fcd34d",
}

const SEGMENT_ICONS = {
  content_reader:   "📄",
  high_converter:   "🚀",
  job_hunter:       "💼",
  scheme_seeker:    "🏛️",
  service_explorer: "🔧",
}

function toneColor(tone = "") {
  const t = tone.toLowerCase()
  return Object.entries(TONE_COLORS).find(([k]) => t.includes(k))?.[1] ?? "#64748b"
}

// ── SEGMENT CARD ─────────────────────────────────────────────────────────────

function SegmentCard({ segment }) {
  if (!segment) return null
  const { label, traits = [], notification_responsive, segment_pct, color, is_best, segment_key } = segment
  const icon   = SEGMENT_ICONS[segment_key] || "👤"
  const pctNum = parseFloat(segment_pct) || 0

  return (
    <div style={{
      background: "var(--card)",
      border: `1px solid ${color}44`,
      borderRadius: 14,
      padding: "20px 24px",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* glow */}
      <div style={{
        position: "absolute", top: -30, right: -30,
        width: 120, height: 120, borderRadius: "50%",
        background: color + "18", pointerEvents: "none",
      }} />

      {/* header */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom: 14 }}>
        <div style={{ display:"flex", alignItems:"center", gap: 12 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 10,
            background: color + "20",
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize: 22,
          }}>
            {icon}
          </div>
          <div>
            <div style={{ display:"flex", alignItems:"center", gap: 8 }}>
              <p style={{ fontFamily:"'Syne',sans-serif", fontSize: 18, fontWeight: 700, color:"#fff", margin: 0 }}>
                {label}
              </p>
              {is_best && (
                <span style={{
                  fontSize: 9, padding:"2px 8px", borderRadius: 20,
                  background: color + "25", color,
                  letterSpacing: 1.2, fontWeight: 700, textTransform:"uppercase",
                }}>
                  Best Segment
                </span>
              )}
            </div>
            <p style={{ fontSize: 11, color:"var(--muted)", margin:"3px 0 0" }}>
              {notification_responsive} notification responsive
            </p>
          </div>
        </div>
        <span style={{ fontFamily:"'Syne',sans-serif", fontSize: 26, fontWeight: 800, color }}>
          {segment_pct}
        </span>
      </div>

      {/* progress bar */}
      <div style={{ height: 3, background:"var(--border)", borderRadius: 99, marginBottom: 14, overflow:"hidden" }}>
        <div style={{
          height:"100%", width:`${pctNum}%`,
          background: `linear-gradient(90deg,${color}88,${color})`,
          borderRadius: 99,
        }} />
      </div>

      {/* traits */}
      <div style={{ display:"flex", flexWrap:"wrap", gap: 7 }}>
        {traits.map((t, i) => (
          <span key={i} style={{
            fontSize: 12, padding:"4px 10px", borderRadius: 6,
            background:"var(--surface)", border:"1px solid var(--border)", color:"var(--text)",
          }}>
            <span style={{ color, marginRight: 4 }}>•</span>{t}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── NOTIFICATION CARD ─────────────────────────────────────────────────────────

function NotifCard({ notif, index }) {
  const color = toneColor(notif.tone_used)
  return (
    <div style={{
      background:"var(--card)",
      border:`1px solid ${color}33`,
      borderLeft:`3px solid ${color}`,
      borderRadius: 12,
      padding:"20px 24px",
      display:"flex", flexDirection:"column", gap: 10,
      animation:`fadeUp 0.4s ease ${index * 0.08}s both`,
    }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <span style={{ fontSize: 11, color:"var(--muted)", letterSpacing: 2 }}>
          NOTIFICATION {notif.notification_number}
        </span>
        <span style={{ fontSize: 11, padding:"3px 10px", borderRadius: 20, background: color+"22", color, letterSpacing: 1 }}>
          {notif.tone_used}
        </span>
      </div>

      <p style={{ fontFamily:"'Syne',sans-serif", fontSize: 20, fontWeight: 700, color:"#fff", lineHeight: 1.3 }}>
        {notif.title}
      </p>
      <p style={{ fontSize: 14, color:"var(--text)", lineHeight: 1.6, opacity: 0.85 }}>
        {notif.body}
      </p>

      <div style={{ height: 1, background:"var(--border)", margin:"4px 0" }} />

      {notif.scheme_name && (
        <p style={{ fontSize: 13, fontWeight: 600, color, margin: 0 }}>
          {notif.scheme_name}
        </p>
      )}

      <div style={{ display:"flex", flexWrap:"wrap", gap: 8 }}>
        <Tag label="ID"       value={notif.scheme_id}              color={color} />
        <Tag label="Lang"     value={notif.language}               color={color} />
        <Tag label="Vector"   value={notif.dependency_vector_used} color={color} />
        <Tag label="Strategy" value={notif.attention_strategy}     color={color} />
      </div>

      {notif.relevance_rationale && (
        <p style={{ fontSize: 12, color:"var(--muted)", fontStyle:"italic", lineHeight: 1.5 }}>
          ↳ {notif.relevance_rationale}
        </p>
      )}
    </div>
  )
}

function Tag({ label, value, color }) {
  return (
    <span style={{
      fontSize: 11, padding:"2px 8px", borderRadius: 6,
      background:"var(--surface)", border:"1px solid var(--border)", color:"var(--muted)",
    }}>
      <span style={{ color }}>{label}:</span> {value}
    </span>
  )
}

// ── METADATA TABLE ────────────────────────────────────────────────────────────

function MetaTable({ profile }) {
  const rows = Object.entries(profile)
  return (
    <div style={{ background:"var(--card)", border:"1px solid var(--border)", borderRadius: 12, overflow:"hidden" }}>
      <div style={{
        padding:"14px 20px", background:"var(--surface)",
        borderBottom:"1px solid var(--border)",
        fontFamily:"'Syne',sans-serif", fontSize: 13, fontWeight: 700,
        letterSpacing: 2, color:"var(--muted)", textTransform:"uppercase",
      }}>
        User Profile
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr" }}>
        {rows.map(([k, v], i) => (
          <div key={k} style={{
            display:"flex", flexDirection:"column", gap: 2,
            padding:"12px 20px",
            borderBottom: i < rows.length - 2 ? "1px solid var(--border)" : "none",
            borderRight:  i % 2 === 0 ? "1px solid var(--border)" : "none",
          }}>
            <span style={{ fontSize: 10, color:"var(--muted)", letterSpacing: 1.5, textTransform:"uppercase" }}>
              {k.replace(/_/g," ")}
            </span>
            <span style={{ fontSize: 14, color:"var(--text)", fontWeight: 500 }}>
              {String(v) || "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── DASHBOARD TABLE ───────────────────────────────────────────────────────────

function DashboardTable({ records }) {
  if (!records.length) return null

  const segColor = {
    content_reader:   "#3b82f6",
    high_converter:   "#16a34a",
    job_hunter:       "#92400e",
    scheme_seeker:    "#7c3aed",
    service_explorer: "#b45309",
  }
  const segLabel = {
    content_reader:   "Content Reader",
    high_converter:   "High Converter",
    job_hunter:       "Job Hunter",
    scheme_seeker:    "Scheme Seeker",
    service_explorer: "Service Explorer",
  }

  return (
    <div style={{ background:"var(--card)", border:"1px solid var(--border)", borderRadius: 12, overflow:"hidden" }}>
      {/* header */}
      <div style={{
        display:"grid",
        gridTemplateColumns:"90px 130px 1fr 1fr 160px",
        padding:"12px 20px",
        background:"var(--surface)", borderBottom:"1px solid var(--border)",
        fontSize: 10, color:"var(--muted)", letterSpacing: 1.5, textTransform:"uppercase",
        fontWeight: 700,
      }}>
        <span>User ID</span>
        <span>Segment</span>
        <span>Title</span>
        <span>Scheme</span>
        <span>Vector · Strategy</span>
      </div>

      {records.map(user =>
        user.notifications.map((n, ni) => {
          const color = segColor[user.segment_key] || "#64748b"
          return (
            <div key={`${user.user_id}-${ni}`} style={{
              display:"grid",
              gridTemplateColumns:"90px 130px 1fr 1fr 160px",
              padding:"12px 20px",
              borderBottom:"1px solid var(--border)",
              alignItems:"center",
              fontSize: 13,
            }}>
              <span style={{ color:"var(--muted)", fontFamily:"'DM Mono',monospace", fontSize: 11 }}>
                {user.user_id}
              </span>
              <span style={{
                fontSize: 11, padding:"3px 8px", borderRadius: 6,
                background: color+"20", color,
                fontWeight: 600, whiteSpace:"nowrap", width:"fit-content",
              }}>
                {SEGMENT_ICONS[user.segment_key]} {segLabel[user.segment_key] || user.segment_key}
              </span>
              <div>
                <p style={{ color:"var(--text)", fontWeight: 500, margin:"0 0 3px", paddingRight: 12 }}>
                  {n.title}
                </p>
                <p style={{ color:"var(--muted)", fontSize: 11, margin: 0 }}>{n.body}</p>
              </div>
              <div>
                <p style={{ color, fontSize: 11, fontWeight: 600, margin:"0 0 2px" }}>{n.scheme_name}</p>
                <p style={{ color:"var(--muted)", fontSize: 10, margin: 0, fontFamily:"'DM Mono',monospace" }}>{n.scheme_id}</p>
              </div>
              <div style={{ fontSize: 10, color:"var(--muted)", lineHeight: 1.6 }}>
                <div>{n.dependency_vector_used}</div>
                <div style={{ color:"var(--accent)", opacity: 0.7 }}>{n.attention_strategy}</div>
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}

// ── LOADER ────────────────────────────────────────────────────────────────────

function Loader() {
  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap: 16, padding: 48 }}>
      <div style={{
        width: 48, height: 48, borderRadius:"50%",
        border:"2px solid var(--border)", borderTop:"2px solid var(--accent)",
        animation:"spin 0.8s linear infinite",
      }} />
      <p style={{ color:"var(--muted)", fontSize: 13, letterSpacing: 1 }}>
        generating 5 notifications...
      </p>
    </div>
  )
}

// ── SECTION HEADER ────────────────────────────────────────────────────────────

function SectionHead({ title }) {
  return (
    <h2 style={{
      fontFamily:"'Syne',sans-serif", fontSize: 13, fontWeight: 700,
      letterSpacing: 3, color:"var(--muted)", textTransform:"uppercase",
      marginBottom: 14,
    }}>
      {title}
    </h2>
  )
}

// ── APP ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [userId,    setUserId]    = useState("")
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState("")
  const [data,      setData]      = useState(null)
  const [dashboard, setDashboard] = useState([])

  // load dashboard on mount
  useEffect(() => { loadDashboard() }, [])

  async function loadDashboard() {
    try {
      const res = await fetch(`${API_BASE}/dashboard`)
      if (res.ok) setDashboard(await res.json())
    } catch(e) {
      console.warn("Dashboard load failed:", e)
    }
  }

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
      await loadDashboard()   // refresh dashboard after new entry
    } catch(e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === "Enter") handleSearch()
  }

  return (
    <div style={{ maxWidth: 900, margin:"0 auto", padding:"48px 24px" }}>

      {/* HEADER */}
      <div style={{ marginBottom: 48, textAlign:"center" }}>
        <p style={{ fontSize: 11, letterSpacing: 4, color:"var(--accent)", marginBottom: 12 }}>
          NOTIFICATION ENGINE
        </p>
        <h1 style={{
          fontFamily:"'Syne',sans-serif", fontSize:"clamp(32px,5vw,52px)",
          fontWeight: 800, lineHeight: 1.1, color:"#fff",
        }}>
          Personalized<br />
          <span style={{ color:"var(--accent)" }}>Government Alerts</span>
        </h1>
        <p style={{ color:"var(--muted)", marginTop: 16, fontSize: 14 }}>
          Enter a user ID to generate 5 independent notifications
        </p>
      </div>

      {/* SEARCH */}
      <div style={{ display:"flex", gap: 12, marginBottom: 40 }}>
        <input
          value={userId}
          onChange={e => setUserId(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Enter user_id  e.g. 208135"
          style={{
            flex: 1, padding:"14px 20px",
            background:"var(--surface)", border:"1px solid var(--border)",
            borderRadius: 10, color:"var(--text)", fontSize: 16,
            fontFamily:"'DM Mono',monospace",
            outline:"none", transition:"border 0.2s",
          }}
          onFocus={e => e.target.style.borderColor = "var(--accent)"}
          onBlur={e  => e.target.style.borderColor = "var(--border)"}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          style={{
            padding:"14px 28px", borderRadius: 10,
            background: loading ? "var(--surface)" : "var(--accent)",
            color: loading ? "var(--muted)" : "#0a0a0f",
            border:"none", cursor: loading ? "not-allowed" : "pointer",
            fontFamily:"'Syne',sans-serif", fontWeight: 700, fontSize: 15,
            transition:"all 0.2s",
          }}
        >
          {loading ? "..." : "Generate →"}
        </button>
      </div>

      {/* ERROR */}
      {error && (
        <div style={{
          padding:"14px 20px", borderRadius: 10,
          background:"#7f1d1d22", border:"1px solid #ef444444",
          color:"#fca5a5", fontSize: 14, marginBottom: 32,
        }}>
          {error}
        </div>
      )}

      {/* LOADER */}
      {loading && <Loader />}

      {/* RESULTS */}
      {data && !loading && (
        <div style={{ display:"flex", flexDirection:"column", gap: 32 }}>

          <p style={{ fontSize: 11, color:"var(--muted)", letterSpacing: 1 }}>
            user {data.user_id} · {new Date(data.generated_at).toLocaleString()}
          </p>

          {/* SEGMENT */}
          {data.user_segment && (
            <div>
              <SectionHead title="User Segment" />
              <SegmentCard segment={data.user_segment} />
            </div>
          )}

          {/* 5 NOTIFICATIONS */}
          <div style={{ display:"flex", flexDirection:"column", gap: 16 }}>
            <SectionHead title="5 Notifications" />
            {data.notifications.map((n, i) => (
              <NotifCard key={n.notification_number} notif={n} index={i} />
            ))}
          </div>

          {/* USER PROFILE */}
          <div>
            <SectionHead title="User Metadata" />
            <MetaTable profile={data.user_profile} />
          </div>

        </div>
      )}

      {/* DASHBOARD */}
      {dashboard.length > 0 && (
        <div style={{ marginTop: 80 }}>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom: 16 }}>
            <SectionHead title={`All Generated Notifications (${dashboard.reduce((a,u) => a + u.notifications.length, 0)} total)`} />
            <button
              onClick={loadDashboard}
              style={{
                padding:"6px 14px", borderRadius: 8, fontSize: 12,
                background:"var(--surface)", border:"1px solid var(--border)",
                color:"var(--muted)", cursor:"pointer",
              }}
            >
              ↻ Refresh
            </button>
          </div>
          <DashboardTable records={dashboard} />
        </div>
      )}

      <style>{`
        @keyframes spin   { to { transform: rotate(360deg); } }
        @keyframes fadeUp {
          from { opacity:0; transform:translateY(16px); }
          to   { opacity:1; transform:translateY(0); }
        }
        input::placeholder { color: #334155; }
        * { -webkit-font-smoothing: antialiased; }
      `}</style>
    </div>
  )
}
