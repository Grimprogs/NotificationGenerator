# Graph Report - C:\anu\proj\Govttestingapp\Zeex-AMI-MVP  (2026-06-08)

## Corpus Check
- cluster-only mode - file stats not available

## Summary
- 96 nodes · 128 edges · 8 communities detected
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `main()` - 11 edges
2. `main()` - 10 edges
3. `get_notifications()` - 9 edges
4. `main()` - 6 edges
5. `get_sb()` - 5 edges
6. `fetch_user()` - 4 edges
7. `classify_segment()` - 3 edges
8. `resolve()` - 3 edges
9. `fetch_schemes()` - 3 edges
10. `save_to_supabase()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `resolve()` --calls--> `norm()`  [EXTRACTED]
  mvp_v2/mvp_v2/backend/main.py → backend/main.py
- `fetch_schemes()` --calls--> `get_sb()`  [EXTRACTED]
  backend/main.py → mvp_v2/mvp_v2/backend/main.py
- `get_notifications()` --calls--> `fetch_schemes()`  [EXTRACTED]
  mvp_v2/mvp_v2/backend/main.py → backend/main.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.2
Nodes (16): _avg(), build_prompt(), call_gemini(), classify_segment(), dashboard(), fetch_schemes(), fetch_user(), get_notifications() (+8 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (2): NotifCard(), toneColor()

### Community 2 - "Community 2"
Cohesion: 0.13
Nodes (0): 

### Community 3 - "Community 3"
Cohesion: 0.25
Nodes (13): aggregate(), build_prompt(), call_gemini(), get_rows(), main(), parse_json(), print_notif(), Notification Pipeline v3 ========================= - Reads metadata CSV + scor (+5 more)

### Community 4 - "Community 4"
Cohesion: 0.27
Nodes (12): build_prompt(), call_gemini(), get_user_row(), load_schemes(), main(), parse_json(), print_notif(), Notification Pipeline v4 ========================= - Single Excel/CSV for user (+4 more)

### Community 5 - "Community 5"
Cohesion: 0.25
Nodes (2): build_meta_prompt(), choose_segment()

### Community 6 - "Community 6"
Cohesion: 0.43
Nodes (7): build_meta_prompt(), call_gemini(), load_user(), main(), User Notification Prompt Pipeline (MVP) =======================================, save_output(), section()

### Community 7 - "Community 7"
Cohesion: 1
Nodes (0): 

## Knowledge Gaps
- **8 isolated node(s):** `Notification MVP — FastAPI + Supabase ====================================== E`, `1. Use primary_category field if present     2. Fallback: highest score wins`, `Returns all saved notification records from Supabase.     Groups by user_id so`, `User Notification Prompt Pipeline (MVP) =======================================`, `Notification Pipeline v4 ========================= - Single Excel/CSV for user` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 7`** (1 nodes): `vite.config.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `Notification MVP — FastAPI + Supabase ====================================== E`, `1. Use primary_category field if present     2. Fallback: highest score wins`, `Returns all saved notification records from Supabase.     Groups by user_id so` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.13 - nodes in this community are weakly interconnected._