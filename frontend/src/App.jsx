import { useState, useEffect, useMemo } from "react"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

// ── CONSTANTS ─────────────────────────────────────────────────────────────────

const SEG = {
  content_reader:   { label:"Content Reader",   color:"#3b82f6", icon:"📄", pct:"45.8%", resp:"12.1%", traits:["High article clicks & views","Long engagement time"] },
  high_converter:   { label:"High Converter",   color:"#16a34a", icon:"🚀", pct:"18.0%", resp:"34.2%", traits:["Contact clicks & enquiries","Completed submissions"], best:true },
  job_hunter:       { label:"Job Hunter",       color:"#d97706", icon:"💼", pct:"16.3%", resp:"15.7%", traits:["Job card & option clicks","Job-focused browsing"] },
  scheme_seeker:    { label:"Scheme Seeker",    color:"#7c3aed", icon:"🏛️", pct:"10.9%", resp:"9.8%",  traits:["Scheme & category clicks","Profile completion intent"] },
  service_explorer: { label:"Service Explorer", color:"#b45309", icon:"🔧", pct:"8.9%",  resp:"14.3%", traits:["Service & sub-service clicks","Deep service navigation"] },
}
const SEG_KEYS   = Object.keys(SEG)
const VECTORS    = ["Dependent Aspirational","Shared Household Distress","High Density Dilution","Independent Pro"]
const STRATEGIES = ["Fatigue Breakthrough","Swift Action Drive","Educational Hook"]

// ── MICRO COMPONENTS ──────────────────────────────────────────────────────────

const Tag = ({ label, value, color }) => !value ? null : (
  <span style={{
    display:"inline-flex", alignItems:"center", gap:4,
    fontSize:11, padding:"3px 8px", borderRadius:4,
    background:"var(--surface)", border:"1px solid var(--border)", color:"var(--muted)",
  }}>
    <span style={{ color, fontWeight:600 }}>{label}</span> {value}
  </span>
)

const Pill = ({ children, color, outline }) => (
  <span style={{
    fontSize:10, padding:"2px 8px", borderRadius:4,
    background: outline ? "transparent" : color+"15",
    border: `1px solid ${outline ? color+"40" : color+"28"}`,
    color: outline ? color+"bb" : color,
    fontWeight:500, letterSpacing:0.2, whiteSpace:"nowrap",
  }}>{children}</span>
)

const Divider = () => <div style={{ height:1, background:"var(--border)", margin:"8px 0" }} />

// ── LOADER ────────────────────────────────────────────────────────────────────

const Loader = () => (
  <div style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:10, padding:44 }}>
    <div style={{ width:28, height:28, borderRadius:"50%", border:"1.5px solid var(--border)", borderTop:"1.5px solid var(--accent)", animation:"spin 0.9s linear infinite" }} />
    <p style={{ color:"var(--muted)", fontSize:11, letterSpacing:0.5, margin:0 }}>Generating 5 notifications…</p>
  </div>
)

// ── SEGMENT CARD (generate tab) ───────────────────────────────────────────────

