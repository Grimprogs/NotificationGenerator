import { useState, useEffect, useMemo, useCallback } from "react"
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom"

const API_BASE       = import.meta.env.VITE_API_URL || "http://localhost:8000"
const GEMINI_KEY     = import.meta.env.VITE_GEMINI_KEY || ""
const SUPABASE_URL   = import.meta.env.VITE_SUPABASE_URL || ""
const SUPABASE_KEY   = import.meta.env.VITE_SUPABASE_KEY || ""
const IMAGEN_URL     = `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image:generateContent`

// ── IMAGE HELPERS ─────────────────────────────────────────────────────────────

const SEG_THEMES = {
  job_hunter:       "a confident Indian person succeeding in a job interview, shaking hands with employer, professional office",
  scheme_seeker:    "a happy Indian family feeling financially secure, smiling at home, receiving government support",
  content_reader:   "a young Indian student reading and learning, bright study room, digital access, knowledge growth",
  high_converter:   "a proud Indian small business owner growing their business, colourful shop, happy customers",
  service_explorer: "an Indian person completing a skill training certification, training center, holding certificate proudly",
}

const AMI_LOGO = "https://www.axismyindia.org/assets/images/logo.png"

async function generateCampaignImage(notif, segKey, userProfile = null) {
  const theme = SEG_THEMES[segKey] || "a positive Indian family achieving their goals, happy and confident"
  
  let profileContext = ""
  if (userProfile) {
    profileContext = `Subject details: Name: ${userProfile.name}, Age: ${userProfile.age}. Occupation: ${userProfile.occupation_id} (or related field).
Based on the name and age, infer their gender and life stage. If it's a male name, feature a male protagonist. If they are older, show them as a family man/woman surrounded by their family. Ensure there are multiple people in the scene so it feels warm and populated, not isolated. Make sure the occupation attire matches.`
  }

  const prompt = `Create a highly creative, photorealistic campaign image for Axis My India.

Format: Landscape 16:9 ratio, horizontal orientation.

Scene: A realistic, emotional Indian scene. The protagonist is working hard, perhaps feeling stressed about their income or slightly homesick, but hoping for a better future through government support.
Theme: ${theme}
Scheme: ${notif.scheme_name}.
${profileContext}

Text Overlay:
- Beautifully integrate this text into the image (in a clean space):
  "${notif.title} - ${notif.body}"
- CRITICAL TYPOGRAPHY RULE: If the text is in Hindi or a regional language, you MUST render the characters perfectly and accurately without hallucinating symbols.

Visual design:
- Focus entirely on the cinematic, realistic human subjects and their environment.
- Professional photography style, highly detailed.
- Color palette: deep purple #7c3aed, white, saffron orange accents subtly integrated.
- Clean white bottom strip (15% of image height) for branding.

Branding (bottom of image):
- Include the Axis My India logo in bottom-left corner: the word "axis" in purple italic font, below it two colored blocks side by side — left block is orange/red with bold white text "MY", right block is green with grass texture and bold white text "INDIA", below both blocks small text "Since 1998"
- Small tagline: "Empowering India, One Citizen at a Time"

Rules:
- No political imagery. No government leader photos.
- High resolution, crisp, premium cinematic feel.`

  const res = await fetch(`${IMAGEN_URL}?key=${GEMINI_KEY}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { responseModalities: ["IMAGE", "TEXT"] },
    })
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data?.error?.message || "Gemini error")
  const parts = data?.candidates?.[0]?.content?.parts || []
  const imgPart = parts.find(p => p.inlineData)
  if (!imgPart) throw new Error("No image in response")
  return imgPart.inlineData.data // base64 string
}

async function saveImageToSupabase(notifId, imgB64) {
  // Update the generated_notifications row with the saved image
  const res = await fetch(
    `${SUPABASE_URL}/rest/v1/generated_notifications?id=eq.${notifId}`,
    {
      method: "PATCH",
      headers: {
        "apikey": SUPABASE_KEY,
        "Authorization": `Bearer ${SUPABASE_KEY}`,
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
      },
      body: JSON.stringify({ campaign_image: imgB64 })
    }
  )
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err)
  }
}

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

const RationaleBox = ({ rationale, title = "Why this notification?" }) => {
  if (!rationale) return null;
  let items = [];
  try {
    // If it's a stringified JSON array from DB (e.g. '["- point 1", "- point 2"]')
    if (typeof rationale === 'string' && rationale.trim().startsWith('[')) {
      items = JSON.parse(rationale);
    } else if (Array.isArray(rationale)) {
      items = rationale;
    } else {
      items = String(rationale).split('\n');
    }
  } catch (e) {
    items = String(rationale).split('\n');
  }
  
  items = items.filter(line => typeof line === 'string' && line.trim() !== '');

  return (
    <div style={{ marginTop: 8, padding: "8px 12px", background: "var(--surface)", borderRadius: 6, border: "1px solid var(--border)" }}>
      <p style={{ fontSize:10, fontWeight:600, color:"var(--muted)", textTransform:"uppercase", letterSpacing:0.5, margin:"0 0 6px" }}>{title}</p>
      <ul style={{ margin:0, paddingLeft:16, fontSize:11, color:"var(--muted)", lineHeight:1.5, opacity:0.9 }}>
        {items.map((line, i) => (
          <li key={i} style={{ marginBottom: i !== items.length-1 ? 4 : 0 }}>
            {line.replace(/^[-*•\s]+/, '')}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ── IMAGE PANEL ───────────────────────────────────────────────────────────────

const ImagePanel = ({ notif, segKey, compact = false, userProfile = null }) => {
  const existing = notif.campaign_image || null
  const [versions,   setVersions]   = useState(existing ? [existing] : [])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState(null)
  // saved = true if this version is persisted in Supabase
  const [saved,      setSaved]      = useState(!!existing)
  const color = SEG[segKey]?.color || "#6b21a8"

  const currentImg = versions[currentIdx] || null
  const notifId    = notif.id || null

  const generate = async (e) => {
    e.stopPropagation()
    setLoading(true)
    setError(null)
    setSaved(false)
    try {
      const b64 = await generateCampaignImage(notif, segKey, userProfile)
      setVersions(prev => {
        const next = [...prev, b64]
        setCurrentIdx(next.length - 1)  // always show the newest
        return next
      })
    } catch(err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const save = async (e) => {
    e.stopPropagation()
    if (!currentImg) return
    if (!notifId) {
      setError("No notification ID — regenerate notifications first")
      return
    }
    try {
      await saveImageToSupabase(notifId, currentImg)
      setSaved(true)
      setError(null)
    } catch(err) {
      setError("Save failed: " + err.message)
    }
  }

  // Compact mode: show just a small button until first image is generated
  if (compact && versions.length === 0 && !loading) return (
    <div style={{ marginTop:8 }} onClick={e => e.stopPropagation()}>
      <button onClick={generate} style={{ padding:"6px 14px", borderRadius:6, background:color+"15", border:`1px solid ${color}30`, color, cursor:"pointer", fontSize:11, fontFamily:"'Inter',sans-serif", fontWeight:600 }}>
        ✨ Generate Campaign Image
      </button>
      {error && <p style={{ color:"#ef4444", fontSize:10, margin:"4px 0 0" }}>⚠ {error}</p>}
    </div>
  )

  return (
    <div style={{ marginTop: compact ? 8 : 24, background:"var(--surface)", border:"1px solid var(--border)", borderRadius:10, padding: compact ? "12px" : "20px" }} onClick={e => e.stopPropagation()}>
      {/* Header row */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom: currentImg ? 12 : 8 }}>
        <div>
          <p style={{ fontSize:12, fontWeight:600, color:"var(--text)", margin:0, fontFamily:"'Inter',sans-serif" }}>📸 Campaign Visual</p>
          <p style={{ fontSize:10, color:"var(--muted)", margin:"2px 0 0" }}>
            {saved && !loading ? "✓ Saved to Supabase" : versions.length > 0 ? `${versions.length} version${versions.length > 1 ? "s" : ""}` : "Ready to generate"}
          </p>
        </div>
        <div style={{ display:"flex", gap:6, alignItems:"center" }}>
          {/* Save button: show when image exists, NOT yet saved, AND we have a valid notifId */}
          {currentImg && !saved && notifId && (
            <button onClick={save} style={{ padding:"5px 14px", borderRadius:6, background:"#16a34a", color:"#fff", border:"none", cursor:"pointer", fontSize:11, fontFamily:"'Inter',sans-serif", fontWeight:600, display:"flex", alignItems:"center", gap:4 }}>
              💾 Save
            </button>
          )}
          {/* Replace button: show when already saved, we have a new version, AND valid notifId */}
          {currentImg && saved && versions.length > 1 && versions[currentIdx] !== existing && notifId && (
            <button onClick={save} style={{ padding:"5px 14px", borderRadius:6, background:"#d97706", color:"#fff", border:"none", cursor:"pointer", fontSize:11, fontFamily:"'Inter',sans-serif", fontWeight:600 }}>
              🔄 Replace
            </button>
          )}
          {currentImg && saved && (versions.length <= 1 || versions[currentIdx] === existing) && notifId && (
            <span style={{ fontSize:10, color:"#16a34a", fontWeight:600, padding:"3px 8px", background:"#16a34a15", borderRadius:4, border:"1px solid #16a34a30" }}>✓ Saved</span>
          )}
          {/* Generate / Regenerate button */}
          <button onClick={generate} disabled={loading} style={{ padding:"5px 12px", borderRadius:6, background: loading ? "var(--surface)" : color, color: loading ? "var(--muted)" : "#fff", border:`1px solid ${loading ? "var(--border)" : color}`, cursor: loading ? "not-allowed" : "pointer", fontSize:11, fontFamily:"'Inter',sans-serif", fontWeight:600, display:"flex", alignItems:"center", gap:5 }}>
            {loading
              ? <><div style={{ width:9, height:9, borderRadius:"50%", border:"1.5px solid transparent", borderTop:`1.5px solid ${color}`, animation:"spin 0.7s linear infinite" }}/> Generating…</>
              : currentImg ? "↺ New Version" : "✨ Generate"
            }
          </button>
        </div>
      </div>


      {error && <p style={{ color:"#ef4444", fontSize:11, margin:"0 0 8px" }}>⚠ {error}</p>}

      {/* Image display */}
      {currentImg && (
        <div>
          <img
            src={`data:image/png;base64,${currentImg}`}
            alt="Campaign visual"
            style={{ width:"100%", borderRadius:8, border:"1px solid var(--border)", display:"block" }}
            onError={e => { e.target.src = `data:image/jpeg;base64,${currentImg}` }}
          />
          {/* Version dots */}
          {versions.length > 1 && (
            <div style={{ display:"flex", gap:6, marginTop:10, justifyContent:"center" }}>
              {versions.map((_, i) => (
                <button key={i} onClick={e => { e.stopPropagation(); setCurrentIdx(i); setSaved(false) }}
                  style={{ width:8, height:8, borderRadius:"50%", border:"none", cursor:"pointer", padding:0, background: currentIdx === i ? color : "var(--border)", transition:"background 0.15s" }}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {!currentImg && !loading && (
        <div style={{ textAlign:"center", padding:"20px 0", color:"var(--muted)", fontSize:11 }}>
          <div style={{ fontSize:28, marginBottom:6, opacity:0.2 }}>🖼</div>
          Click Generate to create a personalized campaign image
        </div>
      )}

      {loading && (
        <div style={{ textAlign:"center", padding:"20px 0", color:"var(--muted)", fontSize:11 }}>
          <div style={{ width:20, height:20, borderRadius:"50%", border:"2px solid var(--border)", borderTop:`2px solid ${color}`, animation:"spin 0.8s linear infinite", margin:"0 auto 8px" }} />
          Generating your campaign image…
        </div>
      )}
    </div>
  )
}

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
      boxShadow:"0 2px 8px rgba(0,0,0,0.05)",
    }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <div style={{ width:38, height:38, borderRadius:8, background:color+"15", border:`1px solid ${color}22`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:17 }}>{s.icon}</div>
          <div>
            <div style={{ display:"flex", alignItems:"center", gap:8 }}>
              <p style={{ fontFamily:"'Inter',sans-serif", fontSize:15, fontWeight:600, color:"var(--text)", margin:0 }}>{label}</p>
              {is_best && <Pill color={color}>Best Segment</Pill>}
            </div>
            <p style={{ fontSize:11, color:"var(--muted)", margin:"3px 0 0" }}>{notification_responsive} notification responsive</p>
          </div>
        </div>
        <span style={{ fontFamily:"'Inter',sans-serif", fontSize:22, fontWeight:600, color }}>{segment_pct}</span>
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
  const navigate = useNavigate()
  const sbKey = notif.source_bucket || ""
  const s     = SEG[sbKey] || {}
  const color = s.color || "#4db8a0"
  return (
    <div style={{
      background:"var(--card)", border:"1px solid var(--border)",
      borderTop:`2px solid ${color}55`, borderRadius:10, padding:"16px 20px",
      display:"flex", flexDirection:"column", gap:10,
      animation:`fadeUp 0.3s ease ${index*0.05}s both`,
      boxShadow:"0 2px 6px rgba(0,0,0,0.04)",
    }}>
      {/* Clickable top section navigates to scheme details */}
      <div onClick={() => navigate(`/scheme/${notif.scheme_id}`, { state: notif })} style={{ cursor:"pointer", transition:"all 0.2s" }}
        onMouseEnter={e => { e.currentTarget.style.opacity = "0.85" }}
        onMouseLeave={e => { e.currentTarget.style.opacity = "1" }}
      >
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
          <span style={{ fontSize:11, color:"var(--muted)", letterSpacing:0.3 }}>Notification {notif.notification_number} <span style={{ fontSize:10, opacity:0.5 }}>— click to view details</span></span>
          <div style={{ display:"flex", gap:5, alignItems:"center" }}>
            {sbKey && <Pill color={color}>{s.icon} {s.label}</Pill>}
            {notif.attention_strategy && <Pill color="#48566a" outline>{notif.attention_strategy}</Pill>}
          </div>
        </div>
        <p style={{ fontFamily:"'Inter',sans-serif", fontSize:16, fontWeight:600, color:"var(--text)", lineHeight:1.35, margin:0 }}>{notif.title}</p>
        <p style={{ fontSize:13, color:"var(--text)", lineHeight:1.65, opacity:0.72, margin:"6px 0 0" }}>{notif.body}</p>
        <Divider />
        {notif.scheme_name && <p style={{ fontSize:12, fontWeight:500, color, margin:0, opacity:0.9 }}>{notif.scheme_name}</p>}
        <div style={{ display:"flex", flexWrap:"wrap", gap:5, marginTop:4 }}>
          <Tag label="ID"     value={notif.scheme_id}              color={color} />
          <Tag label="Lang"   value={notif.language}               color={color} />
          <Tag label="Vector" value={notif.dependency_vector_used} color={color} />
        </div>
        {notif.relevance_rationale && <RationaleBox rationale={notif.relevance_rationale} />}
      </div>
      {/* Image panel — does NOT navigate */}
      <ImagePanel notif={notif} segKey={sbKey} compact />
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

const SegmentsCard = ({ notif, userSegKey, globalSearch }) => {
  const navigate = useNavigate()
  const sbKey    = notif.source_bucket || ""
  const colSeg   = SEG[sbKey] || {}
  const colColor = colSeg.color || "#4db8a0"
  const uSeg     = SEG[userSegKey] || {}
  const isHighlighted = globalSearch && String(notif.user_id).includes(globalSearch.trim())

  return (
    <div style={{
      background:"var(--card)", borderRadius:8,
      border:`1px solid ${isHighlighted ? colColor+"50" : "var(--border)"}`,
      padding:"11px 13px",
      transition:"border-color 0.15s",
      boxShadow: isHighlighted ? `0 0 0 1px ${colColor}20` : "none",
      animation:"fadeUp 0.3s ease both",
    }}>
      {/* Clickable card area — navigates to details */}
      <div
        onClick={() => navigate(`/scheme/${notif.scheme_id}`, { state: { ...notif, userSegKey } })}
        style={{ cursor:"pointer" }}
        onMouseEnter={e => e.currentTarget.style.opacity = "0.85"}
        onMouseLeave={e => e.currentTarget.style.opacity = "1"}
      >
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:7 }}>
          <span style={{ fontFamily:"'DM Mono',monospace", fontSize:11, color:"var(--muted)" }}>{notif.user_id}</span>
          {uSeg.label && (
            <span style={{ fontSize:10, padding:"2px 6px", borderRadius:4, background:uSeg.color+"15", border:`1px solid ${uSeg.color}28`, color:uSeg.color, fontWeight:500 }}>
              {uSeg.icon} {uSeg.label}
            </span>
          )}
        </div>
        <p style={{ fontFamily:"'Inter',sans-serif", fontSize:13, fontWeight:600, color:"var(--text)", margin:"0 0 4px", lineHeight:1.3 }}>{notif.title || "—"}</p>
        <p style={{ fontSize:11, color:"var(--text)", opacity:0.62, margin:"0 0 8px", lineHeight:1.45 }}>{notif.body || ""}</p>
        <Divider />
        {notif.scheme_name && <p style={{ fontSize:11, fontWeight:500, color:colColor, margin:"0 0 4px", opacity:0.9 }}>{notif.scheme_name}</p>}
        <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
          <Tag label="Vector" value={notif.dependency_vector_used?.split(" ")[0]} color={colColor} />
          <Tag label="Lang"   value={notif.language}                              color={colColor} />
        </div>
      </div>
      {/* Image panel — does NOT navigate */}
      <ImagePanel notif={notif} segKey={sbKey} compact />
    </div>
  )
}

// ── Segments COLUMN ─────────────────────────────────────────────────────────────

const SegmentsColumn = ({ segKey, allNotifs, userMap, globalSearch, primaryFilter }) => {
  const s = SEG[segKey]
  const [colSearch, setColSearch] = useState("")
  const [sort, setSort]           = useState("latest")
  

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

  

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:0 }}>
      {/* Controls bar */}
      <div style={{ display:"flex", gap:8, marginBottom:12, alignItems:"center", flexWrap:"wrap" }}>
        <input
          value={colSearch}
          onChange={e => setColSearch(e.target.value)}
          placeholder="Search user ID..."
          style={{ flex:1, minWidth:200, padding:"8px 12px", background:"var(--card)", border:"1px solid var(--border)", borderRadius:7, color:"var(--text)", fontSize:12, fontFamily:"'DM Mono',monospace", outline:"none", boxSizing:"border-box" }}
          onFocus={e => e.target.style.borderColor = s.color+"80"}
          onBlur={e  => e.target.style.borderColor = "var(--border)"}
        />
        <select value={sort} onChange={e => setSort(e.target.value)} style={{ padding:"8px 12px", background:"var(--card)", border:"1px solid var(--border)", borderRadius:7, color:"var(--muted)", fontSize:12, cursor:"pointer", outline:"none" }}>
          <option value="latest">Latest first</option>
          <option value="oldest">Oldest first</option>
          <option value="id_asc">ID A→Z</option>
          <option value="id_desc">ID Z→A</option>
        </select>
        <span style={{ fontSize:12, color:s.color, fontWeight:600, padding:"6px 14px", background:s.color+"12", border:`1px solid ${s.color}30`, borderRadius:7 }}>
          {colNotifs.length} results
        </span>
      </div>

      {/* Full-width card grid */}
      <div style={{
        display:"grid",
        gridTemplateColumns:"repeat(auto-fill, minmax(300px, 1fr))",
        gap:14,
        minHeight:200,
      }}>
        {colNotifs.length === 0
          ? <p style={{ color:"var(--muted)", fontSize:12, textAlign:"center", padding:40, gridColumn:"1/-1" }}>No notifications in this bucket</p>
          : colNotifs.map((n,i) => (
            <SegmentsCard
              key={`${n.user_id}-${n.notification_number}`}
              notif={n}
              userSegKey={userMap[String(n.user_id)] || ""}
              globalSearch={globalSearch}
            />
          ))
        }
      </div>
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
  const [activeBucket,  setActiveBucket]  = useState(SEG_KEYS[0])
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

  // Count per bucket for badges
  const bucketCounts = useMemo(() => {
    const counts = {}
    SEG_KEYS.forEach(k => {
      counts[k] = allNotifs.filter(n => (n.source_bucket||"").toLowerCase().trim().replace(/[\s-]+/g,"_") === k).length
    })
    return counts
  }, [allNotifs])

  return (
    <div>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:20, flexWrap:"wrap", gap:10 }}>
        <div>
          <h2 style={{ fontFamily:"'Inter',sans-serif", fontSize:14, fontWeight:600, letterSpacing:0.8, color:"var(--text)", textTransform:"uppercase", margin:"0 0 3px" }}>Notification Logs</h2>
          <p style={{ fontSize:11, color:"var(--muted)", margin:0 }}>{records.length} users · {allNotifs.length} notifications across 5 buckets</p>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <div style={{ display:"flex", background:"var(--surface)", border:"1px solid var(--border)", borderRadius:6, overflow:"hidden" }}>
            {[["Segments","Segments"],["list","User List"]].map(([key,label])=>(
              <button key={key} onClick={()=>setView(key)} style={{ padding:"6px 14px", fontSize:11, fontWeight:500, cursor:"pointer", border:"none", background:view===key?"var(--accent)":"transparent", color:view===key?"#ffffff":"var(--muted)", fontFamily:"'Inter',sans-serif" }}>{label}</button>
            ))}
          </div>
          <button onClick={onRefresh} disabled={loading} style={{ padding:"6px 14px", borderRadius:6, fontSize:11, background:"var(--surface)", border:"1px solid var(--border)", color:"var(--muted)", cursor:"pointer", fontFamily:"'DM Mono',monospace" }}>{loading?"…":"↻ Refresh"}</button>
        </div>
      </div>

      {view === "list" && <UserListPanel records={records} />}

      {view === "Segments" && <>
        {/* Global search */}
        <input value={globalSearch} onChange={e=>setGlobalSearch(e.target.value)}
          placeholder="Search user ID..."
          style={{ width:"100%", padding:"9px 14px", background:"var(--surface)", border:"1px solid var(--border)", borderRadius:8, color:"var(--text)", fontSize:12, fontFamily:"'DM Mono',monospace", outline:"none", marginBottom:16, boxSizing:"border-box", transition:"border 0.15s" }}
          onFocus={e=>e.target.style.borderColor="var(--accent)"} onBlur={e=>e.target.style.borderColor="var(--border)"} />

        {/* Bucket tabs */}
        <div style={{ display:"flex", gap:0, marginBottom:20, background:"var(--surface)", border:"1px solid var(--border)", borderRadius:10, overflow:"hidden" }}>
          {SEG_KEYS.map((k, idx) => {
            const s = SEG[k]
            const active = activeBucket === k
            return (
              <button key={k} onClick={() => setActiveBucket(k)} style={{
                flex:1, padding:"14px 8px", border:"none", borderRight: idx < SEG_KEYS.length-1 ? "1px solid var(--border)" : "none",
                cursor:"pointer", transition:"all 0.15s", fontFamily:"'Inter',sans-serif",
                background: active ? s.color+"12" : "transparent",
                borderBottom: active ? `3px solid ${s.color}` : "3px solid transparent",
              }}>
                <div style={{ fontSize:18, marginBottom:4 }}>{s.icon}</div>
                <div style={{ fontSize:11, fontWeight:600, color: active ? s.color : "var(--muted)", whiteSpace:"nowrap" }}>{s.label}</div>
                <div style={{ marginTop:4, fontSize:13, fontWeight:700, color: active ? s.color : "var(--text)" }}>{bucketCounts[k] || 0}</div>
                <div style={{ fontSize:10, color:"var(--muted)", opacity:0.7 }}>notifs</div>
              </button>
            )
          })}
        </div>

        {/* Full-page single bucket view */}
        <SegmentsColumn
          key={activeBucket}
          segKey={activeBucket}
          allNotifs={allNotifs}
          userMap={userMap}
          globalSearch={globalSearch}
          primaryFilter="all"
          fullPage
        />
      </>}
    </div>
  )
}


// ── SCHEME DETAILS PAGE ────────────────────────────────────────────────────────
const SchemeDetails = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const notification = location.state

  if (!notification) {
    return <div style={{ padding: 40, textAlign: "center", color: "var(--text)", fontFamily:"'Inter',sans-serif" }}>No data provided. <button onClick={() => navigate("/")}>Go back</button></div>
  }

  const sbKey = notification.source_bucket || ""
  const s     = SEG[sbKey] || {}
  const color = s.color || "var(--accent)"
  const uSeg  = SEG[notification.userSegKey || notification.user_segment?.segment_key] || {}

  const handleApply = () => {
    let url = notification.scheme_url
    if (!url && notification.scheme_name) {
      const initials = notification.scheme_name.split(' ').filter(w => w.trim()).map(w => w[0].toLowerCase()).join('')
      url = `https://www.myscheme.gov.in/schemes/${initials}`
    } else if (!url) {
      url = "https://www.myscheme.gov.in"
    }
    window.open(url, "_blank")
  }

  return (
    <div style={{ maxWidth: 760, margin: "0 auto", padding: "40px 24px" }}>
      <button onClick={() => navigate(-1)} style={{ background:"transparent", border:"none", color:"var(--muted)", cursor:"pointer", marginBottom: 24, fontSize: 13, display:"flex", alignItems:"center", gap: 6, padding:0, fontFamily:"'Inter',sans-serif" }}>
        <span>←</span> Back to Dashboard
      </button>

      <div style={{ background: "var(--card)", border: "1px solid var(--border)", borderTop: `4px solid ${color}`, borderRadius: 12, padding: "32px", boxShadow: "0 8px 32px rgba(0,0,0,0.06)" }}>
        
        <div style={{ marginBottom: 24 }}>
          <p style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: 1, margin: "0 0 6px", fontFamily:"'Inter',sans-serif" }}>Recommended Scheme</p>
          <h1 style={{ fontFamily: "'Inter',sans-serif", fontSize: 24, fontWeight: 600, color: "var(--text)", margin: 0 }}>{notification.scheme_name}</h1>
          <p style={{ fontSize: 13, color: "var(--muted)", margin: "4px 0 0", fontFamily:"'Inter',sans-serif" }}>ID: {notification.scheme_id}</p>
        </div>

        <Divider />

        <div style={{ padding: "20px 0" }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {sbKey && <Pill color={color}>{s.icon} {s.label}</Pill>}
            {uSeg.label && <Pill color={uSeg.color}>{uSeg.icon} User: {uSeg.label}</Pill>}
          </div>

          <h2 style={{ fontFamily: "'Inter',sans-serif", fontSize: 18, fontWeight: 600, color: "var(--text)", margin: "0 0 8px" }}>{notification.title}</h2>
          <p style={{ fontFamily: "'Inter',sans-serif", fontSize: 15, color: "var(--text)", lineHeight: 1.6, opacity: 0.85, margin: "0 0 20px" }}>{notification.body}</p>
        </div>

        <RationaleBox rationale={notification.relevance_rationale} title="Why this was recommended:" />

        <button onClick={handleApply} style={{ width: "100%", padding: "14px 24px", borderRadius: 8, background: "var(--accent)", color: "#ffffff", border: "none", cursor: "pointer", fontFamily: "'Inter',sans-serif", fontWeight: 600, fontSize: 15, transition: "opacity 0.2s" }} onMouseEnter={e => e.target.style.opacity = 0.9} onMouseLeave={e => e.target.style.opacity = 1}>
          Apply Now →
        </button>
      </div>

      {/* Shared AI Image Panel */}
      <ImagePanel notif={notification} segKey={sbKey} />
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
        <button onClick={handleSearch} disabled={loading} style={{ padding:"11px 22px", borderRadius:8, background: loading ? "var(--surface)" : "var(--accent)", color: loading ? "var(--muted)" : "#ffffff", border:"none", cursor: loading ? "not-allowed" : "pointer", fontFamily:"'Inter',sans-serif", fontWeight:600, fontSize:13, letterSpacing:0.3 }}>
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
              {data.notifications.map((n,i) => <NotifCard key={n.notification_number} notif={n} index={i} userProfile={data.user_profile} />)}
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

const Home = () => {
  const [tab,       setTab]       = useState(() => sessionStorage.getItem("homeTab") || "generate")
  const [dashboard, setDashboard] = useState([])
  const [dbLoading, setDbLoading] = useState(false)
  
  useEffect(() => { sessionStorage.setItem("homeTab", tab) }, [tab])
  
  // Theme toggle state
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark")

  useEffect(() => { loadDashboard() }, [])

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
    localStorage.setItem("theme", theme)
  }, [theme])

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
      <div style={{ marginBottom:36, paddingBottom:24, borderBottom:"1px solid var(--border)", display:"flex", justifyContent:"space-between", alignItems:"flex-start" }}>
        <div>
          <p style={{ fontSize:11, letterSpacing:2, color:"var(--accent)", margin:"0 0 8px", opacity:0.85 }}>NOTIFICATION ENGINE</p>
          <h1 style={{ fontFamily:"'Inter',sans-serif", fontSize:"clamp(22px,3vw,34px)", fontWeight:600, color:"var(--text)", lineHeight:1.2, margin:0 }}>
            Personalized Government Alerts
          </h1>
        </div>
        <button 
          onClick={() => setTheme(t => t === "light" ? "dark" : "light")}
          style={{
            padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)",
            background: "var(--surface)", color: "var(--text)", cursor: "pointer",
            fontWeight: 500, fontSize: 13, display:"flex", alignItems:"center", gap: 6
          }}
        >
          {theme === "light" ? "🌙 Dark Mode" : "☀️ Light Mode"}
        </button>
      </div>

      {/* TABS */}
      <div style={{ display:"flex", gap:2, marginBottom:32, background:"var(--surface)", padding:3, borderRadius:8, border:"1px solid var(--border)", width:"fit-content" }}>
        {[["generate","Generate"],["dashboard","Dashboard"]].map(([key,label]) => (
          <button key={key} onClick={() => setTab(key)} style={{
            padding:"7px 18px", borderRadius:6, fontSize:12, fontWeight:500,
            cursor:"pointer", border:"none", transition:"all 0.15s",
            background: tab===key ? "var(--accent)" : "transparent",
            color:       tab===key ? "#ffffff"       : "var(--muted)",
            fontFamily: "'Inter',sans-serif",
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

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/scheme/:schemeId" element={<SchemeDetails />} />
      </Routes>
    </BrowserRouter>
  )
}
