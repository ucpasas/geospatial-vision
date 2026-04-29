---
type: schema
created: 2026-04-22
updated: 2026-04-29
---

# Wiki Schema — geospatial-vision

This document defines the conventions for maintaining this wiki. The LLM (Claude Code) owns all wiki content. The human curates source work; Claude updates the wiki after every meaningful task.

---

## Philosophy

This wiki is a **persistent, compounding artifact** — not a static README. Each time work happens in the `geospatial-vision` repo, relevant pages are updated so future sessions start with full context rather than re-deriving it from code.

> Read `index.md` first when answering any query. Consult project/concept pages before writing code. Update the wiki after every session.

---

## Directory Structure

```
wiki/geospatial-vision/
├── WIKI_SCHEMA.md          ← this file: conventions & workflows
├── index.md                ← master catalog (read first)
├── log.md                  ← append-only session log
├── projects/               ← one page per subproject
│   ├── geoprocessor.md
│   ├── pipeline-system.md
│   ├── fastapi-spatial-api.md
│   ├── dtm-postgis.md
│   ├── giro3d-viewer.md
│   └── geo-viz.md
├── concepts/               ← reusable technical concepts
│   ├── gdal.md
│   ├── pdal.md
│   ├── cog.md
│   ├── copc.md
│   ├── postgis.md
│   └── smrf.md
├── environment/            ← setup, install rules, env constraints
│   ├── wsl2-setup.md
│   ├── conda-lidar-env.md
│   ├── python-install-rules.md
│   └── r2-setup.md
└── decisions/              ← ADRs and pending trade-off notes
    └── postgis-vs-titiler.md
```

---

## Frontmatter Convention

Every page must have YAML frontmatter:

```yaml
---
tags: [project|concept|environment|decision, ...domain tags]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active | in-progress | pending | complete | stale
type: project | concept | environment | decision
related: [[Page1]], [[Page2]]
---
```

- `tags` — first tag is always the page type; remaining are domain keywords
- `status` — reflects current state of the thing described; update on every session
- `related` — explicit cross-references (Obsidian also builds backlinks automatically)

---

## Wikilink Convention

- Use `[[filename]]` (no path prefix) for Obsidian-compatible wikilinks
- Use `[[filename|Display Text]]` when the filename alone is not readable
- Every page must link to at least one other page
- Concept pages should be linked from every project page that uses them

---

## Workflows

### Ingest (after code work)
1. Identify which project page(s) are affected
2. Update `status`, `updated` date, and relevant sections
3. Update or create any concept pages touched
4. Append a dated entry to `log.md`
5. Update `index.md` if a new page was created

### Query (before code work)
1. Read `index.md` for orientation
2. Read the relevant project page
3. Follow `[[wikilinks]]` to concept pages as needed

### Lint (periodically)
- Check for orphaned pages (no inbound links)
- Check for stale `status` fields
- Check for contradictions between project and concept pages
- Flag missing cross-references

---

## Source of Truth

The wiki summarises; the source repo is authoritative for code. When wiki and code conflict, trust the code — then update the wiki.

Raw sources (code, data, configs) live in:
`/home/kisar/src/geospatial-vision/`

Wiki lives at:
`/home/kisar/src/geospatial-vision/wiki/` (tracked in the same repo — readable from Claude chat via GitHub MCP)