const SegmentCard = ({ segment }) => {
  if (!segment) return null
  const { label, traits=[], notification_responsive, segment_pct, color, is_best, segment_key } = segment
  const s = SEG[segment_key] || {}
  const pct = parseFloat(segment_pct || s.pct) || 0
  return (
    <div style={{
      background:"var(--card)",
      border:"1px solid var(--border)",
      borderTop:`2px solid ${color}60`,
      borderRadius:10, padding:"18px 20px",
      boxShadow:"0 1px 4px rgba(0,0,0,0.25)",
    }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <div style={{ width:38, height:38, borderRadius:8, background:color+"15", border:`1px solid ${color}22`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:17 }}>{s.icon}</div>
          <div>
            <div style={{ display:"flex", alignItems:"center", gap:8 }}>
              <p style={{ fontFamily:"'Syne',sans-serif", fontSize:15, fontWeight:600, color:"var(--text)", margin:0 }}>{label}</p>
              {is_best && <Pill color={color}>Best Segment</Pill>}
            </div>
            <p style={{ fontSize:11, color:"var(--muted)", margin:"3px 0 0" }}>{notification_responsive} notification responsive</p>
          </div>
        </div>
        <span style={{ fontFamily:"'Syne',sans-serif", fontSize:22, fontWeight:600, color }}>{segment_pct}</span>
      </div>
      <div style={{ height:2, background:"var(--border)", borderRadius:99, marginBottom:12, overflow:"hidden" }}>
        <div style={{ height:"100%", width:`${pct}%`, background:color, borderRadius:99, opacity:0.65 }} />
      </div>
      <div style={{ display:"flex", flexWrap:"wrap", gap:5 }}>
        {(traits.length ? traits : s.traits||[]).map((t,i) => (
          <span key={i} style={{ fontSize:11, padding:"3px 9px", borderRadius:4, background:"var(--surface)", border:"1px solid var(--border)", color:"var(--text)", opacity:0.85 }}>
            <span style={{ color, marginRight:4, opacity:0.7 }}>·</span>{t}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── NOTIF CARD (generate tab) ─────────────────────────────────────────────────

const NotifCard = ({ notif, index }) => {
  const sbKey = notif.source_bucket || ""
  const s     = SEG[sbKey] || {}
  const color = s.color || "#4db8a0"
  return (
    <div style={{
      background:"var(--card)",
      border:"1px solid var(--border)",
      borderTop:`2px solid ${color}55`,
      borderRadius:10, padding:"16px 20px",
      display:"flex", flexDirection:"column", gap:10,
      animation:`fadeUp 0.3s ease ${index*0.05}s both`,
      boxShadow:"0 1px 3px rgba(0,0,0,0.18)",
    }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <span style={{ fontSize:11, color:"var(--muted)", letterSpacing:0.3 }}>Notification {notif.notification_number}</span>
        <div style={{ display:"flex", gap:5, alignItems:"center" }}>
          {sbKey && <Pill color={color}>{s.icon} {s.label}</Pill>}
          {notif.attention_strategy && <Pill color="#48566a" outline>{notif.attention_strategy}</Pill>}
        </div>
      </div>
      <p style={{ fontFamily:"'Syne',sans-serif", fontSize:16, fontWeight:600, color:"var(--text)", lineHeight:1.35, margin:0 }}>{notif.title}</p>
      <p style={{ fontSize:13, color:"var(--text)", lineHeight:1.65, opacity:0.72, margin:0 }}>{notif.body}</p>
      <Divider />
      {notif.scheme_name && <p style={{ fontSize:12, fontWeight:500, color, margin:0, opacity:0.9 }}>{notif.scheme_name}</p>}
      <div style={{ display:"flex", flexWrap:"wrap", gap:5 }}>
        <Tag label="ID"     value={notif.scheme_id}              color={color} />
        <Tag label="Lang"   value={notif.language}               color={color} />
        <Tag label="Vector" value={notif.dependency_vector_used} color={color} />
      </div>
      {notif.relevance_rationale && (
        <p style={{ fontSize:11, color:"var(--muted)", fontStyle:"italic", lineHeight:1.5, margin:0, opacity:0.8 }}>↳ {notif.relevance_rationale}</p>
      )}
    </div>
  )
}

// ── METADATA TABLE ────────────────────────────────────────────────────────────

const MetaTable = ({ profile }) => {
  const rows = Object.entries(profile).filter(([,v]) => v)
  return (
    <div style={{ background:"var(--card)", border:"1px solid var(--border)", borderRadius:10, overflow:"hidden" }}>
      <div style={{ padding:"9px 16px", background:"var(--surface)", borderBottom:"1px solid var(--border)", fontSize:11, fontWeight:500, letterSpacing:1, color:"var(--muted)", textTransform:"uppercase" }}>
        User Profile
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr" }}>
        {rows.map(([k,v],i) => (
          <div key={k} style={{ display:"flex", flexDirection:"column", gap:2, padding:"9px 16px", borderBottom: i<rows.length-2?"1px solid var(--border)":"none", borderRight: i%2===0?"1px solid var(--border)":"none" }}>
            <span style={{ fontSize:11, color:"var(--muted)", letterSpacing:0.5, textTransform:"uppercase" }}>{k.replace(/_/g," ")}</span>
            <span style={{ fontSize:12, color:"var(--text)", fontWeight:400 }}>{String(v)||"—"}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Segments CARD (dashboard) ───────────────────────────────────────────────────

const SegmentsCard = ({ notif, userSegKey, globalSearch, onClick }) => {
  const sbKey    = notif.source_bucket || ""
  const colSeg   = SEG[sbKey] || {}
  const colColor = colSeg.color || "#4db8a0"
  const uSeg     = SEG[userSegKey] || {}
  const isHighlighted = globalSearch && String(notif.user_id).includes(globalSearch.trim())

  return (
    <div
      onClick={() => onClick(notif)}
      style={{
        background:"var(--card)", borderRadius:8,
        border:`1px solid ${isHighlighted ? colColor+"50" : "var(--border)"}`,
        padding:"11px 13px", cursor:"pointer",
        transition:"border-color 0.15s",
        boxShadow: isHighlighted ? `0 0 0 1px ${colColor}20` : "none",
        animation:"fadeUp 0.3s ease both",
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = colColor+"55"}
      onMouseLeave={e => e.currentTarget.style.borderColor = isHighlighted ? colColor+"50" : "var(--border)"}
    >
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:7 }}>
        <span style={{ fontFamily:"'DM Mono',monospace", fontSize:11, color:"var(--muted)" }}>{notif.user_id}</span>
        {uSeg.label && (
          <span style={{ fontSize:10, padding:"2px 6px", borderRadius:4, background:uSeg.color+"15", border:`1px solid ${uSeg.color}28`, color:uSeg.color, fontWeight:500 }}>
            {uSeg.icon} {uSeg.label}
          </span>
        )}
      </div>
      <p style={{ fontFamily:"'Syne',sans-serif", fontSize:13, fontWeight:600, color:"var(--text)", margin:"0 0 4px", lineHeight:1.3 }}>{notif.title || "—"}</p>
      <p style={{ fontSize:11, color:"var(--text)", opacity:0.62, margin:"0 0 8px", lineHeight:1.45 }}>{notif.body || ""}</p>
      <Divider />
      {notif.scheme_name && <p style={{ fontSize:11, fontWeight:500, color:colColor, margin:"0 0 4px", opacity:0.9 }}>{notif.scheme_name}</p>}
      <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
        <Tag label="Vector" value={notif.dependency_vector_used?.split(" ")[0]} color={colColor} />
        <Tag label="Lang"   value={notif.language}                              color={colColor} />
      </div>
    </div>
  )
}

// ── MODAL ─────────────────────────────────────────────────────────────────────

const Modal = ({ user, notif, onClose }) => {
  if (!notif) return null
  const sbKey = notif.source_bucket || ""
  const s     = SEG[sbKey] || {}
  const uSeg  = SEG[user?.segment_key] || {}
  return (
    <div onClick={onClose} style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.72)", backdropFilter:"blur(4px)", zIndex:100, display:"flex", alignItems:"center", justifyContent:"center", padding:24 }}>
      <div onClick={e => e.stopPropagation()} style={{ background:"var(--card)", border:"1px solid var(--border)", borderRadius:12, padding:"24px 28px", maxWidth:540, width:"100%", maxHeight:"80vh", overflowY:"auto", boxShadow:"0 8px 32px rgba(0,0,0,0.45)" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:16 }}>
          <div>
            <p style={{ fontSize:11, color:"var(--muted)", letterSpacing:0.3, margin:"0 0 6px" }}>User {notif.user_id} · Notification {notif.notification_number}</p>
            <div style={{ display:"flex", gap:5, flexWrap:"wrap" }}>
              {uSeg.label && <Pill color={uSeg.color}>{uSeg.icon} Primary: {uSeg.label}</Pill>}
              {s.label    && <Pill color={s.color}>{s.icon} Source: {s.label}</Pill>}
            </div>
          </div>
          <button onClick={onClose} style={{ background:"none", border:"none", color:"var(--muted)", fontSize:18, cursor:"pointer", lineHeight:1, padding:4, opacity:0.7 }}>×</button>
        </div>
        <p style={{ fontFamily:"'Syne',sans-serif", fontSize:18, fontWeight:600, color:"var(--text)", margin:"0 0 8px", lineHeight:1.35 }}>{notif.title}</p>
        <p style={{ fontSize:13, color:"var(--text)", lineHeight:1.65, margin:"0 0 16px", opacity:0.78 }}>{notif.body}</p>
        <Divider />
        <div style={{ display:"flex", flexDirection:"column", gap:10, marginTop:14 }}>
          {notif.scheme_name && (
            <div>
              <span style={{ fontSize:11, color:"var(--muted)", letterSpacing:0.5, textTransform:"uppercase" }}>Scheme</span>
              <p style={{ fontSize:13, fontWeight:500, color:s.color||"var(--accent)", margin:"3px 0 0" }}>{notif.scheme_name} <span style={{ fontWeight:400, opacity:0.5 }}>({notif.scheme_id})</span></p>
            </div>
          )}
          {notif.dependency_vector_used && (
            <div>
              <span style={{ fontSize:11, color:"var(--muted)", letterSpacing:0.5, textTransform:"uppercase" }}>Dependency Vector</span>
              <p style={{ fontSize:12, color:"var(--text)", margin:"3px 0 0", opacity:0.82 }}>{notif.dependency_vector_used}</p>
            </div>
          )}
          {notif.attention_strategy && (
            <div>
              <span style={{ fontSize:11, color:"var(--muted)", letterSpacing:0.5, textTransform:"uppercase" }}>Attention Strategy</span>
              <p style={{ fontSize:12, color:"var(--text)", margin:"3px 0 0", opacity:0.82 }}>{notif.attention_strategy}</p>
            </div>
          )}
          {notif.relevance_rationale && (
            <div>
              <span style={{ fontSize:11, color:"var(--muted)", letterSpacing:0.5, textTransform:"uppercase" }}>Rationale</span>
              <p style={{ fontSize:12, color:"var(--muted)", fontStyle:"italic", lineHeight:1.5, margin:"3px 0 0" }}>{notif.relevance_rationale}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Segments COLUMN ─────────────────────────────────────────────────────────────

const SegmentsColumn = ({ segKey, allNotifs, userMap, globalSearch, primaryFilter }) => {
  const s = SEG[segKey]
  const [colSearch, setColSearch] = useState("")
  const [sort, setSort]           = useState("latest")
  const [modal, setModal]         = useState(null)

  const normBucket = (v) => (v||"").toLowerCase().trim().replace(/[\s-]+/g,"_")

  const colNotifs = useMemo(() => {
    let items = allNotifs.filter(n => normBucket(n.source_bucket) === segKey)
    if (globalSearch.trim()) items = items.filter(n => String(n.user_id).includes(globalSearch.trim()))
    if (colSearch.trim())    items = items.filter(n => String(n.user_id).includes(colSearch.trim()))
    if (primaryFilter !== "all") items = items.filter(n => userMap[String(n.user_id)] === primaryFilter)
    items = [...items].sort((a,b) => {
      if (sort === "latest")  return (b._ts||0) - (a._ts||0)
      if (sort === "oldest")  return (a._ts||0) - (b._ts||0)
      if (sort === "id_asc")  return String(a.user_id).localeCompare(String(b.user_id))
      if (sort === "id_desc") return String(b.user_id).localeCompare(String(a.user_id))
      return 0
    })
    return items
  }, [allNotifs, colSearch, sort, primaryFilter, segKey, userMap, globalSearch])

  const modalUser = modal ? { segment_key: userMap[String(modal.user_id)] } : null

  return (
    <div style={{ flex:1, minWidth:0, display:"flex", flexDirection:"column", gap:0 }}>
      {/* col header */}
      <div style={{ background:"var(--surface)", border:"1px solid var(--border)", borderBottom:"none", borderRadius:"10px 10px 0 0", padding:"12px 14px" }}>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:3 }}>
          <div style={{ display:"flex", alignItems:"center", gap:7 }}>
            <span style={{ fontSize:16 }}>{s.icon}</span>
            <span style={{ fontFamily:"'Syne',sans-serif", fontSize:13, fontWeight:600, color:s.color }}>{s.label}</span>
          </div>
          <span style={{ fontSize:11, fontWeight:500, color:s.color, background:s.color+"15", border:`1px solid ${s.color}25`, padding:"2px 8px", borderRadius:4 }}>{colNotifs.length}</span>
        </div>
        <p style={{ fontSize:11, color:"var(--muted)", margin:0 }}>{s.resp} responsive</p>
      </div>

      {/* col controls */}
      <div style={{ background:"var(--surface)", borderLeft:"1px solid var(--border)", borderRight:"1px solid var(--border)", padding:"7px 10px", display:"flex", flexDirection:"column", gap:5 }}>
        <input
          value={colSearch}
          onChange={e => setColSearch(e.target.value)}
          placeholder="Search user ID..."
          style={{ width:"100%", padding:"6px 10px", background:"var(--card)", border:"1px solid var(--border)", borderRadius:5, color:"var(--text)", fontSize:11, fontFamily:"'DM Mono',monospace", outline:"none", boxSizing:"border-box" }}
          onFocus={e => e.target.style.borderColor = s.color+"60"}
          onBlur={e  => e.target.style.borderColor = "var(--border)"}
        />
        <select value={sort} onChange={e => setSort(e.target.value)} style={{ padding:"5px 8px", background:"var(--card)", border:"1px solid var(--border)", borderRadius:5, color:"var(--muted)", fontSize:11, cursor:"pointer", outline:"none" }}>
          <option value="latest">Latest first</option>
          <option value="oldest">Oldest first</option>
          <option value="id_asc">ID A→Z</option>
          <option value="id_desc">ID Z→A</option>
        </select>
      </div>

      {/* cards */}
      <div style={{
        flex:1, overflowY:"auto", display:"flex", flexDirection:"column", gap:6,
        padding:"8px 8px", background:"var(--surface)",
        border:"1px solid var(--border)", borderTop:"none", borderRadius:"0 0 10px 10px",
        minHeight:200, maxHeight:"calc(100vh - 360px)",
      }}>
        {colNotifs.length === 0
          ? <p style={{ color:"var(--muted)", fontSize:11, textAlign:"center", padding:24 }}>No notifications</p>
          : colNotifs.map((n,i) => (
            <SegmentsCard
              key={`${n.user_id}-${n.notification_number}`}
              notif={n}
              userSegKey={userMap[String(n.user_id)] || ""}
              globalSearch={globalSearch}
              onClick={setModal}
            />
          ))
        }
      </div>

      {modal && <Modal user={modalUser} notif={modal} onClose={() => setModal(null)} />}
    </div>
  )
}

// ── USER LIST PANEL ──────────────────────────────────────────────────────────────

const UserListPanel = ({ records }) => {
  const [segFilter, setSegFilter] = useState("all")
  const [search,    setSearch]    = useState("")

  const filtered = useMemo(() => records.filter(u => {
    const matchSeg = segFilter === "all" || u.segment_key === segFilter
    const matchQ   = !search.trim() || String(u.user_id).includes(search.trim())
    return matchSeg && matchQ
  }), [records, segFilter, search])

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
      <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search user ID..."
        style={{ padding:"8px 14px", background:"var(--surface)", border:"1px solid var(--border)", borderRadius:8, color:"var(--text)", fontSize:12, fontFamily:"'DM Mono',monospace", outline:"none", marginBottom:8, width:"100%", boxSizing:"border-box" }}
        onFocus={e=>e.target.style.borderColor="var(--accent)"} onBlur={e=>e.target.style.borderColor="var(--border)"} />
      <div style={{ display:"flex", flexWrap:"wrap", gap:5, marginBottom:10 }}>
        {[["all","All","#64748b"],...Object.entries(SEG).map(([k,s])=>[k,s.icon+" "+s.label,s.color])].map(([key,label,color])=>(
          <button key={key} onClick={()=>setSegFilter(key)} style={{ padding:"3px 10px", borderRadius:4, fontSize:11, fontWeight:500, cursor:"pointer", border:`1px solid ${segFilter===key?color+"55":"var(--border)"}`, background:segFilter===key?color+"15":"transparent", color:segFilter===key?color:"var(--muted)" }}>{label}</button>
        ))}
      </div>
      <p style={{ fontSize:11, color:"var(--muted)", margin:"0 0 8px" }}>{filtered.length} users</p>
      <div style={{ display:"flex", flexDirection:"column", gap:0, maxHeight:400, overflowY:"auto", borderRadius:8, border:"1px solid var(--border)" }}>
        {filtered.length === 0
          ? <p style={{ padding:16, color:"var(--muted)", fontSize:11, textAlign:"center" }}>No users found</p>
          : filtered.map((u,i) => {
            const s = SEG[u.segment_key] || {}
            return (
              <div key={u.user_id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"9px 14px", background: i%2===0?"var(--surface)":"var(--card)", borderBottom: i<filtered.length-1?"1px solid var(--border)":"none" }}>
                <span style={{ fontFamily:"'DM Mono',monospace", fontSize:12, color:"var(--text)" }}>{u.user_id}</span>
                <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <span style={{ fontSize:11, color:"var(--muted)" }}>{u.notifications?.length||0} notifs</span>
                  <span style={{ fontSize:11, color:"var(--muted)" }}>{u.generated_at ? new Date(u.generated_at).toLocaleDateString() : ""}</span>
                  <span style={{ fontSize:11, padding:"2px 8px", borderRadius:4, background:s.color+"15", border:`1px solid ${s.color}28`, color:s.color, fontWeight:500 }}>{s.icon} {s.label}</span>
                </div>
              </div>
            )
          })
        }
      </div>
    </div>
  )
}

// ── DASHBOARD TAB ─────────────────────────────────────────────────────────────

const Dashboard = ({ records, onRefresh, loading }) => {
  const [globalSearch,  setGlobalSearch]  = useState("")
  const [primaryFilter, setPrimaryFilter] = useState("all")
  const [view,          setView]          = useState("Segments")

  const { allNotifs, userMap } = useMemo(() => {
    const map = {}; const flat = []
    records.forEach(u => {
      map[String(u.user_id)] = u.segment_key
      const ts = u.generated_at ? new Date(u.generated_at).getTime() : 0
      u.notifications.forEach(n => flat.push({ ...n, user_id: u.user_id, _ts: ts }))
    })
    return { allNotifs: flat, userMap: map }
  }, [records])

  return (
    <div>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16, flexWrap:"wrap", gap:10 }}>
        <div>
          <h2 style={{ fontFamily:"'Syne',sans-serif", fontSize:14, fontWeight:600, letterSpacing:0.8, color:"var(--text)", textTransform:"uppercase", margin:"0 0 3px" }}>Notification Logs</h2>
          <p style={{ fontSize:11, color:"var(--muted)", margin:0 }}>{records.length} users · {allNotifs.length} notifications across 5 buckets</p>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <div style={{ display:"flex", background:"var(--surface)", border:"1px solid var(--border)", borderRadius:6, overflow:"hidden" }}>
            {[["Segments","Segments"],["list","User List"]].map(([key,label])=>(
              <button key={key} onClick={()=>setView(key)} style={{ padding:"6px 14px", fontSize:11, fontWeight:500, cursor:"pointer", border:"none", background:view===key?"var(--accent)":"transparent", color:view===key?"#070810":"var(--muted)", fontFamily:"'Syne',sans-serif" }}>{label}</button>
            ))}
          </div>
          <button onClick={onRefresh} disabled={loading} style={{ padding:"6px 14px", borderRadius:6, fontSize:11, background:"var(--surface)", border:"1px solid var(--border)", color:"var(--muted)", cursor:"pointer", fontFamily:"'DM Mono',monospace" }}>{loading?"…":"↻ Refresh"}</button>
        </div>
      </div>

      {view === "list" && <UserListPanel records={records} />}

      {view === "Segments" && <>
        <input value={globalSearch} onChange={e=>setGlobalSearch(e.target.value)}
          placeholder="Search user ID — filters all 5 columns simultaneously..."
          style={{ width:"100%", padding:"9px 14px", background:"var(--surface)", border:"1px solid var(--border)", borderRadius:8, color:"var(--text)", fontSize:12, fontFamily:"'DM Mono',monospace", outline:"none", marginBottom:10, boxSizing:"border-box", transition:"border 0.15s" }}
          onFocus={e=>e.target.style.borderColor="var(--accent)"} onBlur={e=>e.target.style.borderColor="var(--border)"} />
        <div style={{ display:"flex", flexWrap:"wrap", gap:6, marginBottom:18 }}>
          {[["all","All Users","#64748b"],...SEG_KEYS.map(k=>[k,SEG[k].label,SEG[k].color])].map(([key,label,color])=>(
            <button key={key} onClick={()=>setPrimaryFilter(key)} style={{ padding:"4px 12px", borderRadius:5, fontSize:11, fontWeight:500, cursor:"pointer", transition:"all 0.15s", border:`1px solid ${primaryFilter===key?color+"55":"var(--border)"}`, background:primaryFilter===key?color+"15":"var(--surface)", color:primaryFilter===key?color:"var(--muted)" }}>
              {key!=="all"&&SEG[key]?.icon+" "}{label}
            </button>
          ))}
          <span style={{ fontSize:11, color:"var(--muted)", alignSelf:"center", opacity:0.6 }}>← primary segment</span>
        </div>
        <div style={{ display:"flex", gap:10, alignItems:"flex-start", overflowX:"auto", paddingBottom:8 }}>
          {SEG_KEYS.map(k=>(
            <SegmentsColumn key={k} segKey={k} allNotifs={allNotifs} userMap={userMap} globalSearch={globalSearch} primaryFilter={primaryFilter} />
          ))}
        </div>
      </>}
    </div>
  )
}

// ── GENERATE TAB ──────────────────────────────────────────────────────────────

const GenerateTab = ({ onNewData }) => {
  const [userId, setUserId]   = useState("")
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState("")
  const [data,    setData]    = useState(null)

  async function handleSearch() {
    if (!userId.trim()) return
    setLoading(true); setError(""); setData(null)
    try {
      const res = await fetch(`${API_BASE}/notify/${userId.trim()}`)
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Server error") }
      const json = await res.json()
      setData(json)
      onNewData()
    } catch(e) { setError(e.message) }
    finally { setLoading(false) }
  }

  return (
    <div>
      <div style={{ display:"flex", gap:10, marginBottom:28 }}>
        <input
          value={userId}
          onChange={e => setUserId(e.target.value)}
          onKeyDown={e => e.key==="Enter" && handleSearch()}
          placeholder="Enter user_id  e.g. 208135"
          style={{ flex:1, padding:"11px 16px", background:"var(--surface)", border:"1px solid var(--border)", borderRadius:8, color:"var(--text)", fontSize:14, fontFamily:"'DM Mono',monospace", outline:"none", transition:"border 0.15s" }}
          onFocus={e => e.target.style.borderColor = "var(--accent)"}
          onBlur={e  => e.target.style.borderColor = "var(--border)"}
        />
        <button onClick={handleSearch} disabled={loading} style={{ padding:"11px 22px", borderRadius:8, background: loading ? "var(--surface)" : "var(--accent)", color: loading ? "var(--muted)" : "#070810", border:"none", cursor: loading ? "not-allowed" : "pointer", fontFamily:"'Syne',sans-serif", fontWeight:600, fontSize:13, letterSpacing:0.3 }}>
          {loading ? "…" : "Generate →"}
        </button>
      </div>

      {error && <div style={{ padding:"10px 14px", borderRadius:8, background:"rgba(127,29,29,0.18)", border:"1px solid rgba(239,68,68,0.28)", color:"#fca5a5", fontSize:12, marginBottom:20 }}>{error}</div>}
      {loading && <Loader />}

      {data && !loading && (
        <div style={{ display:"flex", flexDirection:"column", gap:22 }}>
          <p style={{ fontSize:11, color:"var(--muted)", margin:0 }}>User {data.user_id} · {new Date(data.generated_at).toLocaleString()}</p>
          {data.user_segment && <div>
            <p style={{ fontSize:11, letterSpacing:1, color:"var(--muted)", textTransform:"uppercase", margin:"0 0 10px" }}>User Segment</p>
            <SegmentCard segment={data.user_segment} />
          </div>}
          <div>
            <p style={{ fontSize:11, letterSpacing:1, color:"var(--muted)", textTransform:"uppercase", margin:"0 0 12px" }}>5 Notifications</p>
            <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
              {data.notifications.map((n,i) => <NotifCard key={n.notification_number} notif={n} index={i} />)}
            </div>
          </div>
          <div>
            <p style={{ fontSize:11, letterSpacing:1, color:"var(--muted)", textTransform:"uppercase", margin:"0 0 10px" }}>User Metadata</p>
            <MetaTable profile={data.user_profile} />
          </div>
        </div>
      )}
    </div>
  )
}

// ── APP ROOT ──────────────────────────────────────────────────────────────────

export default function App() {
  const [tab,       setTab]       = useState("generate")
  const [dashboard, setDashboard] = useState([])
  const [dbLoading, setDbLoading] = useState(false)

  useEffect(() => { loadDashboard() }, [])

  async function loadDashboard() {
    setDbLoading(true)
    try {
      const res = await fetch(`${API_BASE}/dashboard`)
      if (res.ok) setDashboard(await res.json())
    } catch(e) { console.warn("Dashboard failed:", e) }
    finally { setDbLoading(false) }
  }

  return (
    <div style={{ maxWidth:1200, margin:"0 auto", padding:"36px 24px" }}>

      {/* HEADER */}
      <div style={{ marginBottom:36, paddingBottom:24, borderBottom:"1px solid var(--border)" }}>
        <p style={{ fontSize:11, letterSpacing:2, color:"var(--accent)", margin:"0 0 8px", opacity:0.85 }}>NOTIFICATION ENGINE</p>
        <h1 style={{ fontFamily:"'Syne',sans-serif", fontSize:"clamp(22px,3vw,34px)", fontWeight:600, color:"var(--text)", lineHeight:1.2, margin:0 }}>
          Personalized Government Alerts
        </h1>
      </div>

      {/* TABS */}
      <div style={{ display:"flex", gap:2, marginBottom:32, background:"var(--surface)", padding:3, borderRadius:8, border:"1px solid var(--border)", width:"fit-content" }}>
        {[["generate","Generate"],["dashboard","Dashboard"]].map(([key,label]) => (
          <button key={key} onClick={() => setTab(key)} style={{
            padding:"7px 18px", borderRadius:6, fontSize:12, fontWeight:500,
            cursor:"pointer", border:"none", transition:"all 0.15s",
            background: tab===key ? "var(--accent)" : "transparent",
            color:       tab===key ? "#070810"       : "var(--muted)",
            fontFamily: "'Syne',sans-serif",
            letterSpacing: 0.3,
          }}>{label}</button>
        ))}
      </div>

      {tab === "generate"
        ? <GenerateTab onNewData={loadDashboard} />
        : <Dashboard records={dashboard} onRefresh={loadDashboard} loading={dbLoading} />
      }

      <style>{`
        @keyframes spin   { to { transform:rotate(360deg); } }
        @keyframes fadeUp { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
        input::placeholder { color:var(--muted); opacity:0.45; }
        select option { background:var(--surface); }
        * { -webkit-font-smoothing:antialiased; }
        ::-webkit-scrollbar { width:3px; height:3px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:var(--border); border-radius:99px; }
        ::-webkit-scrollbar-thumb:hover { background:var(--muted); }
      `}</style>
    </div>
  )
}
